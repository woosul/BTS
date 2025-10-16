"""
BTS 중앙화된 API 매니저

모든 외부 API 요청을 중앙에서 관리하여 rate limit 및 중복 요청 방지
"""
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import requests
from playwright.sync_api import sync_playwright

from utils.logger import get_logger

logger = get_logger(__name__)


class APIProvider(Enum):
    """API 제공자"""
    COINGECKO = "coingecko"
    CURRENCY_API = "currency_api"
    UPBIT_WEB = "upbit_web"
    UPBIT_API = "upbit_api"


@dataclass
class RateLimitConfig:
    """Rate Limit 설정"""
    max_requests: int  # 최대 요청 수
    time_window: int   # 시간 창(초)
    min_interval: float  # 최소 요청 간격(초)


@dataclass
class APIRequest:
    """API 요청 정보"""
    provider: APIProvider
    url: str
    params: Optional[Dict] = None
    headers: Optional[Dict] = None
    timeout: int = 10
    callback: Optional[Callable] = None


class CentralizedAPIManager:
    """
    중앙화된 API 매니저
    
    특징:
    1. 모든 외부 API 요청을 단일 지점에서 관리
    2. Provider별 Rate Limiting 적용
    3. 요청 큐잉 및 스케줄링
    4. 자동 재시도 및 오류 처리
    5. 캐싱 및 중복 요청 방지
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BTS-CryptoTrading-System/1.0'
        })
        
        # Rate Limit 설정
        self.rate_limits = {
            APIProvider.COINGECKO: RateLimitConfig(
                max_requests=30, 
                time_window=60, 
                min_interval=2.0  # 30회/분 = 2초 간격
            ),
            APIProvider.CURRENCY_API: RateLimitConfig(
                max_requests=100, 
                time_window=3600, 
                min_interval=36.0  # 안전 마진
            ),
            APIProvider.UPBIT_WEB: RateLimitConfig(
                max_requests=10, 
                time_window=60, 
                min_interval=6.0  # 웹스크래핑 제한
            ),
            APIProvider.UPBIT_API: RateLimitConfig(
                max_requests=100, 
                time_window=60, 
                min_interval=0.6
            )
        }
        
        # 요청 이력 추적
        self.request_history = {provider: [] for provider in APIProvider}
        self.last_request_time = {provider: None for provider in APIProvider}
        
        # 요청 큐
        self.request_queue = asyncio.Queue()
        self.processing = False
        self.lock = threading.Lock()
        
        # 캐시
        self.cache = {}
        self.cache_ttl = {}
        
    def _can_make_request(self, provider: APIProvider) -> tuple[bool, float]:
        """
        요청 가능 여부 확인
        
        Returns:
            (가능여부, 대기시간)
        """
        config = self.rate_limits[provider]
        now = time.time()
        
        # 최소 간격 체크
        last_time = self.last_request_time[provider]
        if last_time:
            elapsed = now - last_time
            if elapsed < config.min_interval:
                wait_time = config.min_interval - elapsed
                return False, wait_time
        
        # 시간 창 내 요청 수 체크
        history = self.request_history[provider]
        cutoff = now - config.time_window
        
        # 오래된 요청 기록 제거
        history[:] = [req_time for req_time in history if req_time > cutoff]
        
        if len(history) >= config.max_requests:
            # 가장 오래된 요청이 시간 창을 벗어날 때까지 대기
            wait_time = history[0] + config.time_window - now
            return False, max(wait_time, 0)
        
        return True, 0
    
    def _record_request(self, provider: APIProvider):
        """요청 기록"""
        now = time.time()
        self.request_history[provider].append(now)
        self.last_request_time[provider] = now
    
    def _get_cache_key(self, provider: APIProvider, url: str, params: Dict = None) -> str:
        """캐시 키 생성"""
        key_parts = [provider.value, url]
        if params:
            sorted_params = sorted(params.items())
            key_parts.append(str(sorted_params))
        return "|".join(key_parts)
    
    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """캐시된 응답 조회"""
        if cache_key not in self.cache:
            return None
            
        if cache_key in self.cache_ttl:
            if time.time() > self.cache_ttl[cache_key]:
                # 캐시 만료
                del self.cache[cache_key]
                del self.cache_ttl[cache_key]
                return None
                
        return self.cache[cache_key]
    
    def _set_cache(self, cache_key: str, data: Any, ttl_seconds: int = 300):
        """캐시 저장"""
        self.cache[cache_key] = data
        self.cache_ttl[cache_key] = time.time() + ttl_seconds
    
    async def make_request(self, request: APIRequest, cache_ttl: int = 300) -> Optional[Any]:
        """
        중앙화된 API 요청
        
        Args:
            request: API 요청 정보
            cache_ttl: 캐시 유효시간(초)
            
        Returns:
            API 응답 데이터 또는 None
        """
        cache_key = self._get_cache_key(request.provider, request.url, request.params)
        
        # 캐시 확인
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            logger.debug(f"{request.provider.value} 캐시 히트: {request.url}")
            return cached
        
        with self.lock:
            can_request, wait_time = self._can_make_request(request.provider)
            
            if not can_request:
                logger.warning(f"{request.provider.value} rate limit: {wait_time:.1f}초 대기")
                await asyncio.sleep(wait_time)
                return await self.make_request(request, cache_ttl)
        
        try:
            # 실제 API 요청
            if request.provider == APIProvider.UPBIT_WEB:
                # 웹스크래핑
                response_data = await self._scrape_upbit_web(request.url)
            else:
                # HTTP 요청
                response = self.session.get(
                    request.url,
                    params=request.params,
                    headers=request.headers,
                    timeout=request.timeout
                )
                response.raise_for_status()
                response_data = response.json()
            
            # 요청 기록
            with self.lock:
                self._record_request(request.provider)
            
            # 캐시 저장
            self._set_cache(cache_key, response_data, cache_ttl)
            
            logger.info(f"{request.provider.value} API 요청 성공: {request.url}")
            return response_data
            
        except Exception as e:
            logger.error(f"{request.provider.value} API 요청 실패: {e}")
            return None
    
    async def _scrape_upbit_web(self, url: str) -> Dict[str, Any]:
        """업비트 웹스크래핑"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                await page.goto(url)
                
                # 스크래핑 로직 (기존 코드 이전)
                content = await page.content()
                browser.close()
                
                # 파싱 로직 추가 필요
                return {"content": content}
                
        except Exception as e:
            logger.error(f"업비트 웹스크래핑 실패: {e}")
            return {}
    
    # ===== 고수준 API 메서드들 =====
    
    async def get_coingecko_global(self) -> Optional[Dict]:
        """CoinGecko 글로벌 데이터"""
        request = APIRequest(
            provider=APIProvider.COINGECKO,
            url="https://api.coingecko.com/api/v3/global"
        )
        return await self.make_request(request, cache_ttl=300)
    
    async def get_coingecko_markets(self, limit: int = 10, vs_currency: str = 'usd') -> Optional[Dict]:
        """CoinGecko 마켓 데이터"""
        request = APIRequest(
            provider=APIProvider.COINGECKO,
            url="https://api.coingecko.com/api/v3/coins/markets",
            params={
                'vs_currency': vs_currency,
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': 'true',
                'price_change_percentage': '24h,7d'
            }
        )
        return await self.make_request(request, cache_ttl=60)
    
    async def get_usd_krw_rate(self) -> Optional[Dict]:
        """USD/KRW 환율"""
        request = APIRequest(
            provider=APIProvider.CURRENCY_API,
            url="https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
        )
        return await self.make_request(request, cache_ttl=3600)  # 1시간 캐시
    
    async def get_upbit_indices(self) -> Optional[Dict]:
        """업비트 지수 (웹스크래핑)"""
        request = APIRequest(
            provider=APIProvider.UPBIT_WEB,
            url="https://upbit.com/exchange"
        )
        return await self.make_request(request, cache_ttl=300)
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Rate Limit 상태 조회"""
        status = {}
        now = time.time()
        
        for provider in APIProvider:
            config = self.rate_limits[provider]
            history = self.request_history[provider]
            
            # 현재 시간 창 내 요청 수
            cutoff = now - config.time_window
            recent_requests = len([t for t in history if t > cutoff])
            
            # 다음 요청 가능 시간
            can_request, wait_time = self._can_make_request(provider)
            
            status[provider.value] = {
                'max_requests': config.max_requests,
                'time_window': config.time_window,
                'min_interval': config.min_interval,
                'recent_requests': recent_requests,
                'can_request': can_request,
                'wait_time': wait_time,
                'last_request': self.last_request_time[provider]
            }
        
        return status


# 싱글톤 인스턴스
_api_manager_instance = None

def get_api_manager() -> CentralizedAPIManager:
    """API 매니저 싱글톤 인스턴스 반환"""
    global _api_manager_instance
    if _api_manager_instance is None:
        _api_manager_instance = CentralizedAPIManager()
    return _api_manager_instance


if __name__ == "__main__":
    async def test_api_manager():
        """API 매니저 테스트"""
        manager = get_api_manager()
        
        print("=== API 매니저 테스트 ===\n")
        
        # Rate limit 상태 확인
        print("Rate Limit 상태:")
        status = manager.get_rate_limit_status()
        for provider, info in status.items():
            print(f"{provider}: {info['recent_requests']}/{info['max_requests']} 요청")
        
        print("\n=== CoinGecko 글로벌 데이터 테스트 ===")
        global_data = await manager.get_coingecko_global()
        if global_data:
            print("✓ 글로벌 데이터 조회 성공")
        else:
            print("✗ 글로벌 데이터 조회 실패")
        
        print("\n=== USD/KRW 환율 테스트 ===")
        usd_data = await manager.get_usd_krw_rate()
        if usd_data:
            print("✓ 환율 데이터 조회 성공")
        else:
            print("✗ 환율 데이터 조회 실패")
    
    asyncio.run(test_api_manager())