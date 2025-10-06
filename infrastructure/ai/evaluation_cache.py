"""
BTS Evaluation Cache

AI 평가 결과 캐싱 시스템
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib
import json

from utils.logger import get_logger

logger = get_logger(__name__)


class EvaluationCache:
    """
    평가 결과 캐시

    동일한 데이터에 대한 중복 API 호출 방지
    """

    def __init__(self, ttl_minutes: int = 15):
        """
        초기화

        Args:
            ttl_minutes: 캐시 유효 시간 (분)
        """
        self.ttl = timedelta(minutes=ttl_minutes)
        self._cache: Dict[str, Dict] = {}

        logger.info(f"평가 캐시 초기화 | TTL: {ttl_minutes}분")

    def get(
        self,
        symbol: str,
        eval_type: str,
        context_hash: str
    ) -> Optional[Dict]:
        """
        캐시에서 평가 결과 조회

        Args:
            symbol: 거래 심볼
            eval_type: 평가 타입 (entry|exit)
            context_hash: 컨텍스트 해시

        Returns:
            Optional[Dict]: 캐시된 결과 (없으면 None)
        """
        cache_key = self._generate_key(symbol, eval_type, context_hash)

        if cache_key in self._cache:
            entry = self._cache[cache_key]

            # 만료 확인
            if datetime.now() - entry["timestamp"] < self.ttl:
                logger.debug(f"캐시 히트 | {symbol} | {eval_type}")
                return entry["result"]
            else:
                # 만료된 항목 삭제
                del self._cache[cache_key]
                logger.debug(f"캐시 만료 | {symbol} | {eval_type}")

        return None

    def set(
        self,
        symbol: str,
        eval_type: str,
        context_hash: str,
        result: Dict
    ):
        """
        평가 결과 캐싱

        Args:
            symbol: 거래 심볼
            eval_type: 평가 타입
            context_hash: 컨텍스트 해시
            result: 평가 결과
        """
        cache_key = self._generate_key(symbol, eval_type, context_hash)

        self._cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now()
        }

        logger.debug(f"캐시 저장 | {symbol} | {eval_type}")

    def invalidate(self, symbol: Optional[str] = None):
        """
        캐시 무효화

        Args:
            symbol: 특정 심볼만 무효화 (None이면 전체)
        """
        if symbol is None:
            # 전체 캐시 삭제
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"전체 캐시 무효화 | {count}개 항목 삭제")
        else:
            # 특정 심볼 캐시만 삭제
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(f"{symbol}_")
            ]

            for key in keys_to_delete:
                del self._cache[key]

            logger.info(f"{symbol} 캐시 무효화 | {len(keys_to_delete)}개 항목 삭제")

    def cleanup_expired(self):
        """만료된 캐시 항목 정리"""
        now = datetime.now()
        expired_keys = []

        for key, entry in self._cache.items():
            if now - entry["timestamp"] >= self.ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info(f"만료 캐시 정리 | {len(expired_keys)}개 항목 삭제")

    def get_stats(self) -> Dict:
        """
        캐시 통계 조회

        Returns:
            Dict: 통계 정보
        """
        now = datetime.now()
        valid_count = 0
        expired_count = 0

        for entry in self._cache.values():
            if now - entry["timestamp"] < self.ttl:
                valid_count += 1
            else:
                expired_count += 1

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_count,
            "expired_entries": expired_count,
            "ttl_minutes": self.ttl.total_seconds() / 60
        }

    def _generate_key(
        self,
        symbol: str,
        eval_type: str,
        context_hash: str
    ) -> str:
        """
        캐시 키 생성

        Args:
            symbol: 거래 심볼
            eval_type: 평가 타입
            context_hash: 컨텍스트 해시

        Returns:
            str: 캐시 키
        """
        return f"{symbol}_{eval_type}_{context_hash}"

    @staticmethod
    def hash_context(data: Dict) -> str:
        """
        컨텍스트 데이터를 해시로 변환

        Args:
            data: 컨텍스트 데이터

        Returns:
            str: SHA256 해시 (앞 16자리)
        """
        # JSON 문자열로 변환 (정렬하여 일관성 보장)
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)

        # SHA256 해시
        hash_obj = hashlib.sha256(json_str.encode('utf-8'))

        # 앞 16자리만 사용 (충분히 고유함)
        return hash_obj.hexdigest()[:16]

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<EvaluationCache(entries={stats['total_entries']}, "
            f"valid={stats['valid_entries']}, ttl={stats['ttl_minutes']}min)>"
        )


if __name__ == "__main__":
    print("=== Evaluation Cache 테스트 ===")

    import time

    # 캐시 생성 (TTL 1분)
    cache = EvaluationCache(ttl_minutes=1)

    # 테스트 데이터
    test_context = {
        "current_price": 50000000,
        "indicators": {"rsi": 65.5}
    }

    context_hash = EvaluationCache.hash_context(test_context)
    print(f"\n컨텍스트 해시: {context_hash}")

    # 평가 결과
    test_result = {
        "recommendation": "buy",
        "confidence": 75,
        "reasoning": "테스트 평가"
    }

    # 캐시 저장
    print("\n[캐시 저장]")
    cache.set("KRW-BTC", "entry", context_hash, test_result)
    print(cache)

    # 캐시 조회 (히트)
    print("\n[캐시 조회 - 히트]")
    cached = cache.get("KRW-BTC", "entry", context_hash)
    print(f"결과: {cached}")

    # 다른 컨텍스트 (미스)
    print("\n[캐시 조회 - 미스]")
    different_context = {
        "current_price": 51000000,
        "indicators": {"rsi": 70.0}
    }
    different_hash = EvaluationCache.hash_context(different_context)
    cached = cache.get("KRW-BTC", "entry", different_hash)
    print(f"결과: {cached}")

    # 통계
    print("\n[캐시 통계]")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 만료 테스트
    print("\n[만료 테스트]")
    print("60초 대기 중...")
    time.sleep(61)

    cached = cache.get("KRW-BTC", "entry", context_hash)
    print(f"만료 후 조회: {cached}")

    # 정리
    cache.cleanup_expired()
    print(f"\n정리 후: {cache}")

    # 무효화 테스트
    print("\n[무효화 테스트]")
    cache.set("KRW-BTC", "entry", context_hash, test_result)
    cache.set("KRW-ETH", "entry", "hash123", test_result)
    print(f"저장 후: {cache}")

    cache.invalidate("KRW-BTC")
    print(f"KRW-BTC 무효화 후: {cache}")

    cache.invalidate()
    print(f"전체 무효화 후: {cache}")
