"""
BTS 캐시 마켓 지수 서비스

DB 캐싱과 백그라운드 업데이트를 통한 빠른 지수 조회 제공
"""
import json
import threading
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from application.services.market_index_service import MarketIndexService
from infrastructure.repositories.market_index_repository import MarketIndexRepository
from infrastructure.database.connection import SessionLocal
from domain.entities.market_index import MarketIndex
from utils.logger import get_logger

logger = get_logger(__name__)


class CachedMarketIndexService:
    """
    캐시된 마켓 지수 서비스

    전략:
    1. 요청 시 DB에서 캐시된 데이터 우선 반환 (빠름)
    2. 데이터가 없거나 만료되었으면 백그라운드에서 업데이트 시작
    3. 업데이트 중에도 기존 데이터 제공 (stale-while-revalidate)
    """

    def __init__(self):
        self.market_service = MarketIndexService()
        self._update_locks = {}  # 코드별 업데이트 락

    def _get_repo(self) -> MarketIndexRepository:
        """Repository 인스턴스 생성 (새 세션)"""
        db = SessionLocal()
        return MarketIndexRepository(db)

    def _should_update(self, index_orm) -> bool:
        """업데이트 필요 여부 판단"""
        if not index_orm:
            return True

        expiry_time = index_orm.updated_at + timedelta(seconds=index_orm.ttl_seconds)
        return datetime.now() > expiry_time

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

    def get_upbit_indices_cached(self) -> Dict[str, any]:
        """
        업비트 지수 조회 (캐시 우선)

        Returns:
            dict: 업비트 지수 데이터 {'ubci': {...}, 'ubmi': {...}, ...}
        """
        repo = self._get_repo()

        try:
            # DB에서 캐시된 데이터 조회
            cached_indices = repo.get_by_type(MarketIndex.TYPE_UPBIT)

            result = {'timestamp': datetime.now()}
            needs_update = False

            # 4개 지수 확인
            for code in ['ubci', 'ubmi', 'ub10', 'ub30']:
                cached = next((idx for idx in cached_indices if idx.code == code), None)

                if cached and not self._should_update(cached):
                    # 캐시 유효 - 즉시 반환
                    result[code] = {
                        'value': float(cached.value),
                        'change': float(cached.change),
                        'change_rate': float(cached.change_rate)
                    }
                else:
                    # 캐시 없거나 만료됨
                    needs_update = True
                    if cached:
                        # 만료된 데이터라도 우선 반환 (stale-while-revalidate)
                        result[code] = {
                            'value': float(cached.value),
                            'change': float(cached.change),
                            'change_rate': float(cached.change_rate)
                        }
                    else:
                        result[code] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

            # 업데이트 필요하면 백그라운드에서 실행
            if needs_update and 'upbit_indices' not in self._update_locks:
                logger.info("업비트 지수 캐시 만료 - 백그라운드 업데이트 시작")
                self._update_locks['upbit_indices'] = True
                self._start_background_update(self._update_upbit_indices)

            return result

        except Exception as e:
            logger.error(f"업비트 지수 캐시 조회 실패: {e}")
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
                            'ttl_seconds': 300
                        })

                if indices_data:
                    repo.bulk_upsert(indices_data)
                    logger.info(f"업비트 지수 업데이트 완료: {len(indices_data)}개")

            finally:
                repo.db.close()

        except Exception as e:
            logger.error(f"업비트 지수 백그라운드 업데이트 실패: {e}")
        finally:
            self._update_locks.pop('upbit_indices', None)

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
            if 'usd_krw' not in self._update_locks:
                logger.info("USD/KRW 환율 캐시 만료 - 백그라운드 업데이트 시작")
                self._update_locks['usd_krw'] = True
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
                    ttl_seconds=300
                )
                logger.info("USD/KRW 환율 업데이트 완료")

            finally:
                repo.db.close()

        except Exception as e:
            logger.error(f"USD/KRW 환율 백그라운드 업데이트 실패: {e}")
        finally:
            self._update_locks.pop('usd_krw', None)

    # ===== 글로벌 지수 =====

    def get_global_crypto_data_cached(self) -> Dict[str, any]:
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

            if needs_update and 'global_crypto' not in self._update_locks:
                logger.info("글로벌 지수 캐시 만료 - 백그라운드 업데이트 시작")
                self._update_locks['global_crypto'] = True
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
                        'ttl_seconds': 300
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'total_volume',
                        'name': '24h 거래량',
                        'value': fresh_data['total_volume_usd'],
                        'extra_data': {'currency': 'USD'},
                        'ttl_seconds': 300
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'btc_dominance',
                        'name': 'BTC 도미넌스',
                        'value': fresh_data['btc_dominance'],
                        'ttl_seconds': 300
                    },
                    {
                        'index_type': MarketIndex.TYPE_GLOBAL,
                        'code': 'market_cap_change_24h',
                        'name': '시가총액 24h 변동',
                        'value': fresh_data.get('market_cap_change_24h', 0),
                        'ttl_seconds': 300
                    }
                ]

                repo.bulk_upsert(indices_data)
                logger.info("글로벌 지수 업데이트 완료")

            finally:
                repo.db.close()

        except Exception as e:
            logger.error(f"글로벌 지수 백그라운드 업데이트 실패: {e}")
        finally:
            self._update_locks.pop('global_crypto', None)

    # ===== 개별 코인 (캐시 우선 전략) =====

    def get_top_coins_with_sparkline_cached(
        self,
        limit: int = 10
    ) -> List[Dict[str, any]]:
        """
        상위 코인 데이터 조회 (실시간 조회, 캐싱 안 함)

        Note: sparkline 데이터는 실시간성이 중요하므로 캐싱하지 않음
        """
        return self.market_service.get_top_coins_with_sparkline(limit=limit)

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
        """모든 지수 강제 업데이트 (동기)"""
        logger.info("모든 지수 강제 업데이트 시작...")

        try:
            # 업비트 지수
            self._update_upbit_indices()

            # USD/KRW
            self._update_usd_krw()

            # 글로벌 지수
            self._update_global_crypto_data()

            logger.info("모든 지수 강제 업데이트 완료")

        except Exception as e:
            logger.error(f"강제 업데이트 실패: {e}")

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
