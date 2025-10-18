"""
BTS 마켓 인덱스 스케줄러

백그라운드에서 주기적으로 지수 업데이트 및 WebSocket 알림
"""
import asyncio
import threading
import time
import json
from datetime import datetime
from typing import Set, Any
import websockets

from application.services.market_index_service import MarketIndexService
from infrastructure.repositories.market_index_repository import MarketIndexRepository
from infrastructure.database.connection import engine  # 전역 엔진 사용
from sqlalchemy.orm import sessionmaker
from domain.entities.market_index import MarketIndex
from config.market_index_config import MarketIndexConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketIndexScheduler:
    """
    마켓 인덱스 백그라운드 스케줄러

    기능:
    1. 설정된 주기마다 자동으로 지수 업데이트
    2. 업데이트 완료 시 WebSocket으로 클라이언트에 알림
    3. 연결 끊김 감지 및 자동 재연결
    4. 클라이언트 상태 관리
    """

    def __init__(self):
        self.service = MarketIndexService()  # 캐싱 제거된 기본 서비스 사용
        self.config = MarketIndexConfig()
        self.running = False
        self.update_thread = None
        self.websocket_thread = None
        self.websocket_loop = None  # WebSocket 이벤트 루프 참조
        self.connected_clients: Set[Any] = set()  # WebSocket 클라이언트 집합
        self.websocket_server = None
        self.last_update_time = None
        self.health_check_interval = 30  # 30초마다 헬스체크
        self.client_info = {}  # 클라이언트별 정보 저장
        self.min_update_interval = self.config.SAFE_UPBIT_SCRAPING  # 시스템 최소 업데이트 간격 (6초)

    # ===== 스케줄러 =====

    def _serialize_data(self, data):
        """datetime 객체를 JSON 직렬화 가능한 형태로 변환"""
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_data(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data

    def _format_coin_data_for_websocket(self, coin_data: list, usd_krw_rate: float = 1400.0) -> list:
        """
        코인 데이터에 포맷팅된 가격 필드 추가 (WebSocket 전송용)
        
        Args:
            coin_data: 코인 데이터 리스트
            usd_krw_rate: USD/KRW 환율
            
        Returns:
            list: 포맷팅된 코인 데이터 리스트
        """
        if not coin_data or not isinstance(coin_data, list):
            return []
        
        formatted_coins = []
        for coin in coin_data:
            # 원본 데이터 복사
            formatted_coin = dict(coin)
            
            # USD 가격 추출
            price_usd = float(coin.get('current_price', 0))
            
            # USD 포맷팅 (천 단위 콤마)
            if price_usd < 1:
                formatted_coin['price_usd_formatted'] = f"${price_usd:.4f}"
            else:
                formatted_coin['price_usd_formatted'] = f"${price_usd:,.2f}"
            
            # KRW 환산 및 포맷팅 (천 단위 콤마)
            price_krw = price_usd * usd_krw_rate
            if price_krw < 1000:
                formatted_coin['price_krw_formatted'] = f"₩{price_krw:,.2f}"
            else:
                formatted_coin['price_krw_formatted'] = f"₩{price_krw:,.0f}"
            
            formatted_coins.append(formatted_coin)
        
        return formatted_coins

    def update_all_indices(self):
        """모든 지수 업데이트 (개선된 버전)"""
        try:
            update_start_time = datetime.now()
            logger.info(f"[스케줄러] 지수 업데이트 시작 ({update_start_time})")
            
            # 캐싱 없이 직접 데이터 수집 및 DB 저장
            self._collect_and_save_all_data()
            
            # 업데이트 시간 기록
            self.last_update_time = datetime.now()
            update_duration = (self.last_update_time - update_start_time).total_seconds()
            logger.info(f"[스케줄러] 지수 업데이트 완료 (소요시간: {update_duration:.2f}초)")

            # DB에서 최신 데이터 조회 (캐싱 제거)
            upbit_data = self._get_upbit_data_from_db()
            usd_data = self._get_usd_krw_data_from_db()
            global_data = self._get_global_data_from_db()
            coin_data = self._get_coin_data_from_db()

            # 코인 데이터 포맷팅 (WebSocket 전송용 가격 문자열 추가)
            usd_krw_rate = usd_data.get('value', 1400.0) if isinstance(usd_data, dict) else 1400.0
            coin_data = self._format_coin_data_for_websocket(coin_data, usd_krw_rate)

            # datetime 객체 직렬화
            upbit_data = self._serialize_data(upbit_data)
            usd_data = self._serialize_data(usd_data)
            global_data = self._serialize_data(global_data)
            coin_data = self._serialize_data(coin_data)

            # JSON 메시지 구성
            message_data = {
                "type": "indices_updated",
                "timestamp": self.last_update_time.isoformat(),
                "update_duration": update_duration,
                "data": {
                    "upbit": upbit_data,
                    "usd_krw": usd_data,
                    "global": global_data,
                    "top_coins": coin_data
                }
            }
            message_json = json.dumps(message_data, ensure_ascii=False)

            # WebSocket 클라이언트에 데이터 전송
            self._notify_clients_safe(message_json)

        except Exception as e:
            logger.error(f"[스케줄러] 업데이트 실패: {e}", exc_info=True)

    def _notify_clients_safe(self, message_json: str):
        """안전한 클라이언트 알림 (논블로킹)"""
        if not self.websocket_loop or self.websocket_loop.is_closed():
            logger.warning("[스케줄러] WebSocket 이벤트 루프 없음 - 전송 스킵")
            return
            
        if not self.connected_clients:
            logger.debug("[스케줄러] 연결된 클라이언트 없음 - 전송 스킵")
            return

        logger.info(f"[스케줄러] WebSocket 데이터 전송 시작 ({len(self.connected_clients)}명)")
        
        try:
            # 비동기 작업을 이벤트 루프에 예약 (논블로킹)
            future = asyncio.run_coroutine_threadsafe(
                self.notify_clients(message_json),
                self.websocket_loop
            )
            
            # 타임아웃 설정으로 블로킹 방지
            future.result(timeout=3)
            logger.info("[스케줄러] WebSocket 데이터 전송 완료")
            
        except asyncio.TimeoutError:
            logger.warning("[스케줄러] WebSocket 전송 타임아웃 (3초)")
        except Exception as notify_error:
            logger.error(f"[스케줄러] WebSocket 전송 실패: {notify_error}", exc_info=True)

    def run_scheduler(self):
        """스케줄러 메인 루프 - 듀얼 스레드 데이터 수집 + 페이지별 차등 WebSocket 전송"""
        logger.info("[SCHEDULER] 듀얼 스레드 스케줄러 시작")
        logger.info(f"[SCHEDULER] 업비트 지수 + USD/KRW 간격: {self.config.SAFE_UPBIT_SCRAPING}초")
        logger.info(f"[SCHEDULER] 글로벌 지수 간격: {self.config.SAFE_COINGECKO}초")
        logger.debug("[SCHEDULER] WebSocket 전송: 페이지별 차등 전송 전략 적용")
        
        # 활성화된 페이지 전략 출력
        for page, strategy in MarketIndexConfig.WEBSOCKET_PAGE_STRATEGIES.items():
            if strategy['enabled']:
                logger.debug(f"[SCHEDULER] {page} 페이지: {strategy['interval']}초 간격 ({strategy['description']})")

        # 백그라운드 데이터 업데이트 스레드 시작 (2개 독립 스레드)
        self._start_background_data_updater()

        # 페이지별 마지막 전송 시간 추적
        last_send_times = {}
        
        # 시작 시 활성화된 페이지에 즉시 한 번 전송
        self._send_websocket_by_page_strategy(last_send_times, force_send=True)

        while self.running:
            # 다음 전송까지 대기할 시간 계산
            next_sleep = self._calculate_next_sleep_time(last_send_times)
            
            if next_sleep > 0:
                logger.debug(f"[WebSocket 스케줄러] 다음 전송까지 {next_sleep:.1f}초 대기")
                time.sleep(next_sleep)
            
            if self.running:
                self._send_websocket_by_page_strategy(last_send_times)

    def _start_background_data_updater(self):
        """
        백그라운드 데이터 업데이트 스레드 시작

        각 데이터 소스별로 독립적인 업데이트 주기를 가진 스레드 실행:
        - 업비트 지수: 8초 (웹스크래핑, 실측 필요)
        - 글로벌 지수: 8초 (CoinGecko API)
        - USD/KRW 환율: 1시간 (FxRates API, 무료 플랜 제한)
        """

        def upbit_update_loop():
            """업비트 지수 + USD/KRW 업데이트 루프 (동적 간격)"""
            logger.info(f"[업비트 업데이터] 스레드 시작")

            while self.running:
                try:
                    start_time = datetime.now()

                    # 동적 간격 계산 (Dashboard 활성 여부에 따라)
                    interval = self._get_update_interval_for_upbit()

                    logger.info(f"[업비트 업데이터] 업비트 지수 + USD/KRW 수집 시작 (간격: {interval}초)")

                    # 업비트 지수 수집 (USD/KRW 포함)
                    data = self.service.get_upbit_indices()
                    if self._validate_collected_data(data, "업비트 지수"):
                        self._save_upbit_data(data)

                        # USD/KRW가 포함되어 있으면 저장
                        if 'usd_krw' in data and data['usd_krw'].get('value', 0) > 0:
                            self._save_usd_krw_data(data['usd_krw'])
                            logger.info(f"[업비트 업데이터] USD/KRW 함께 저장: {data['usd_krw']['value']:,.2f} ({data['usd_krw']['change_rate']:+.2f}%)")

                    duration = (datetime.now() - start_time).total_seconds()
                    logger.info(f"[업비트 업데이터] 완료 (소요시간: {duration:.2f}초)")

                    # Sleep을 WebSocket 전송 주기(5초)로 분할하여 Dashboard 전환 감지 개선
                    remaining_time = max(interval - duration, 1)
                    sleep_chunk = self.config.WEBSOCKET_UPDATE_INTERVAL  # 5초
                    elapsed = 0

                    while elapsed < remaining_time and self.running:
                        time.sleep(min(sleep_chunk, remaining_time - elapsed))
                        elapsed += sleep_chunk

                        # Dashboard 활성 상태 변화 감지
                        new_interval = self._get_update_interval_for_upbit()
                        if new_interval != interval:
                            logger.info(f"[업비트 업데이터] 간격 변경 감지: {interval}초 → {new_interval}초 (조기 종료)")
                            break  # 즉시 다음 루프 시작

                except Exception as e:
                    logger.error(f"[업비트 업데이터] 실패: {e}", exc_info=True)
                    time.sleep(5)  # 에러 시 5초 후 재시도

        def global_update_loop():
            """글로벌 지수 업데이트 루프 (동적 간격)"""
            logger.info(f"[글로벌 업데이터] 스레드 시작")

            while self.running:
                try:
                    start_time = datetime.now()

                    # 동적 간격 계산 (Dashboard 활성 여부에 따라)
                    interval = self._get_update_interval_for_global()

                    logger.info(f"[글로벌 업데이터] 글로벌 지수 수집 시작 (간격: {interval}초)")

                    # 글로벌 지수 수집 및 저장 (CoinGecko만 제공)
                    data = self.service.get_global_crypto_data()
                    if self._validate_collected_data(data, "글로벌 데이터"):
                        self._save_global_data(data)

                    logger.info(f"[글로벌 업데이터] 🔍 코인 데이터 수집 시작 (ENABLE_BINANCE_API={self.config.ENABLE_BINANCE_API})")
                    
                    # 코인 데이터 수집 (Binance Primary, CoinGecko Fallback)
                    coin_data = None
                    api_source = 'unknown'
                    
                    # 1. Binance 시도 (Primary)
                    if self.config.ENABLE_BINANCE_API:
                        try:
                            from infrastructure.exchanges.binance_service import BinanceService
                            binance = BinanceService()
                            coin_data = binance.get_top_coins_data(limit=self.config.BINANCE_TOP_COINS_LIMIT)
                            if coin_data and len(coin_data) > 0:
                                api_source = 'binance'
                                logger.info(f"[글로벌 업데이터] Binance에서 {len(coin_data)}개 코인 수집 완료")
                        except Exception as e:
                            logger.warning(f"[글로벌 업데이터] Binance 실패: {e}")
                    
                    # 2. CoinGecko Fallback
                    if not coin_data or len(coin_data) == 0:
                        if self.config.ENABLE_COINGECKO_API:
                            logger.info("[글로벌 업데이터] Binance 실패 - CoinGecko Fallback")
                            coingecko_data = self.service.get_top_coins_with_sparkline(limit=10)
                            if coingecko_data and len(coingecko_data) > 0:
                                # CoinGecko 데이터를 Binance 표준 포맷으로 변환
                                coin_data = self._convert_coingecko_to_binance_format(coingecko_data)
                                api_source = 'coingecko'
                                logger.info(f"[글로벌 업데이터] CoinGecko에서 {len(coin_data)}개 코인 수집 완료 (Binance 포맷으로 변환)")
                    
                    # 3. 데이터 저장
                    logger.debug(f"[글로벌 업데이터] 데이터 저장 시도: type={type(coin_data)}, count={len(coin_data) if coin_data else 0}, source={api_source}")
                    if self._validate_collected_data(coin_data, f"코인 데이터 ({api_source})"):
                        logger.debug(f"[글로벌 업데이터] 검증 통과 - 저장 시작")
                        self._save_coin_data(coin_data, api_source)
                    else:
                        logger.warning(f"[글로벌 업데이터] 검증 실패 - 저장 건너뜀")

                    duration = (datetime.now() - start_time).total_seconds()
                    logger.info(f"[글로벌 업데이터] 완료 (소요시간: {duration:.2f}초)")

                    # Sleep을 WebSocket 전송 주기(5초)로 분할하여 Dashboard 전환 감지 개선
                    remaining_time = max(interval - duration, 1)
                    sleep_chunk = self.config.WEBSOCKET_UPDATE_INTERVAL  # 5초
                    elapsed = 0

                    while elapsed < remaining_time and self.running:
                        time.sleep(min(sleep_chunk, remaining_time - elapsed))
                        elapsed += sleep_chunk

                        # Dashboard 활성 상태 변화 감지
                        new_interval = self._get_update_interval_for_global()
                        if new_interval != interval:
                            logger.info(f"[글로벌 업데이터] 간격 변경 감지: {interval}초 → {new_interval}초 (조기 종료)")
                            break  # 즉시 다음 루프 시작

                except Exception as e:
                    logger.error(f"[글로벌 업데이터] 실패: {e}", exc_info=True)
                    time.sleep(5)

        # 각 데이터 소스별 독립 스레드 시작 (USD/KRW는 Upbit과 함께 수집)
        threads = [
            threading.Thread(target=upbit_update_loop, daemon=True, name="UpbitUpdater"),
            threading.Thread(target=global_update_loop, daemon=True, name="GlobalUpdater")
        ]

        for thread in threads:
            thread.start()

        logger.info("[SCHEDULER] 듀얼 스레드 데이터 수집 시스템 시작됨:")
        logger.info(f"  - 업비트 지수 + USD/KRW: {self.config.SAFE_UPBIT_SCRAPING}초")
        logger.info(f"  - 글로벌 지수: {self.config.SAFE_COINGECKO}초")
        logger.info(f"  - WebSocket 전송: {self.config.WEBSOCKET_UPDATE_INTERVAL}초")

    def _calculate_next_sleep_time(self, last_send_times: dict) -> float:
        """다음 전송까지 대기할 시간 계산 (초 단위)
        
        Args:
            last_send_times: 페이지별 마지막 전송 시간
            
        Returns:
            다음 전송까지 남은 시간 (초), 전송할 페이지가 없으면 10초
        """
        current_time = time.time()
        min_wait_time = 10.0  # 클라이언트 없을 때 기본 대기 시간
        
        # 페이지별 클라이언트 그룹 분류
        page_clients = {}
        for ws, info in self.client_info.items():
            if ws not in self.connected_clients:
                continue
                
            page = info.get('page', 'unknown')
            if page not in page_clients:
                page_clients[page] = []
            page_clients[page].append(ws)
        
        # 활성화된 각 페이지의 다음 전송 시간까지 남은 시간 계산
        next_send_times = []
        
        for page, clients in page_clients.items():
            strategy = MarketIndexConfig.WEBSOCKET_PAGE_STRATEGIES.get(
                page, 
                MarketIndexConfig.WEBSOCKET_PAGE_STRATEGIES['unknown']
            )
            
            # 전송 비활성화된 페이지는 스킵
            if not strategy['enabled']:
                continue
            
            interval = strategy['interval']
            last_send = last_send_times.get(page, 0)
            elapsed = current_time - last_send
            remaining = interval - elapsed
            
            if remaining > 0:
                next_send_times.append(remaining)
                logger.debug(f"[WebSocket 스케줄러] {page}: 다음 전송까지 {remaining:.1f}초 남음")
        
        # 가장 빠른 전송 시간 반환
        if next_send_times:
            next_sleep = min(next_send_times)
            return max(next_sleep, 0.1)  # 최소 0.1초는 보장
        else:
            logger.debug(f"[WebSocket 스케줄러] 활성 클라이언트 없음 - {min_wait_time}초 대기")
            return min_wait_time

    def _send_websocket_by_page_strategy(self, last_send_times: dict, force_send: bool = False):
        """페이지별 전송 전략에 따라 WebSocket 전송
        
        Args:
            last_send_times: 페이지별 마지막 전송 시간 딕셔너리
            force_send: 강제 전송 여부 (시작 시)
        """
        # WebSocket 전송이 비활성화되어 있으면 전송하지 않음
        if not self._is_websocket_enabled():
            logger.debug("[WebSocket] 전송 비활성화됨 (user_settings에서 OFF)")
            return
        
        current_time = time.time()
        
        # 페이지별 클라이언트 그룹 분류
        page_clients = {}
        for ws, info in self.client_info.items():
            if ws not in self.connected_clients:
                continue
                
            page = info.get('page', 'unknown')
            if page not in page_clients:
                page_clients[page] = []
            page_clients[page].append(ws)
        
        # 각 페이지별로 전송 전략 확인 및 전송
        for page, clients in page_clients.items():
            strategy = MarketIndexConfig.WEBSOCKET_PAGE_STRATEGIES.get(
                page, 
                MarketIndexConfig.WEBSOCKET_PAGE_STRATEGIES['unknown']
            )
            
            # 전송 비활성화된 페이지는 스킵
            if not strategy['enabled']:
                continue
            
            # Dashboard 페이지는 user_settings에서 간격 가져오기
            if page == 'dashboard':
                interval = self._get_dashboard_websocket_interval()
            else:
                interval = strategy['interval']
            
            last_send = last_send_times.get(page, 0)
            
            # 전송 시간이 되었는지 확인
            if force_send or (current_time - last_send >= interval):
                try:
                    message_json = self._prepare_websocket_message()
                    self._send_to_page_clients(clients, message_json, page)
                    last_send_times[page] = current_time
                    logger.info(f"[WebSocket] {page} 페이지 {len(clients)}명 전송 완료 ({interval}초 주기)")
                except Exception as e:
                    logger.error(f"[WebSocket] {page} 페이지 전송 실패: {e}", exc_info=True)

    def _prepare_websocket_message(self) -> str:
        """WebSocket 전송용 메시지 준비"""
        # DB에서 직접 최신 데이터 조회
        upbit_data = self._get_upbit_data_from_db()
        usd_data = self._get_usd_krw_data_from_db()
        global_data = self._get_global_data_from_db()
        coin_data = self._get_coin_data_from_db()

        # 코인 데이터 포맷팅 (WebSocket 전송용 가격 문자열 추가)
        usd_krw_rate = usd_data.get('value', 1400.0) if isinstance(usd_data, dict) else 1400.0
        coin_data = self._format_coin_data_for_websocket(coin_data, usd_krw_rate)

        # datetime 객체 직렬화
        upbit_data = self._serialize_data(upbit_data)
        usd_data = self._serialize_data(usd_data)
        global_data = self._serialize_data(global_data)
        coin_data = self._serialize_data(coin_data)

        # 메시지 구성
        message = {
            'type': 'indices_updated',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'upbit': upbit_data,
                'usd_krw': usd_data,
                'global': global_data,
                'top_coins': coin_data
            }
        }
        
        return json.dumps(message, ensure_ascii=False, default=str)

    def _send_to_page_clients(self, clients: list, message_json: str, page: str):
        """특정 페이지 클라이언트 그룹에게 전송"""
        if not self.websocket_loop or self.websocket_loop.is_closed():
            logger.warning(f"[WebSocket] {page} 전송 스킵 - 이벤트 루프 없음")
            return
        
        try:
            # 비동기 작업을 이벤트 루프에 예약 (논블로킹)
            future = asyncio.run_coroutine_threadsafe(
                self._notify_specific_clients(clients, message_json, page),
                self.websocket_loop
            )
            
            # 타임아웃 설정으로 블로킹 방지
            future.result(timeout=3)
            
        except asyncio.TimeoutError:
            logger.warning(f"[WebSocket] {page} 전송 타임아웃 (3초)")
        except Exception as e:
            logger.error(f"[WebSocket] {page} 전송 실패: {e}", exc_info=True)

    async def _notify_specific_clients(self, clients: list, message: str, page: str):
        """특정 클라이언트 그룹에게만 전송"""
        disconnected = []
        successful_sends = 0

        for websocket in clients:
            try:
                await websocket.send(message)
                successful_sends += 1
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(websocket)
                logger.warning(f"[{page}] 연결 끊긴 클라이언트 감지: {getattr(websocket, 'remote_address', 'unknown')}")
            except Exception as e:
                disconnected.append(websocket)
                logger.error(f"[{page}] 클라이언트 전송 실패: {e}")

        # 끊어진 연결 정리
        for websocket in disconnected:
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)
            if websocket in self.client_info:
                del self.client_info[websocket]

        if disconnected:
            logger.info(f"[{page}] 끊어진 연결 {len(disconnected)}개 정리 완료")
        
        logger.debug(f"[{page}] WebSocket 전송 완료: {successful_sends}/{len(clients) + len(disconnected)}명")

    def _send_websocket_update(self):
        """WebSocket 클라이언트에게 최신 데이터 전송 (레거시 메서드 - 호환성 유지)"""
        try:
            # DB에서 직접 최신 데이터 조회
            upbit_data = self._get_upbit_data_from_db()
            usd_data = self._get_usd_krw_data_from_db()
            global_data = self._get_global_data_from_db()
            coin_data = self._get_coin_data_from_db()

            # 코인 데이터 포맷팅 (WebSocket 전송용 가격 문자열 추가)
            usd_krw_rate = usd_data.get('value', 1400.0) if isinstance(usd_data, dict) else 1400.0
            coin_data = self._format_coin_data_for_websocket(coin_data, usd_krw_rate)

            # datetime 객체 직렬화
            upbit_data = self._serialize_data(upbit_data)
            usd_data = self._serialize_data(usd_data)
            global_data = self._serialize_data(global_data)
            coin_data = self._serialize_data(coin_data)

            # 메시지 구성
            message = {
                'type': 'indices_updated',
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'upbit': upbit_data,
                    'usd_krw': usd_data,
                    'global': global_data,
                    'top_coins': coin_data
                }
            }

            # WebSocket 전송
            message_json = json.dumps(message, ensure_ascii=False, default=str)
            self._notify_clients_safe(message_json)
            
        except Exception as e:
            logger.error(f"[SCHEDULER] WebSocket 업데이트 실패: {e}", exc_info=True)

    def _is_dashboard_active(self) -> bool:
        """Dashboard가 활성화되어 있는지 확인"""
        dashboard_clients = [info for ws, info in self.client_info.items()
                           if info.get('page') == 'dashboard' and ws in self.connected_clients]
        return len(dashboard_clients) > 0

    def _is_websocket_enabled(self) -> bool:
        """WebSocket 전송이 활성화되어 있는지 확인 (UserSettings에서)"""
        try:
            from infrastructure.repositories.user_settings_repository import UserSettingsRepository
            from domain.entities.user_settings import UserSettings

            settings_repo = UserSettingsRepository()
            websocket_setting = settings_repo.get_by_key(UserSettings.WEBSOCKET_ENABLED)

            if websocket_setting:
                # 'True', 'true', '1' 등을 True로 인식
                return websocket_setting.setting_value.lower() in ('true', '1', 'yes')
            else:
                # 기본값: WebSocket 활성화
                return True

        except Exception as e:
            logger.error(f"WebSocket 활성화 여부 조회 실패: {e}")
            return True  # 에러 시 기본적으로 활성화

    def _get_dashboard_websocket_interval(self) -> int:
        """Dashboard WebSocket 전송 간격 (UserSettings에서 가져오기)"""
        try:
            from infrastructure.repositories.user_settings_repository import UserSettingsRepository
            from domain.entities.user_settings import UserSettings

            settings_repo = UserSettingsRepository()
            dashboard_setting = settings_repo.get_by_key(UserSettings.DASHBOARD_REFRESH_INTERVAL)

            if dashboard_setting:
                return int(dashboard_setting.setting_value)
            else:
                # 기본값: config의 dashboard 전략 interval
                return MarketIndexConfig.WEBSOCKET_PAGE_STRATEGIES['dashboard']['interval']

        except Exception as e:
            logger.error(f"Dashboard WebSocket 간격 조회 실패: {e}")
            return MarketIndexConfig.WEBSOCKET_PAGE_STRATEGIES['dashboard']['interval']

    def _get_background_interval(self) -> int:
        """백그라운드 모드 업데이트 간격 (UserSettings에서 가져오기)"""
        try:
            from infrastructure.repositories.user_settings_repository import UserSettingsRepository
            from domain.entities.user_settings import UserSettings

            settings_repo = UserSettingsRepository()
            general_setting = settings_repo.get_by_key(UserSettings.GENERAL_UPDATE_INTERVAL)

            if general_setting:
                return int(general_setting.setting_value)
            else:
                return int(self.config.BACKGROUND_UPDATE_INTERVAL)

        except Exception as e:
            logger.error(f"백그라운드 간격 조회 실패: {e}")
            return int(self.config.BACKGROUND_UPDATE_INTERVAL)

    def _get_update_interval_for_upbit(self) -> int:
        """업비트 업데이트 간격 (Dashboard 활성 여부에 따라)"""
        if self._is_dashboard_active():
            return int(self.config.SAFE_UPBIT_SCRAPING)  # 빠른 모드: 6초
        else:
            return self._get_background_interval()  # 느린 모드: 사용자 설정값

    def _get_update_interval_for_global(self) -> int:
        """글로벌 업데이트 간격 (Dashboard 활성 여부에 따라)"""
        if self._is_dashboard_active():
            return int(self.config.SAFE_COINGECKO)  # 빠른 모드: 3초
        else:
            return self._get_background_interval()  # 느린 모드: 사용자 설정값

    def _get_dynamic_update_interval(self) -> int:
        """동적 업데이트 간격 계산 (하위 호환성 유지)"""
        try:
            from infrastructure.repositories.user_settings_repository import UserSettingsRepository
            from domain.entities.user_settings import UserSettings

            settings_repo = UserSettingsRepository()

            # 대시보드에 연결된 클라이언트들의 요청 간격 수집
            dashboard_clients = [info for ws, info in self.client_info.items()
                               if info.get('page') == 'dashboard' and ws in self.connected_clients]

            if len(dashboard_clients) > 0:
                # 대시보드 클라이언트들의 요청 간격 중 최소값 찾기
                requested_intervals = []

                for client_info in dashboard_clients:
                    interval = client_info.get('requested_interval', 0)
                    if interval > 0:
                        requested_intervals.append(interval)

                # 요청된 간격이 있으면 최소값 사용, 없으면 설정값 사용
                if requested_intervals:
                    min_requested = min(requested_intervals)
                    # rate limit 고려하여 최소값 적용
                    actual_interval = max(min_requested, self.min_update_interval)
                    logger.info(f"[SCHEDULER] 대시보드 활성 모드: 요청간격들 {requested_intervals}초 중 최소 {min_requested}초, 실제 적용 {actual_interval}초 (최소한계 {self.min_update_interval}초)")
                    return actual_interval
                else:
                    # 요청 간격이 없으면 설정에서 가져오기
                    dashboard_setting = settings_repo.get_by_key(UserSettings.DASHBOARD_REFRESH_INTERVAL)
                    if dashboard_setting and int(dashboard_setting.setting_value) > 0:
                        dashboard_interval = max(int(dashboard_setting.setting_value), self.min_update_interval)
                        logger.info(f"[SCHEDULER] 대시보드 활성 모드: 설정값 {dashboard_interval}초 간격")
                        return dashboard_interval

            # 일반 업데이트 간격 사용
            general_setting = settings_repo.get_by_key(UserSettings.GENERAL_UPDATE_INTERVAL)
            if general_setting:
                general_interval = max(int(general_setting.setting_value), self.min_update_interval)
                logger.info(f"[SCHEDULER] 백그라운드 모드: {general_interval}초 간격")
                return general_interval

            # 기본값 (최소값 보장)
            default_interval = int(max(self.config.BACKGROUND_UPDATE_INTERVAL, self.min_update_interval))
            logger.info(f"[SCHEDULER] 기본값 사용: {default_interval}초 간격")
            return default_interval

        except Exception as e:
            logger.error(f"동적 간격 계산 실패: {e}")
            return int(max(self.config.BACKGROUND_UPDATE_INTERVAL, self.min_update_interval))

    def start_scheduler(self):
        """스케줄러 시작"""
        if self.running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        self.running = True
        self.update_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.update_thread.start()

    # ===== WebSocket 서버 =====

    async def handle_client(self, websocket, path=None):
        """WebSocket 클라이언트 연결 처리"""
        _ = path  # unused parameter
        client_address = getattr(websocket, 'remote_address', 'unknown')
        
        self.connected_clients.add(websocket)
        logger.info(f"[WebSocket] 클라이언트 연결: {client_address} (총 {len(self.connected_clients)}명)")

        try:
            # 연결 즉시 최신 데이터 전송
            await self.send_latest_data_to_client(websocket)
            
            # 클라이언트로부터 메시지 대기 (연결 유지)
            async for message in websocket:
                logger.debug(f"WebSocket 메시지 수신 [{client_address}]: {message}")
                
                if message == "ping":
                    await websocket.send("pong")
                    logger.debug(f"WebSocket pong 전송 완료 [{client_address}]")
                elif message == "get_latest":
                    # 클라이언트 요청 시 최신 데이터 전송
                    await self.send_latest_data_to_client(websocket)
                else:
                    # JSON 메시지 처리
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'client_info':
                            # 클라이언트 정보 저장
                            self.client_info[websocket] = {
                                'page': data.get('page'),
                                'timestamp': data.get('timestamp'),
                                'address': client_address,
                                'requested_interval': data.get('requested_interval', 0)  # 클라이언트가 요청한 간격
                            }
                            logger.info(f"클라이언트 정보 등록 [{client_address}]: {data.get('page')} 페이지, 요청 간격: {data.get('requested_interval', 0)}초")
                    except json.JSONDecodeError:
                        logger.warning(f"JSON 파싱 실패 [{client_address}]: {message}")
                    except Exception as e:
                        logger.error(f"메시지 처리 오류 [{client_address}]: {e}")
                    
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"WebSocket 연결 비정상 종료 [{client_address}]: {e}")
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"WebSocket 연결 정상 종료 [{client_address}]")
        except Exception as e:
            logger.error(f"WebSocket 처리 중 오류 [{client_address}]: {e}", exc_info=True)
        finally:
            # 연결 해제 처리
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)
            if websocket in self.client_info:
                del self.client_info[websocket]
            logger.info(f"WebSocket 클라이언트 연결 해제: {client_address} (남은 {len(self.connected_clients)}명)")

    async def send_latest_data_to_client(self, websocket):
        """특정 클라이언트에 최신 데이터 전송"""
        try:
            # DB에서 직접 최신 데이터 조회
            upbit_data = self._get_upbit_data_from_db()
            usd_data = self._get_usd_krw_data_from_db()
            global_data = self._get_global_data_from_db()
            coin_data = self._get_coin_data_from_db()

            # 코인 데이터 포맷팅 (WebSocket 전송용 가격 문자열 추가)
            usd_krw_rate = usd_data.get('value', 1400.0) if isinstance(usd_data, dict) else 1400.0
            coin_data = self._format_coin_data_for_websocket(coin_data, usd_krw_rate)

            # datetime 객체 직렬화
            upbit_data = self._serialize_data(upbit_data)
            usd_data = self._serialize_data(usd_data)
            global_data = self._serialize_data(global_data)
            coin_data = self._serialize_data(coin_data)

            # JSON 메시지 구성
            message_data = {
                "type": "indices_updated",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "upbit": upbit_data,
                    "usd_krw": usd_data,
                    "global": global_data,
                    "top_coins": coin_data
                }
            }
            message_json = json.dumps(message_data, ensure_ascii=False)
            
            await websocket.send(message_json)
            logger.debug(f"최신 데이터 전송 완료 [{getattr(websocket, 'remote_address', 'unknown')}]")
            
        except Exception as e:
            logger.error(f"최신 데이터 전송 실패: {e}")

    async def notify_clients(self, message: str):
        """연결된 모든 클라이언트에 알림 (개선된 버전)"""
        if not self.connected_clients:
            logger.debug("WebSocket 알림 스킵: 연결된 클라이언트 없음")
            return

        logger.info(f"WebSocket 알림 전송 시작 ({len(self.connected_clients)}명)")
        
        # 끊어진 연결 감지를 위한 리스트
        disconnected_clients = []
        successful_sends = 0

        # 각 클라이언트에 개별적으로 전송
        for websocket in list(self.connected_clients):  # 복사본으로 순회
            try:
                await websocket.send(message)
                successful_sends += 1
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(websocket)
                logger.warning(f"연결 끊긴 클라이언트 감지: {getattr(websocket, 'remote_address', 'unknown')}")
            except Exception as e:
                disconnected_clients.append(websocket)
                logger.error(f"클라이언트 전송 실패: {e}")

        # 끊어진 연결 정리
        for websocket in disconnected_clients:
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)

        if disconnected_clients:
            logger.info(f"끊어진 연결 {len(disconnected_clients)}개 정리 완료")
        
        logger.info(f"WebSocket 알림 전송 완료 ({successful_sends}/{len(self.connected_clients) + len(disconnected_clients)})")

    async def start_websocket_server(self):
        """WebSocket 서버 시작 (개선된 버전)"""
        try:
            # 서버 시작 시 ping interval 설정으로 연결 안정성 향상
            self.websocket_server = await websockets.serve(
                self.handle_client,
                self.config.WEBSOCKET_HOST,
                self.config.WEBSOCKET_PORT,
                ping_interval=20,  # 20초마다 ping
                ping_timeout=10,   # ping 응답 대기 시간 10초
                close_timeout=10   # 종료 대기 시간 10초
            )
            logger.info(f"[WebSocket] 서버 시작: {self.config.get_websocket_url()}")
            logger.debug("[WebSocket] ping 간격: 20초, timeout: 10초")
            
            # 서버 종료까지 대기
            await self.websocket_server.wait_closed()
            
        except Exception as e:
            logger.error(f"[WebSocket] 서버 오류: {e}", exc_info=True)
        finally:
            logger.info("WebSocket 서버 종료됨")

    def run_websocket_server(self):
        """WebSocket 서버 실행 (별도 스레드)"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.websocket_loop = loop  # 이벤트 루프 참조 저장
            logger.info("WebSocket 이벤트 루프 초기화 완료")
            
            loop.run_until_complete(self.start_websocket_server())
            
        except Exception as e:
            logger.error(f"WebSocket 서버 스레드 오류: {e}", exc_info=True)
        finally:
            logger.info("WebSocket 서버 스레드 종료")

    def start_websocket(self):
        """WebSocket 서버 시작"""
        if self.websocket_thread and self.websocket_thread.is_alive():
            logger.warning("WebSocket 서버가 이미 실행 중입니다")
            return
            
        self.websocket_thread = threading.Thread(
            target=self.run_websocket_server, 
            daemon=True,
            name="WebSocketServer"
        )
        self.websocket_thread.start()
        logger.info("WebSocket 서버 스레드 시작됨")

    # ===== 제어 =====

    def start(self):
        """스케줄러 + WebSocket 서버 시작"""
        logger.info("=== 마켓 인덱스 백그라운드 시스템 시작 ===")
        self.start_scheduler()
        self.start_websocket()
        logger.info("=== 시작 완료 ===")

    def stop(self):
        """스케줄러 + WebSocket 서버 중지 (개선된 버전)"""
        logger.info("마켓 인덱스 백그라운드 시스템 중지 시작...")
        
        # 스케줄러 중지
        self.running = False

        # 업데이트 스레드 종료 대기
        if self.update_thread and self.update_thread.is_alive():
            logger.info("업데이트 스레드 종료 대기...")
            self.update_thread.join(timeout=5)
            if self.update_thread.is_alive():
                logger.warning("업데이트 스레드가 5초 내에 종료되지 않음")

        # WebSocket 서버 종료
        if self.websocket_server:
            logger.info("WebSocket 서버 종료 중...")
            try:
                if self.websocket_loop and not self.websocket_loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(
                        self._close_websocket_server(),
                        self.websocket_loop
                    )
                    future.result(timeout=3)
            except Exception as e:
                logger.error(f"WebSocket 서버 종료 중 오류: {e}")

        # WebSocket 스레드 종료 대기
        if self.websocket_thread and self.websocket_thread.is_alive():
            logger.info("WebSocket 스레드 종료 대기...")
            self.websocket_thread.join(timeout=3)
            if self.websocket_thread.is_alive():
                logger.warning("WebSocket 스레드가 3초 내에 종료되지 않음")

        logger.info("마켓 인덱스 백그라운드 시스템 중지 완료")

    async def _close_websocket_server(self):
        """WebSocket 서버 안전 종료"""
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
            self.websocket_server = None
            logger.info("WebSocket 서버 종료 완료")

    def get_status(self) -> dict:
        """현재 상태 반환 (개선된 버전)"""
        dashboard_clients = [info for info in self.client_info.values() if info.get('page') == 'dashboard']
        
        return {
            'running': self.running,
            'update_interval_minutes': self.config.get_update_interval_minutes(),
            'websocket_url': self.config.get_websocket_url(),
            'connected_clients': len(self.connected_clients),
            'dashboard_clients': len(dashboard_clients),
            'current_mode': 'dashboard' if len(dashboard_clients) > 0 else 'background',
            'websocket_server_running': self.websocket_server is not None,
            'websocket_loop_running': self.websocket_loop is not None and not self.websocket_loop.is_closed(),
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'client_details': [
                {
                    'address': info.get('address', 'unknown'),
                    'page': info.get('page', 'unknown'),
                    'connected_at': info.get('timestamp')
                }
                for info in self.client_info.values()
            ],
            'threads': {
                'update_thread_alive': self.update_thread is not None and self.update_thread.is_alive(),
                'websocket_thread_alive': self.websocket_thread is not None and self.websocket_thread.is_alive()
            }
        }

    def _collect_and_save_all_data(self):
        """모든 지수 데이터 수집 및 DB 저장 (단순화된 직접 호출 방식)"""
        collection_start = datetime.now()
        success_count = 0
        total_count = 4
        
        logger.info("[데이터 수집 시작] 캐싱 없는 직접 서비스 호출 방식 사용")
        
        # 수집할 데이터 소스 정의 (우선순위 순)
        data_sources = [
            ("업비트 지수", self.service.get_upbit_indices, self._save_upbit_data, True),  # 웹스크래핑
            ("USD/KRW 환율", self.service.get_usd_krw_rate, self._save_usd_krw_data, False),  # API
            ("글로벌 데이터", self.service.get_global_crypto_data, self._save_global_data, False),  # API
            ("코인게코 데이터", lambda: self.service.get_top_coins_with_sparkline(limit=10), self._save_coingecko_data, False)  # API
        ]
        
        # 각 데이터 소스별 순차 처리
        for name, collect_func, save_func, is_critical in data_sources:
            success = self._collect_and_save_single_source(name, collect_func, save_func, is_critical)
            if success:
                success_count += 1
        
        # 전체 수집 결과 요약
        total_duration = (datetime.now() - collection_start).total_seconds()
        success_rate = (success_count / total_count) * 100
        logger.info(f"[데이터 수집 완료] 성공률: {success_count}/{total_count} ({success_rate:.1f}%) - 총 소요시간: {total_duration:.2f}초")

    def _collect_and_save_single_source(self, name: str, collect_func, save_func, is_critical: bool = False) -> bool:
        """단일 데이터 소스 수집 및 저장 (단순화된 로직)"""
        start_time = datetime.now()
        try:
            logger.info(f"[데이터 수집] {name} 수집 시작...")
            
            # 데이터 수집
            data = collect_func()
            
            # 데이터 검증
            if not self._validate_collected_data(data, name):
                logger.warning(f"[데이터 수집] ✗ {name} 데이터 검증 실패")
                return False
            
            # 데이터 저장
            save_func(data)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"[데이터 수집] {name} 완료 (소요시간: {duration:.2f}초)")
            return True
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            if is_critical:
                logger.error(f"[데이터 수집] {name} 실패 (소요시간: {duration:.2f}초): {e}")
            else:
                logger.warning(f"[데이터 수집] ✗ {name} 실패 (소요시간: {duration:.2f}초): {e}")
            return False

    def _convert_coingecko_to_binance_format(self, coingecko_data: list) -> list:
        """
        CoinGecko 데이터를 Binance 표준 포맷으로 변환
        
        Args:
            coingecko_data: CoinGecko API 응답 데이터
            
        Returns:
            Binance 표준 포맷 리스트
        """
        converted_data = []
        
        for coin in coingecko_data:
            try:
                # Binance 표준 포맷으로 변환
                binance_format = {
                    'id': coin.get('id', '').lower(),
                    'symbol': coin.get('symbol', '').upper(),
                    'name': coin.get('name', ''),
                    'current_price': float(coin.get('current_price', 0)),
                    'price_change_24h': 0.0,  # CoinGecko는 제공하지 않음
                    'price_change_percentage_24h': float(coin.get('price_change_percentage_24h', 0)),
                    'high_24h': 0.0,  # CoinGecko는 제공하지 않음
                    'low_24h': 0.0,   # CoinGecko는 제공하지 않음
                    'total_volume': 0.0,  # CoinGecko는 제공하지 않음 (다른 필드명)
                    'market_cap': float(coin.get('market_cap', 0)),
                    'last_updated': datetime.now().isoformat(),
                    'source': 'coingecko'  # 출처 표시
                }
                converted_data.append(binance_format)
            except Exception as e:
                logger.warning(f"[포맷 변환] {coin.get('symbol', 'Unknown')} 변환 실패: {e}")
                continue
        
        logger.info(f"[포맷 변환] CoinGecko → Binance 포맷: {len(converted_data)}개 변환 완료")
        return converted_data

    def _validate_collected_data(self, data, source_name: str) -> bool:
        """수집된 데이터의 유효성 검증"""
        if not data:
            logger.debug(f"[데이터 검증] {source_name}: 데이터 없음")
            return False
            
        if not isinstance(data, dict):
            # 코인 데이터는 리스트일 수 있음 (Binance, CoinGecko)
            if isinstance(data, list) and ("코인" in source_name or "binance" in source_name.lower() or "coingecko" in source_name.lower()):
                result = len(data) > 0 and all(isinstance(item, dict) for item in data)
                logger.info(f"[데이터 검증] {source_name}: 리스트 검증 결과={result}, 길이={len(data)}")
                return result
            logger.debug(f"[데이터 검증] {source_name}: dict 타입이 아님 (타입: {type(data)})")
            return False
            
        # 기본 구조 검증
        if source_name == "업비트 지수":
            return any(key in data for key in ['ubci', 'ubmi', 'ub10', 'ub30'])
        elif source_name == "USD/KRW 환율":
            return 'value' in data
        elif source_name == "글로벌 데이터":
            return any(key in data for key in ['total_market_cap', 'total_volume', 'btc_dominance'])
        elif source_name == "코인게코 데이터":
            # 이미 위에서 리스트 검증 완료
            return isinstance(data, list) and len(data) > 0 and all(isinstance(item, dict) for item in data)
            
        return True

    def _save_upbit_data(self, data: dict):
        """업비트 지수 데이터 DB 저장 (성능 최적화)"""
        if not data or not isinstance(data, dict):
            logger.warning("[DB 저장] 업비트 데이터가 비어있음")
            return
            
        save_start = datetime.now()
        try:
            # 전역 엔진 사용으로 성능 최적화
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                repo = MarketIndexRepository(session)
                
                indices_data = []
                name_mapping = {
                    'ubci': '업비트 종합지수',
                    'ubmi': '업비트 대형주지수', 
                    'ub10': '업비트 10지수',
                    'ub30': '업비트 30지수'
                }
                
                for code, index_data in data.items():
                    if code in name_mapping and isinstance(index_data, dict):
                        indices_data.append({
                            'index_type': MarketIndex.TYPE_UPBIT,
                            'code': code,
                            'name': name_mapping[code],
                            'value': index_data.get('value', 0),
                            'change': index_data.get('change', 0),
                            'change_rate': index_data.get('change_rate', 0)
                        })
                
                if indices_data:
                    repo.bulk_upsert(indices_data)
                    save_duration = (datetime.now() - save_start).total_seconds()
                    logger.info(f"[DB 저장] 업비트 지수 저장 완료: {len(indices_data)}개 (소요시간: {save_duration:.3f}초)")
                else:
                    logger.warning("[DB 저장] 업비트 지수 저장할 데이터 없음")
                    
            finally:
                session.close()
                
        except Exception as e:
            save_duration = (datetime.now() - save_start).total_seconds()
            logger.error(f"[DB 저장] ✗ 업비트 데이터 저장 실패 (소요시간: {save_duration:.3f}초): {e}")

    def _save_usd_krw_data(self, data: dict):
        """USD/KRW 환율 데이터 DB 저장 (성능 최적화)"""
        if not data or not isinstance(data, dict):
            logger.warning("[DB 저장] USD/KRW 데이터가 비어있음")
            return
            
        save_start = datetime.now()
        try:
            # 전역 엔진 사용으로 성능 최적화
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                repo = MarketIndexRepository(session)
                
                usd_krw_data = {
                    'index_type': MarketIndex.TYPE_USD,
                    'code': 'USD_KRW',
                    'name': 'USD/KRW 환율',
                    'value': data.get('value', 0),
                    'change': data.get('change', 0),
                    'change_rate': data.get('change_rate', 0)
                }
                
                repo.bulk_upsert([usd_krw_data])
                save_duration = (datetime.now() - save_start).total_seconds()
                logger.info(f"[DB 저장] USD/KRW 환율 저장 완료 (소요시간: {save_duration:.3f}초)")
                
            finally:
                session.close()
                
        except Exception as e:
            save_duration = (datetime.now() - save_start).total_seconds()
            logger.error(f"[DB 저장] ✗ USD/KRW 데이터 저장 실패 (소요시간: {save_duration:.3f}초): {e}")

    def _save_global_data(self, data: dict):
        """글로벌 암호화폐 데이터 DB 저장 (검증 강화)"""
        if not data or not isinstance(data, dict):
            logger.warning("[DB 저장] 글로벌 데이터가 비어있음")
            return

        # ⚠️ API 실패 시 빈 데이터로 덮어쓰기 방지
        # CoinGecko 429 에러 등으로 API 실패 시 empty data가 반환되는 경우
        # 이전의 정상 데이터를 보존하기 위해 저장하지 않음
        is_empty_data = (
            data.get('total_market_cap_usd', 0) == 0 and
            data.get('total_volume_usd', 0) == 0 and
            data.get('btc_dominance', 0) == 0
        )

        if is_empty_data:
            logger.warning("[DB 저장] 글로벌 데이터가 모두 0 - API 실패로 판단, DB 업데이트 스킵 (이전 데이터 보존)")
            return

        save_start = datetime.now()
        try:
            # 데이터 내용 상세 로깅 (디버깅용)
            logger.info(f"[DB 저장] 글로벌 데이터 수신 - 키 목록: {list(data.keys())}")
            logger.info(f"[DB 저장] 글로벌 데이터 내용: 시가총액=${data.get('total_market_cap_usd', 0):,.0f}, "
                       f"거래량=${data.get('total_volume_usd', 0):,.0f}, "
                       f"BTC도미넌스={data.get('btc_dominance', 0):.2f}%, "
                       f"24h변동={data.get('market_cap_change_24h', 0):.2f}%")
            
            # 전역 엔진 사용으로 성능 최적화
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                repo = MarketIndexRepository(session)
                
                indices_data = [
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'total_market_cap',
                        'name': '총 시가총액',
                        'value': data.get('total_market_cap_usd', 0),
                        'change_rate': 0.0  # 시가총액 자체는 변동률 없음
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'total_volume',
                        'name': '총 거래량',
                        'value': data.get('total_volume_usd', 0),
                        'change_rate': 0.0  # 거래량 자체는 변동률 없음
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'btc_dominance',
                        'name': 'BTC 도미넌스',
                        'value': data.get('btc_dominance', 0),
                        'change_rate': 0.0  # 도미넌스 자체는 변동률 없음
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'market_cap_change_24h',
                        'name': '시가총액 24h 변동',
                        'value': data.get('market_cap_change_24h', 0),
                        'change_rate': data.get('market_cap_change_24h', 0)  # 변동률 저장
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'volume_to_market_cap_ratio',
                        'name': '거래량-시가총액 비율',
                        'value': data.get('volume_to_market_cap_ratio', 0),
                        'change_rate': 0.0  # 비율 자체는 변동률 없음
                    }
                ]
                
                repo.bulk_upsert(indices_data)
                save_duration = (datetime.now() - save_start).total_seconds()
                logger.info(f"[DB 저장] 글로벌 지수 저장 완료: {len(indices_data)}개 (소요시간: {save_duration:.3f}초)")
                
            finally:
                session.close()
                
        except Exception as e:
            save_duration = (datetime.now() - save_start).total_seconds()
            logger.error(f"[DB 저장] 글로벌 데이터 저장 실패 (소요시간: {save_duration:.3f}초): {e}")

    def _save_coingecko_data(self, data: list):
        """
        CoinGecko 톱 코인 데이터 DB 저장
        
        범용 top_coins 코드 + api_source='coingecko'로 저장
        """
        self._save_coin_data(data, 'coingecko')
    
    def _save_coin_data(self, data: list, api_source: str = 'coingecko'):
        """
        코인 데이터 DB 저장 (범용 메서드)
        
        Args:
            data: 코인 데이터 리스트
            api_source: API 소스 ('binance' or 'coingecko')
        """
        if not data or not isinstance(data, list):
            logger.warning(f"[DB 저장] {api_source.upper()} 데이터가 비어있음")
            return

        save_start = datetime.now()
        try:
            # 데이터 내용 상세 로깅
            coin_names = [coin.get('symbol', 'unknown').upper() for coin in data[:5]] if data else []
            coin_prices = [coin.get('current_price', 0) for coin in data[:5]] if data else []
            logger.info(f"[DB 저장] {api_source.upper()} 데이터 수신: {len(data)}개 코인")
            logger.info(f"[DB 저장] 상위 5개 코인: {coin_names}, 가격: {coin_prices}")
            
            # 전역 엔진 사용으로 성능 최적화
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                repo = MarketIndexRepository(session)
                
                # 범용 top_coins 코드로 저장 (api_source로 구분)
                coin_data = {
                    'index_type': 'coin',
                    'code': 'top_coins',
                    'api_source': api_source,
                    'name': f'상위 코인 ({api_source.upper()})',
                    'value': len(data),  # 코인 개수
                    'change': 0.0,
                    'change_rate': 0.0,
                    'extra_data': json.dumps(data),
                    'ttl_seconds': 300  # 5분 TTL
                }
                
                repo.bulk_upsert([coin_data])
                save_duration = (datetime.now() - save_start).total_seconds()
                logger.info(f"[DB 저장] {api_source.upper()} 데이터 저장 완료: {len(data)}개 코인 (소요시간: {save_duration:.3f}초)")
                logger.debug(f"[DB 저장] 저장된 JSON 크기: {len(json.dumps(data))} bytes")
                
            finally:
                session.close()
                
        except Exception as e:
            save_duration = (datetime.now() - save_start).total_seconds()
            logger.error(f"[DB 저장] {api_source.upper()} 데이터 저장 실패 (소요시간: {save_duration:.3f}초): {e}")

    def _get_upbit_data_from_db(self) -> dict:
        """DB에서 업비트 지수 데이터 조회"""
        try:
            # 전역 엔진 사용으로 성능 최적화
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                repo = MarketIndexRepository(session)
                upbit_indices = repo.get_by_type(MarketIndex.TYPE_UPBIT)
                
                result: dict = {'timestamp': datetime.now()}
                for code in ['ubci', 'ubmi', 'ub10', 'ub30']:
                    cached = next((idx for idx in upbit_indices if idx.code == code), None)
                    if cached:
                        result[code] = {
                            'value': float(cached.value),
                            'change': float(cached.change),
                            'change_rate': float(cached.change_rate)
                        }
                    else:
                        result[code] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}
                
                return result
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"업비트 데이터 DB 조회 실패: {e}")
            return {'timestamp': datetime.now(), 'ubci': {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}, 
                   'ubmi': {'value': 0.0, 'change': 0.0, 'change_rate': 0.0},
                   'ub10': {'value': 0.0, 'change': 0.0, 'change_rate': 0.0},
                   'ub30': {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}}

    def _get_usd_krw_data_from_db(self) -> dict:
        """DB에서 USD/KRW 환율 데이터 조회"""
        try:
            # 전역 엔진 사용으로 성능 최적화
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                repo = MarketIndexRepository(session)
                usd_data = repo.get_by_code('USD_KRW')
                
                if usd_data:
                    return {
                        'value': float(usd_data.value),
                        'change': float(usd_data.change),
                        'change_rate': float(usd_data.change_rate)
                    }
                else:
                    return {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"USD/KRW 데이터 DB 조회 실패: {e}")
            return {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

    def _get_global_data_from_db(self) -> dict:
        """DB에서 글로벌 암호화폐 데이터 조회 (검증 강화)"""
        try:
            # 전역 엔진 사용으로 성능 최적화
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                repo = MarketIndexRepository(session)
                global_indices = repo.get_by_type(MarketIndex.TYPE_GLOBAL)

                result: dict = {'timestamp': datetime.now()}
                data_count = 0

                for idx in global_indices:
                    if idx.code == 'total_market_cap':
                        result['total_market_cap_usd'] = float(idx.value)
                        data_count += 1
                    elif idx.code == 'total_volume':
                        result['total_volume_usd'] = float(idx.value)
                        data_count += 1
                    elif idx.code == 'btc_dominance':
                        result['btc_dominance'] = float(idx.value)
                        data_count += 1
                    elif idx.code == 'market_cap_change_24h':
                        result['market_cap_change_24h'] = float(idx.value)
                        data_count += 1
                    elif idx.code == 'volume_to_market_cap_ratio':
                        result['volume_to_market_cap_ratio'] = float(idx.value)
                        data_count += 1

                # 데이터 검증 상세 로깅
                if data_count == 0:
                    logger.warning("[WebSocket] 글로벌 데이터 DB에서 데이터 없음 - DB에 저장된 레코드 없음")
                else:
                    logger.debug(f"[WebSocket] 글로벌 데이터 조회 완료: {data_count}개 항목 - "
                               f"시가총액=${result.get('total_market_cap_usd', 0):,.0f}, "
                               f"거래량=${result.get('total_volume_usd', 0):,.0f}, "
                               f"BTC도미넌스={result.get('btc_dominance', 0):.2f}%, "
                               f"거래량-시가총액 비율={result.get('volume_to_market_cap_ratio', 0):.2f}%")

                return result
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"[WebSocket] 글로벌 데이터 DB 조회 실패: {e}")
            return {'timestamp': datetime.now()}

    def _get_coingecko_data_from_db(self) -> list:
        """
        DB에서 코인게코 데이터 조회 (하위 호환용 alias)
        
        DEPRECATED: _get_coin_data_from_db() 사용 권장
        """
        return self._get_coin_data_from_db()

    def _get_coin_data_from_db(self) -> list:
        """
        DB에서 코인 데이터 조회 (범용 메서드)
        
        Binance 우선, CoinGecko fallback으로 조회
        
        Returns:
            list: 코인 데이터 리스트
        """
        try:
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                repo = MarketIndexRepository(session)
                
                # 1. Binance 데이터 우선 조회 (Primary)
                coin_data = repo.get_by_code_and_source('top_coins', 'binance')
                
                # 2. Binance 데이터 없으면 CoinGecko fallback
                if not coin_data or not coin_data.extra_data:
                    logger.debug("[WebSocket] Binance 데이터 없음 - CoinGecko fallback")
                    coin_data = repo.get_by_code_and_source('top_coins', 'coingecko')

                if coin_data and coin_data.extra_data:
                    try:
                        # extra_data에서 JSON 파싱
                        parsed_data = json.loads(coin_data.extra_data)

                        # 중첩된 JSON 문자열인 경우 한번 더 파싱
                        if isinstance(parsed_data, str):
                            logger.debug(f"[WebSocket] 중첩 JSON 감지 - 2차 파싱 시도")
                            parsed_data = json.loads(parsed_data)

                        coin_count = len(parsed_data) if isinstance(parsed_data, list) else 0
                        if coin_count > 0 and isinstance(parsed_data, list):
                            coin_symbols = [coin.get('symbol', 'N/A').upper() for coin in parsed_data[:5]]
                            api_source = coin_data.api_source or 'unknown'
                            logger.info(f"[WebSocket] 코인 데이터 조회 완료 (소스: {api_source}): {coin_count}개 - 상위 5개: {coin_symbols}")
                        else:
                            logger.warning(f"[WebSocket] 코인 데이터 형식 오류: 타입={type(parsed_data)}, 개수={coin_count}")
                        return parsed_data
                    except json.JSONDecodeError as e:
                        logger.warning(f"[WebSocket] 코인 데이터 JSON 파싱 실패: {e}")
                        return []
                else:
                    logger.warning("[WebSocket] 코인 데이터 DB에서 데이터 없음 (Binance/CoinGecko 모두)")
                    return []
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"[WebSocket] 코인 데이터 DB 조회 실패: {e}")
            return []


if __name__ == "__main__":
    print("=== 마켓 인덱스 스케줄러 테스트 ===\n")

    scheduler = MarketIndexScheduler()

    print("현재 설정:")
    print(f"  - 업데이트 주기: {scheduler.config.get_update_interval_minutes()}분")
    print(f"  - WebSocket URL: {scheduler.config.get_websocket_url()}\n")

    print("스케줄러 시작...")
    scheduler.start()

    print("\n30초 동안 대기 중... (Ctrl+C로 중단)")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass

    print("\n스케줄러 중지...")
    scheduler.stop()

    print("✓ 테스트 완료")
