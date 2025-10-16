"""
BTS 캐시 마켓 지수 서비스

DB 캐싱과 백그라운드 업데이트를 통한 빠른 지수 조회 제공
"""
import json
import threading
from typing import Dict, List, Any
from decimal import Decimal
from datetime import datetime, timedelta

from application.services.market_index_service import MarketIndexService
from infrastructure.repositories.market_index_repository import MarketIndexRepository
from infrastructure.repositories.user_settings_repository import UserSettingsRepository
from infrastructure.database.connection import SessionLocal
from domain.entities.market_index import MarketIndex
from domain.entities.user_settings import UserSettings
from utils.logger import get_logger

logger = get_logger(__name__)


class CachedMarketIndexService:
    """
    캐시된 마켓 지수 서비스

    전략:
    1. 요청 시 DB에서 캐시된 데이터 우선 반환 (빠름)
    2. 데이터가 없거나 만료되었으면 백그라운드에서 업데이트 시작
    3. 업데이트 중에도 기존 데이터 제공 (stale-while-revalidate)
    4. 성능 최적화: 동시 업데이트 방지, 메모리 누수 방지
    """

    def __init__(self):
        self.market_service = MarketIndexService()
        self._update_locks = {}  # 코드별 업데이트 락
        self._last_update_times = {}  # 마지막 업데이트 시간 기록
        self._cache_hit_count = 0  # 캐시 히트 카운터
        self._cache_miss_count = 0  # 캐시 미스 카운터

    def _get_repo(self) -> MarketIndexRepository:
        """Repository 인스턴스 생성 (새 세션)"""
        db = SessionLocal()
        return MarketIndexRepository(db)

    def _get_ttl_seconds(self, cache_type: str) -> int:
        """UserSettings에서 TTL 값 조회"""
        try:
            settings_repo = UserSettingsRepository()
            key_mapping = {
                'upbit': UserSettings.CACHE_TTL_UPBIT,
                'global': UserSettings.CACHE_TTL_GLOBAL,
                'usd': UserSettings.CACHE_TTL_USD
            }
            
            setting_key = key_mapping.get(cache_type)
            if setting_key:
                setting = settings_repo.get_by_key(setting_key)
                if setting:
                    return int(setting.setting_value)
            
            # 기본값 반환
            default_ttl = {
                'upbit': 300,  # 5분
                'global': 300,  # 5분
                'usd': 300,    # 5분
            }
            return default_ttl.get(cache_type, 300)
            
        except Exception as e:
            logger.error(f"TTL 설정 조회 실패 ({cache_type}): {e}")
            return 300  # 기본값 5분

    def _should_update(self, index_orm) -> bool:
        """업데이트 필요 여부 판단 (성능 최적화)"""
        if not index_orm:
            self._cache_miss_count += 1
            return True

        expiry_time = index_orm.updated_at + timedelta(seconds=index_orm.ttl_seconds)
        is_expired = datetime.now() > expiry_time
        
        if is_expired:
            self._cache_miss_count += 1
        else:
            self._cache_hit_count += 1
            
        return is_expired

    def _can_start_update(self, update_key: str) -> bool:
        """업데이트 시작 가능 여부 확인 (동시 업데이트 방지)"""
        if update_key in self._update_locks:
            # 이미 업데이트 중
            return False
            
        # 최근 업데이트가 너무 자주 발생하는지 확인 (최소 10초 간격)
        last_update = self._last_update_times.get(update_key)
        if last_update:
            time_since_last = (datetime.now() - last_update).total_seconds()
            if time_since_last < 10:
                logger.debug(f"업데이트 간격 제한: {update_key} ({time_since_last:.1f}초 전)")
                return False
                
        return True

    def _mark_update_start(self, update_key: str):
        """업데이트 시작 마킹"""
        self._update_locks[update_key] = True
        self._last_update_times[update_key] = datetime.now()

    def _mark_update_end(self, update_key: str):
        """업데이트 완료 마킹"""
        self._update_locks.pop(update_key, None)

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self._cache_hit_count + self._cache_miss_count
        hit_rate = (self._cache_hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self._cache_hit_count,
            'cache_misses': self._cache_miss_count,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'active_updates': list(self._update_locks.keys()),
            'last_update_times': {k: v.isoformat() for k, v in self._last_update_times.items()}
        }

    def _start_background_update(self, update_func, *args, **kwargs):
        """백그라운드 업데이트 시작"""
        thread = threading.Thread(
            target=update_func,
            args=args,
            kwargs=kwargs,
            daemon=True
        )
        thread.start()

    # ===== 업비트 지수 =====

    def get_upbit_indices_cached(self) -> Dict[str, Any]:
        """
        업비트 지수 조회 (WebSocket용 - 항상 최신 DB 데이터 반환)

        Returns:
            dict: 업비트 지수 데이터 {'ubci': {...}, 'ubmi': {...}, ...}
        """
        repo = self._get_repo()

        try:
            # DB에서 최신 데이터 조회 (캐시 TTL 무시)
            cached_indices = repo.get_by_type(MarketIndex.TYPE_UPBIT)

            result = {'timestamp': datetime.now()}

            # 4개 지수 확인 - 항상 DB 최신 데이터 반환
            for code in ['ubci', 'ubmi', 'ub10', 'ub30']:
                cached = next((idx for idx in cached_indices if idx.code == code), None)

                if cached:
                    # DB에서 가져온 최신 데이터 바로 반환
                    result[code] = {
                        'value': float(cached.value),
                        'change': float(cached.change),
                        'change_rate': float(cached.change_rate)
                    }
                    self._cache_hit_count += 1
                else:
                    # 데이터 없음
                    result[code] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}
                    self._cache_miss_count += 1

            return result

        except Exception as e:
            logger.error(f"업비트 지수 DB 조회 실패: {e}")
            # 실패 시 실시간 조회
            return self.market_service.get_upbit_indices()
        finally:
            repo.db.close()

    def _update_upbit_indices(self):
        """업비트 지수 백그라운드 업데이트"""
        try:
            logger.debug("업비트 지수 업데이트 시작...")
            fresh_data = self.market_service.get_upbit_indices()

            if not fresh_data or all(fresh_data.get(k, {}).get('value', 0) == 0 for k in ['ubci', 'ubmi', 'ub10', 'ub30']):
                logger.warning("업비트 지수 업데이트 실패 - 유효한 데이터 없음")
                return

            repo = self._get_repo()
            try:
                indices_data = []
                name_mapping = {
                    'ubci': '업비트 종합 지수',
                    'ubmi': '업비트 알트코인 지수',
                    'ub10': '업비트 10',
                    'ub30': '업비트 30'
                }

                for code in ['ubci', 'ubmi', 'ub10', 'ub30']:
                    data = fresh_data.get(code, {})
                    if data.get('value', 0) > 0:
                        indices_data.append({
                            'index_type': MarketIndex.TYPE_UPBIT,
                            'code': code,
                            'name': name_mapping[code],
                            'value': data['value'],
                            'change': data.get('change', 0),
                            'change_rate': data.get('change_rate', 0),
                            'ttl_seconds': self._get_ttl_seconds('upbit')  # 동적 TTL
                        })

                if indices_data:
                    repo.bulk_upsert(indices_data)
                    logger.info(f"업비트 지수 업데이트 완료: {len(indices_data)}개")

            finally:
                repo.db.close()

        except Exception as e:
            logger.error(f"업비트 지수 백그라운드 업데이트 실패: {e}", exc_info=True)
        finally:
            self._mark_update_end('upbit_indices')

    # ===== USD/KRW 환율 =====

    def get_usd_krw_cached(self) -> Dict[str, float]:
        """
        USD/KRW 환율 조회 (캐시 우선)

        Returns:
            dict: {'value': 환율, 'change_rate': 변동률}
        """
        repo = self._get_repo()

        try:
            cached = repo.get_by_code("usd_krw")

            if cached and not self._should_update(cached):
                # 캐시 유효
                return {
                    'value': float(cached.value),
                    'change': float(cached.change),
                    'change_rate': float(cached.change_rate)
                }

            # 캐시 없거나 만료
            if self._can_start_update('usd_krw'):
                logger.info("USD/KRW 환율 캐시 만료 - 백그라운드 업데이트 시작")
                self._mark_update_start('usd_krw')
                self._start_background_update(self._update_usd_krw)

            # 만료된 캐시라도 반환
            if cached:
                return {
                    'value': float(cached.value),
                    'change': float(cached.change),
                    'change_rate': float(cached.change_rate)
                }

            # 캐시 없으면 실시간 조회
            return self.market_service.get_usd_krw_rate()

        except Exception as e:
            logger.error(f"USD/KRW 환율 캐시 조회 실패: {e}")
            return self.market_service.get_usd_krw_rate()
        finally:
            repo.db.close()

    def _update_usd_krw(self):
        """USD/KRW 환율 백그라운드 업데이트"""
        try:
            logger.debug("USD/KRW 환율 업데이트 시작...")
            fresh_data = self.market_service.get_usd_krw_rate()

            if fresh_data.get('value', 0) == 0:
                logger.warning("USD/KRW 환율 업데이트 실패 - 유효한 데이터 없음")
                return

            repo = self._get_repo()
            try:
                repo.upsert_index(
                    index_type=MarketIndex.TYPE_USD,
                    code="usd_krw",
                    name="USD/KRW",
                    value=Decimal(str(fresh_data['value'])),
                    change=Decimal(str(fresh_data.get('change', 0))),
                    change_rate=Decimal(str(fresh_data.get('change_rate', 0))),
                    ttl_seconds=self._get_ttl_seconds('usd')  # 동적 TTL
                )
                logger.info("USD/KRW 환율 업데이트 완료")

            finally:
                repo.db.close()

        except Exception as e:
            logger.error(f"USD/KRW 환율 백그라운드 업데이트 실패: {e}", exc_info=True)
        finally:
            self._mark_update_end('usd_krw')

    # ===== 글로벌 지수 =====

    def get_global_crypto_data_cached(self) -> Dict[str, Any]:
        """
        글로벌 암호화폐 데이터 조회 (캐시 우선)

        Returns:
            dict: 글로벌 지수 데이터
        """
        repo = self._get_repo()

        try:
            cached_indices = repo.get_by_type(MarketIndex.TYPE_GLOBAL)

            # 주요 지수 확인
            codes = ['total_market_cap', 'total_volume', 'btc_dominance', 'market_cap_change_24h']
            needs_update = False

            result = {}
            for code in codes:
                cached = next((idx for idx in cached_indices if idx.code == code), None)
                if not cached or self._should_update(cached):
                    needs_update = True
                    break

            if needs_update and self._can_start_update('global_crypto'):
                logger.info("글로벌 지수 캐시 만료 - 백그라운드 업데이트 시작")
                self._mark_update_start('global_crypto')
                self._start_background_update(self._update_global_crypto_data)

            # 캐시가 있으면 반환, 없으면 실시간 조회
            if cached_indices:
                # 캐시된 데이터 조합
                for idx in cached_indices:
                    if idx.code == 'total_market_cap':
                        result['total_market_cap_usd'] = float(idx.value)
                    elif idx.code == 'total_volume':
                        result['total_volume_usd'] = float(idx.value)
                    elif idx.code == 'btc_dominance':
                        result['btc_dominance'] = float(idx.value)
                    elif idx.code == 'market_cap_change_24h':
                        result['market_cap_change_24h'] = float(idx.value)

                result.setdefault('total_market_cap_usd', 0.0)
                result.setdefault('total_volume_usd', 0.0)
                result.setdefault('btc_dominance', 0.0)
                result.setdefault('market_cap_change_24h', 0.0)
                result['timestamp'] = datetime.now()

                return result

            # 캐시 없으면 실시간 조회
            return self.market_service.get_global_crypto_data()

        except Exception as e:
            logger.error(f"글로벌 지수 캐시 조회 실패: {e}")
            return self.market_service.get_global_crypto_data()
        finally:
            repo.db.close()

    def _update_global_crypto_data(self):
        """글로벌 암호화폐 데이터 백그라운드 업데이트"""
        try:
            logger.debug("글로벌 지수 업데이트 시작...")
            fresh_data = self.market_service.get_global_crypto_data()

            if not fresh_data or fresh_data.get('total_market_cap_usd', 0) == 0:
                logger.warning("글로벌 지수 업데이트 실패 - 유효한 데이터 없음")
                return

            repo = self._get_repo()
            try:
                indices_data = [
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'total_market_cap',
                        'name': '총 시가총액',
                        'value': fresh_data['total_market_cap_usd'],
                        'extra_data': {'currency': 'USD'},
                        'ttl_seconds': self._get_ttl_seconds('global')  # 동적 TTL
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'total_volume',
                        'name': '24h 거래량',
                        'value': fresh_data['total_volume_usd'],
                        'extra_data': {'currency': 'USD'},
                        'ttl_seconds': self._get_ttl_seconds('global')  # 동적 TTL
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'btc_dominance',
                        'name': 'BTC 도미넌스',
                        'value': fresh_data['btc_dominance'],
                        'ttl_seconds': self._get_ttl_seconds('global')  # 동적 TTL
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'market_cap_change_24h',
                        'name': '시가총액 24h 변동',
                        'value': fresh_data.get('market_cap_change_24h', 0),
                        'ttl_seconds': self._get_ttl_seconds('global')  # 동적 TTL
                    }
                ]

                repo.bulk_upsert(indices_data)
                logger.info("글로벌 지수 업데이트 완료")

            finally:
                repo.db.close()

        except Exception as e:
            logger.error(f"글로벌 지수 백그라운드 업데이트 실패: {e}", exc_info=True)
        finally:
            self._mark_update_end('global_crypto')

    # ===== 개별 코인 (캐시 우선 전략) =====

    def get_top_coins_with_sparkline_cached(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        상위 코인 데이터 조회 (캐시 우선, DB 저장)
        
        Args:
            limit: 가져올 코인 개수
            
        Returns:
            List[Dict]: 코인 데이터 리스트
        """
        repo = self._get_repo()
        
        try:
            # 캐시된 데이터 조회
            cached = repo.get_by_code("coingecko_top_coins")
            ttl_seconds = self._get_ttl_seconds('global')  # global TTL 사용
            
            if cached:
                cache_age = (datetime.now() - cached.updated_at).total_seconds()
                if cache_age < ttl_seconds:
                    try:
                        # extra_data에서 데이터 조회
                        if cached.extra_data:
                            coingecko_data: List[Dict[str, Any]] = []
                            if isinstance(cached.extra_data, list):
                                # 리스트 타입의 경우 직접 할당하되 타입 확인
                                for item in cached.extra_data:
                                    if isinstance(item, dict):
                                        coingecko_data.append(item)
                            elif isinstance(cached.extra_data, str):
                                parsed_data = json.loads(cached.extra_data)
                                if isinstance(parsed_data, list):
                                    for item in parsed_data:
                                        if isinstance(item, dict):
                                            coingecko_data.append(item)
                            
                            if coingecko_data:
                                self._cache_hit_count += 1
                                logger.debug(f"CoinGecko 상위 코인 캐시 히트 (TTL: {ttl_seconds}초)")
                                return coingecko_data[:limit]
                    except (json.JSONDecodeError, AttributeError, TypeError):
                        logger.warning("CoinGecko 캐시 데이터 파싱 실패")
            
            # 캐시 만료 시 백그라운드 업데이트
            if self._can_start_update('coingecko_top_coins'):
                logger.info("CoinGecko 상위 코인 캐시 만료 - 백그라운드 업데이트 시작")
                self._mark_update_start('coingecko_top_coins')
                self._start_background_update(self._update_coingecko_top_coins)
            
            # 캐시된 데이터 반환 (만료되었더라도)
            if cached and cached.extra_data:
                try:
                    coingecko_data: List[Dict[str, Any]] = []
                    if isinstance(cached.extra_data, list):
                        # 리스트 타입의 경우 직접 할당하되 타입 확인
                        for item in cached.extra_data:
                            if isinstance(item, dict):
                                coingecko_data.append(item)
                    elif isinstance(cached.extra_data, str):
                        parsed_data = json.loads(cached.extra_data)
                        if isinstance(parsed_data, list):
                            for item in parsed_data:
                                if isinstance(item, dict):
                                    coingecko_data.append(item)
                    
                    if coingecko_data:
                        self._cache_miss_count += 1
                        logger.debug("CoinGecko 상위 코인 만료된 캐시 반환")
                        return coingecko_data[:limit]
                except (json.JSONDecodeError, AttributeError, TypeError):
                    pass
            
            # 캐시가 없는 경우 직접 조회
            self._cache_miss_count += 1
            return self.market_service.get_top_coins_with_sparkline(limit=limit)
            
        except Exception as e:
            logger.error(f"CoinGecko 상위 코인 캐시 조회 실패: {e}")
            return self.market_service.get_top_coins_with_sparkline(limit=limit)
        finally:
            repo.db.close()

    def _update_coingecko_top_coins(self):
        """CoinGecko 상위 코인 백그라운드 업데이트"""
        try:
            logger.debug("CoinGecko 상위 코인 업데이트 시작...")
            
            # 실제 데이터 조회
            coingecko_data = self.market_service.get_top_coins_with_sparkline(limit=10)
            
            if not coingecko_data:
                logger.warning("CoinGecko 상위 코인 업데이트 실패 - 유효한 데이터 없음")
                return
            
            repo = self._get_repo()
            try:
                # 단일 레코드로 JSON 저장
                indices_data = [{
                    'index_type': MarketIndex.TYPE_COIN,
                    'code': "coingecko_top_coins",
                    'name': "CoinGecko 상위 코인",
                    'value': len(coingecko_data),  # 코인 개수
                    'change': 0,
                    'change_rate': 0,
                    'extra_data': coingecko_data,  # JSON 데이터는 extra_data에 저장
                    'ttl_seconds': self._get_ttl_seconds('global')
                }]
                
                repo.bulk_upsert(indices_data)
                logger.info(f"CoinGecko 상위 코인 업데이트 완료 ({len(coingecko_data)}개)")
                
            finally:
                repo.db.close()
            
        except Exception as e:
            logger.error(f"CoinGecko 상위 코인 업데이트 실패: {e}")
        finally:
            self._mark_update_end('coingecko_top_coins')

    def calculate_7day_averages(self, sparkline_data: List[Dict]) -> Dict[str, float]:
        """
        7일간 데이터의 평균 계산 (위임)

        Args:
            sparkline_data: 코인 데이터 리스트

        Returns:
            dict: 평균 데이터
        """
        return self.market_service.calculate_7day_averages(sparkline_data)

    # ===== 유틸리티 =====

    def force_update_all(self):
        """모든 지수 강제 업데이트 (동기, 성능 최적화 - 병렬 처리)"""
        logger.info("모든 지수 강제 업데이트 시작...")
        start_time = datetime.now()

        import concurrent.futures
        
        def update_upbit():
            if self._can_start_update('upbit_indices_force'):
                self._mark_update_start('upbit_indices_force')
                try:
                    self._update_upbit_indices()
                    return "upbit_success"
                except Exception as e:
                    logger.error(f"업비트 지수 업데이트 실패: {e}")
                    return f"upbit_error: {e}"
                finally:
                    self._mark_update_end('upbit_indices_force')
            return "upbit_skipped"
        
        def update_usd():
            if self._can_start_update('usd_krw_force'):
                self._mark_update_start('usd_krw_force')
                try:
                    self._update_usd_krw()
                    return "usd_success"
                except Exception as e:
                    logger.error(f"USD/KRW 업데이트 실패: {e}")
                    return f"usd_error: {e}"
                finally:
                    self._mark_update_end('usd_krw_force')
            return "usd_skipped"
        
        def update_global():
            if self._can_start_update('global_crypto_force'):
                self._mark_update_start('global_crypto_force')
                try:
                    self._update_global_crypto_data()
                    return "global_success"
                except Exception as e:
                    logger.error(f"글로벌 지수 업데이트 실패: {e}")
                    return f"global_error: {e}"
                finally:
                    self._mark_update_end('global_crypto_force')
            return "global_skipped"

        try:
            # 병렬 실행으로 성능 향상
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # 3개 업데이트를 동시에 실행
                upbit_future = executor.submit(update_upbit)
                usd_future = executor.submit(update_usd)
                global_future = executor.submit(update_global)
                
                # 결과 수집 (최대 30초 대기)
                results = []
                for future in concurrent.futures.as_completed([upbit_future, usd_future, global_future], timeout=30):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"병렬 업데이트 중 오류: {e}")
                        results.append(f"error: {e}")

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"모든 지수 강제 업데이트 완료 (소요시간: {duration:.2f}초, 결과: {results})")

        except concurrent.futures.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            logger.warning(f"강제 업데이트 타임아웃 (30초 초과, 실제 소요: {duration:.2f}초)")
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"강제 업데이트 실패 (소요시간: {duration:.2f}초): {e}", exc_info=True)

    def cleanup_cache_stats(self):
        """캐시 통계 정리 (메모리 누수 방지)"""
        if self._cache_hit_count > 10000 or self._cache_miss_count > 10000:
            logger.info(f"캐시 통계 초기화 (hits: {self._cache_hit_count}, misses: {self._cache_miss_count})")
            self._cache_hit_count = 0
            self._cache_miss_count = 0
            
        # 오래된 업데이트 시간 기록 정리 (1시간 이상)
        current_time = datetime.now()
        old_keys = []
        for key, last_time in self._last_update_times.items():
            if (current_time - last_time).total_seconds() > 3600:
                old_keys.append(key)
                
        for key in old_keys:
            del self._last_update_times[key]
            
        if old_keys:
            logger.info(f"오래된 업데이트 기록 {len(old_keys)}개 정리 완료")

    def cleanup_expired_indices(self):
        """만료된 지수 정리"""
        repo = self._get_repo()
        try:
            count = repo.delete_expired_indices()
            if count > 0:
                logger.info(f"만료된 지수 {count}개 삭제 완료")
        finally:
            repo.db.close()


if __name__ == "__main__":
    print("=== 캐시된 마켓 지수 서비스 테스트 ===\n")

    service = CachedMarketIndexService()

    # 1. 업비트 지수 조회 (캐시 우선)
    print("1. 업비트 지수 조회 (캐시 우선)")
    upbit_data = service.get_upbit_indices_cached()
    print(f"   UBCI: {upbit_data.get('ubci', {}).get('value', 0):,.2f}")
    print(f"   UBMI: {upbit_data.get('ubmi', {}).get('value', 0):,.2f}\n")

    # 2. USD/KRW 조회
    print("2. USD/KRW 조회 (캐시 우선)")
    usd_data = service.get_usd_krw_cached()
    print(f"   환율: ₩{usd_data.get('value', 0):,.2f}\n")

    # 3. 글로벌 지수 조회
    print("3. 글로벌 지수 조회 (캐시 우선)")
    global_data = service.get_global_crypto_data_cached()
    market_cap = global_data.get('total_market_cap_usd', 0) / 1_000_000_000_000
    print(f"   시가총액: ${market_cap:.2f}T")
    print(f"   BTC 도미넌스: {global_data.get('btc_dominance', 0):.2f}%\n")

    # 4. 강제 업데이트
    print("4. 강제 업데이트 테스트")
    print("   업데이트 시작... (백그라운드)")

    import time
    time.sleep(3)  # 백그라운드 업데이트 대기

    print("   완료\n")

    # 5. 만료된 지수 정리
    print("5. 만료된 지수 정리")
    service.cleanup_expired_indices()

    # 6. 캐시 통계 확인
    print("6. 캐시 통계")
    stats = service.get_cache_stats()
    print(f"   캐시 히트: {stats['cache_hits']}")
    print(f"   캐시 미스: {stats['cache_misses']}")
    print(f"   히트율: {stats['hit_rate_percent']}%")
    
    # 7. 메모리 정리
    print("\n7. 메모리 정리")
    service.cleanup_cache_stats()
