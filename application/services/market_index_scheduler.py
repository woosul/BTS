"""
BTS 마켓 인덱스 스케줄러

백그라운드에서 주기적으로 지수 업데이트 및 WebSocket 알림
"""
import asyncio
import threading
import time
from datetime import datetime
from typing import Set
import websockets

from application.services.cached_market_index_service import CachedMarketIndexService
from config.market_index_config import MarketIndexConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketIndexScheduler:
    """
    마켓 인덱스 백그라운드 스케줄러

    기능:
    1. 설정된 주기마다 자동으로 지수 업데이트
    2. 업데이트 완료 시 WebSocket으로 클라이언트에 알림
    """

    def __init__(self):
        self.service = CachedMarketIndexService()
        self.config = MarketIndexConfig()
        self.running = False
        self.update_thread = None
        self.websocket_thread = None
        self.websocket_loop = None  # WebSocket 이벤트 루프 참조
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()

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

    def update_all_indices(self):
        """모든 지수 업데이트"""
        try:
            logger.info(f"[스케줄러] 지수 업데이트 시작 ({datetime.now()})")
            self.service.force_update_all()
            logger.info("[스케줄러] 지수 업데이트 완료")

            # 업데이트된 데이터 조회
            upbit_data = self.service.get_upbit_indices_cached()
            usd_data = self.service.get_usd_krw_cached()
            global_data = self.service.get_global_crypto_data_cached()

            # datetime 객체 직렬화
            upbit_data = self._serialize_data(upbit_data)
            usd_data = self._serialize_data(usd_data)
            global_data = self._serialize_data(global_data)

            # JSON 메시지 구성
            import json
            message_data = {
                "type": "indices_updated",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "upbit": upbit_data,
                    "usd_krw": usd_data,
                    "global": global_data
                }
            }
            message_json = json.dumps(message_data, ensure_ascii=False)

            # WebSocket 클라이언트에 데이터 전송
            logger.info(f"[스케줄러] WebSocket 상태 - loop:{self.websocket_loop is not None}, clients:{len(self.connected_clients)}")
            if self.websocket_loop and not self.websocket_loop.is_closed():
                logger.info(f"[스케줄러] WebSocket 데이터 전송 시작 ({len(self.connected_clients)}명)")
                future = asyncio.run_coroutine_threadsafe(
                    self.notify_clients(message_json),
                    self.websocket_loop
                )
                try:
                    future.result(timeout=2)
                    logger.info("[스케줄러] WebSocket 데이터 전송 완료")
                except TimeoutError as e:
                    logger.error(f"[스케줄러] WebSocket 전송 타임아웃 (2초): {e}")
                except Exception as notify_error:
                    logger.error(f"[스케줄러] WebSocket 전송 실패: {type(notify_error).__name__}: {notify_error}", exc_info=True)
            else:
                logger.warning("[스케줄러] WebSocket 이벤트 루프 없음 - 전송 스킵")

        except Exception as e:
            logger.error(f"[스케줄러] 업데이트 실패: {e}")

    def run_scheduler(self):
        """스케줄러 메인 루프"""
        logger.info(f"✓ 지수 자동 업데이트 스케줄러 시작 (주기: {self.config.get_update_interval_minutes()}분)")

        # 시작 시 즉시 한 번 업데이트
        self.update_all_indices()

        while self.running:
            # UserSettings에서 동적으로 간격 조회
            interval_seconds = self.config.get_update_interval_seconds()
            time.sleep(interval_seconds)
            if self.running:  # 중단되지 않았으면 업데이트
                self.update_all_indices()

    def start_scheduler(self):
        """스케줄러 시작"""
        if self.running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        self.running = True
        self.update_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.update_thread.start()

    # ===== WebSocket 서버 =====

    async def handle_client(self, websocket):
        """WebSocket 클라이언트 연결 처리"""
        self.connected_clients.add(websocket)
        logger.info(f"WebSocket 클라이언트 연결: {websocket.remote_address}")

        try:
            # 연결 유지 (클라이언트로부터 메시지 대기)
            async for message in websocket:
                logger.debug(f"WebSocket 메시지 수신: {message}")
                if message == "ping":
                    await websocket.send("pong")
                    logger.debug("WebSocket pong 전송 완료")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"WebSocket 연결 비정상 종료: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket 연결 정상 종료")
        except Exception as e:
            logger.error(f"WebSocket 처리 중 오류: {e}")
        finally:
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)
            logger.info(f"WebSocket 클라이언트 연결 해제: {websocket.remote_address}")

    async def notify_clients(self, message: str):
        """연결된 모든 클라이언트에 알림"""
        if not self.connected_clients:
            logger.warning(f"WebSocket 알림 스킵: 연결된 클라이언트 없음 (message={message})")
            return

        logger.info(f"WebSocket 알림 전송: {message} ({len(self.connected_clients)}명)")

        # 모든 클라이언트에 메시지 전송
        results = await asyncio.gather(
            *[client.send(message) for client in self.connected_clients],
            return_exceptions=True
        )

        # 전송 결과 로깅
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            logger.error(f"WebSocket 알림 전송 중 {len(errors)}개 오류: {errors}")
        else:
            logger.info(f"WebSocket 알림 전송 완료 ({len(results)}명)")

    async def start_websocket_server(self):
        """WebSocket 서버 시작"""
        try:
            server = await websockets.serve(
                self.handle_client,
                self.config.WEBSOCKET_HOST,
                self.config.WEBSOCKET_PORT
            )
            logger.info(f"✓ WebSocket 서버 시작: {self.config.get_websocket_url()}")
            await server.wait_closed()
        except Exception as e:
            logger.error(f"WebSocket 서버 오류: {e}")

    def run_websocket_server(self):
        """WebSocket 서버 실행 (별도 스레드)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.websocket_loop = loop  # 이벤트 루프 참조 저장
        loop.run_until_complete(self.start_websocket_server())

    def start_websocket(self):
        """WebSocket 서버 시작"""
        self.websocket_thread = threading.Thread(target=self.run_websocket_server, daemon=True)
        self.websocket_thread.start()

    # ===== 제어 =====

    def start(self):
        """스케줄러 + WebSocket 서버 시작"""
        logger.info("=== 마켓 인덱스 백그라운드 시스템 시작 ===")
        self.start_scheduler()
        self.start_websocket()
        logger.info("=== 시작 완료 ===")

    def stop(self):
        """스케줄러 + WebSocket 서버 중지"""
        logger.info("마켓 인덱스 백그라운드 시스템 중지 중...")
        self.running = False

        if self.update_thread:
            self.update_thread.join(timeout=5)

        logger.info("중지 완료")

    def get_status(self) -> dict:
        """현재 상태 반환"""
        return {
            'running': self.running,
            'update_interval_minutes': self.config.get_update_interval_minutes(),
            'websocket_url': self.config.get_websocket_url(),
            'connected_clients': len(self.connected_clients)
        }


if __name__ == "__main__":
    print("=== 마켓 인덱스 스케줄러 테스트 ===\n")

    scheduler = MarketIndexScheduler()

    print(f"현재 설정:")
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
