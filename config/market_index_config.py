"""
BTS 마켓 인덱스 설정

백그라운드 업데이트 주기 및 WebSocket 설정
"""
from typing import Dict


class MarketIndexConfig:
    """마켓 인덱스 설정"""

    # 업데이트 주기 (초) - 기본값, 실제 값은 UserSettings에서 관리
    DEFAULT_UPDATE_INTERVAL_SECONDS = 300  # 5분 (기본값)

    # ===== 데이터 소스별 업데이트 주기 설정 (초 단위) =====
    # 대시보드 활성 시 (빠른 모드)
    UPDATE_INTERVAL_UPBIT_SCRAPING = 5  # 업비트 웹스크래핑 + USD/KRW: 5초 (실시간성 우선)
    UPDATE_INTERVAL_UPBIT_API = 5  # 업비트 API: 5초 (빠른 응답)
    UPDATE_INTERVAL_COINGECKO = 6  # CoinGecko API: 6초 (429 에러 방지, 무료 플랜 제한)
    UPDATE_INTERVAL_FXRATES = 3600  # FxRates API: 1시간 (무료 플랜 1000 requests/month, fallback)
    UPDATE_INTERVAL_CURRENCY_API = 86400  # Currency API: 1일 (fallback, 일일 업데이트)

    # 백그라운드 모드 (다른 페이지 활성 시)
    DEFAULT_BACKGROUND_UPDATE_INTERVAL = 300  # 5분 (기본값)

    # ===== WebSocket 전송 주기 =====
    WEBSOCKET_UPDATE_INTERVAL = 5  # 5초 (화면 업데이트 주기, 실시간성 우선)

    # ===== 페이지별 WebSocket 전송 전략 =====
    # 각 페이지별로 WebSocket 전송 여부 및 주기 설정
    # 'enabled': True/False - WebSocket 전송 활성화 여부
    # 'interval': 초 단위 전송 주기 (enabled=True일 때만 적용)
    WEBSOCKET_PAGE_STRATEGIES = {
        'dashboard': {
            'enabled': True,
            'interval': 5,  # 5초 (실시간 업데이트)
            'description': 'Dashboard 실시간 모니터링'
        },
        'screening': {
            'enabled': False,  # 필요시 True로 변경
            'interval': 60,
            'description': '종목 스크리닝 (필요시 활성화)'
        },
        'filtering': {
            'enabled': False,  # 필요시 True로 변경
            'interval': 60,
            'description': '종목 필터링 (필요시 활성화)'
        },
        'portfolio': {
            'enabled': False,
            'interval': 30,
            'description': '포트폴리오 모니터링 (필요시 활성화)'
        },
        'setting': {
            'enabled': False,
            'interval': 0,
            'description': '설정 페이지 (전송 불필요)'
        },
        'unknown': {
            'enabled': False,
            'interval': 0,
            'description': '알 수 없는 페이지 (기본값)'
        }
    }

    # API Rate Limit 설정 (밀리초 단위, API 문서상 최소값)
    API_MIN_INTERVAL_UPBIT_SCRAPING = 5000  # 업비트 웹스크래핑: 5초 (측정 기준)
    API_MIN_INTERVAL_UPBIT_API = 100  # 업비트 API: 100ms (10회/초)
    API_MIN_INTERVAL_COINGECKO = 4000  # CoinGecko API: 4초 (보수적 설정 - 429 오류 방지)
    API_MIN_INTERVAL_FXRATES = 3600000  # FxRates API: 1시간 (무료 플랜)
    API_MIN_INTERVAL_CURRENCY_API = 86400000  # Currency API: 1일 (fallback용)

    # 내부 Rate Limit (API 최소 간격 * 125% 안전 여유)
    INTERNAL_MIN_INTERVAL_UPBIT_SCRAPING = int(API_MIN_INTERVAL_UPBIT_SCRAPING * 1.2)  # 6초
    INTERNAL_MIN_INTERVAL_UPBIT_API = int(API_MIN_INTERVAL_UPBIT_API * 1.2)  # 120ms
    INTERNAL_MIN_INTERVAL_COINGECKO = int(API_MIN_INTERVAL_COINGECKO * 1.25)  # 5초 (보수적)
    INTERNAL_MIN_INTERVAL_CURRENCY_API = int(API_MIN_INTERVAL_CURRENCY_API * 1.2)  # 28.8시간

    # API Timeout 설정 (초 단위), 화면 업데이트 기본값 : 10초 대응
    TIMEOUT_UPBIT_API = 8  # 업비트 API: 8초
    TIMEOUT_UPBIT_SCRAPING = 8  # 업비트 웹스크래핑: 8초
    TIMEOUT_UPBIT_WAIT_SELECTOR = 8  # 업비트 셀렉터 대기: 8초  
    TIMEOUT_UPBIT_WAIT_LOAD = 8  # 업비트 페이지 로드 대기: 8초
    TIMEOUT_COINGECKO_API = 8  # CoinGecko API: 8초
    TIMEOUT_COINGECKO_MARKETS = 8  # CoinGecko Markets API: 8초
    TIMEOUT_CURRENCY_API = 8  # 환율 API: 8초
    
    # 화면 업데이트 최소값 (밀리초)
    SCREEN_UPDATE_MIN_INTERVAL = 10000  # 10초 (권장 최소값)
    
    # 시스템 전체 업데이트 최소 간격 (가장 제한적인 스크래핑 기준, 초 단위)
    SYSTEM_MIN_UPDATE_INTERVAL = max(
        INTERNAL_MIN_INTERVAL_UPBIT_SCRAPING // 1000,  # 6초
        SCREEN_UPDATE_MIN_INTERVAL // 1000,  # 10초
        5  # 절대 최소값 5초
    )

    # WebSocket 설정
    WEBSOCKET_HOST = "localhost"
    WEBSOCKET_PORT = 8765

    # TTL 설정 (초)
    TTL_UPBIT = 300  # 업비트 지수: 5분
    TTL_GLOBAL = 300  # 글로벌 지수: 5분
    TTL_USD = 300  # USD/KRW 환율: 5분
    TTL_COIN = 60  # 개별 코인: 1분

    @classmethod
    def get_update_interval_seconds(cls) -> int:
        """업데이트 주기 (초 단위) - UserSettings에서 조회"""
        try:
            from infrastructure.repositories.user_settings_repository import UserSettingsRepository
            from domain.entities.user_settings import UserSettings

            repo = UserSettingsRepository()
            setting = repo.get_by_key(UserSettings.GENERAL_UPDATE_INTERVAL)
            if setting:
                return int(setting.setting_value)
        except Exception:
            pass
        return cls.DEFAULT_UPDATE_INTERVAL_SECONDS

    @classmethod
    def get_update_interval_minutes(cls) -> int:
        """업데이트 주기 (분 단위)"""
        return cls.get_update_interval_seconds() // 60

    @classmethod
    def set_update_interval(cls, seconds: int):
        """업데이트 주기 설정 (초 단위) - UserSettings에 저장"""
        try:
            from infrastructure.repositories.user_settings_repository import UserSettingsRepository
            from domain.entities.user_settings import UserSettings

            repo = UserSettingsRepository()
            repo.upsert(
                key=UserSettings.GENERAL_UPDATE_INTERVAL,
                value=str(seconds),
                description="백그라운드 일반 업데이트 간격 (초)"
            )
        except Exception as e:
            print(f"업데이트 주기 설정 실패: {e}")

    @classmethod
    def validate_update_interval(cls, seconds: int) -> int:
        """
        사용자 설정 업데이트 간격 유효성 검증
        
        Args:
            seconds: 사용자가 설정하려는 간격 (초)
            
        Returns:
            int: 유효성 검증된 간격 (시스템 최소값 이상으로 조정)
        """
        if seconds <= 0:
            return cls.SYSTEM_MIN_UPDATE_INTERVAL
        
        # 시스템 최소값보다 작으면 최소값으로 조정
        return max(seconds, cls.SYSTEM_MIN_UPDATE_INTERVAL)
    
    @classmethod
    def get_available_background_intervals(cls) -> list:
        """
        백그라운드 업데이트 간격 옵션 (초 단위)
        다른 페이지에 있을 때 사용

        Returns:
            list: [10, 30, 60, 300, 600, 1200, 1800]
        """
        return [10, 30, 60, 300, 600, 1200, 1800]  # 10초, 30초, 1분, 5분, 10분, 20분, 30분

    @classmethod
    def get_background_interval_label(cls, seconds: int) -> str:
        """
        백그라운드 간격 초를 라벨로 변환

        Args:
            seconds: 초 단위 간격

        Returns:
            str: "10초", "30초", "1분", "5분", "10분", "20분", "30분"
        """
        if seconds < 60:
            return f"{seconds}초"
        else:
            return f"{seconds // 60}분"

    @classmethod
    def get_available_update_intervals(cls) -> list:
        """
        사용자에게 제공할 업데이트 간격 옵션들 (초 단위)

        Returns:
            list: 선택 가능한 간격들
        """
        base_intervals = [
            0,  # OFF (업데이트 비활성화)
            10,  # 10초 (화면 업데이트 최소값)
            30,  # 30초
            60,  # 1분
            180,  # 3분
            300,  # 5분 (기본값)
            600,  # 10분
            900,  # 15분
            1800,  # 30분
            3600   # 1시간
        ]

        # 시스템 최소값 이상만 반환 (OFF 제외)
        return [0] + [interval for interval in base_intervals[1:]
                     if interval >= cls.SYSTEM_MIN_UPDATE_INTERVAL]

    @classmethod
    def get_websocket_url(cls) -> str:
        """WebSocket URL"""
        return f"ws://{cls.WEBSOCKET_HOST}:{cls.WEBSOCKET_PORT}"

    @classmethod
    def to_dict(cls) -> Dict:
        """설정을 딕셔너리로 변환"""
        return {
            'update_interval_seconds': cls.get_update_interval_seconds(),
            'update_interval_minutes': cls.get_update_interval_minutes(),
            'system_min_update_interval': cls.SYSTEM_MIN_UPDATE_INTERVAL,
            'websocket_host': cls.WEBSOCKET_HOST,
            'websocket_port': cls.WEBSOCKET_PORT,
            'websocket_url': cls.get_websocket_url(),
            'api_rate_limits': {
                'upbit_scraping_ms': cls.API_MIN_INTERVAL_UPBIT_SCRAPING,
                'upbit_api_ms': cls.API_MIN_INTERVAL_UPBIT_API,
                'coingecko_ms': cls.API_MIN_INTERVAL_COINGECKO,
                'currency_api_ms': cls.API_MIN_INTERVAL_CURRENCY_API
            },
            'internal_rate_limits': {
                'upbit_scraping_ms': cls.INTERNAL_MIN_INTERVAL_UPBIT_SCRAPING,
                'upbit_api_ms': cls.INTERNAL_MIN_INTERVAL_UPBIT_API,
                'coingecko_ms': cls.INTERNAL_MIN_INTERVAL_COINGECKO,
                'currency_api_ms': cls.INTERNAL_MIN_INTERVAL_CURRENCY_API
            },
            'api_timeouts': {
                'upbit_api': cls.TIMEOUT_UPBIT_API,
                'upbit_scraping': cls.TIMEOUT_UPBIT_SCRAPING,
                'upbit_wait_selector': cls.TIMEOUT_UPBIT_WAIT_SELECTOR,
                'upbit_wait_load': cls.TIMEOUT_UPBIT_WAIT_LOAD,
                'coingecko_api': cls.TIMEOUT_COINGECKO_API,
                'coingecko_markets': cls.TIMEOUT_COINGECKO_MARKETS,
                'currency_api': cls.TIMEOUT_CURRENCY_API
            },
            'ttl': {
                'upbit': cls.TTL_UPBIT,
                'global': cls.TTL_GLOBAL,
                'usd': cls.TTL_USD,
                'coin': cls.TTL_COIN
            }
        }


if __name__ == "__main__":
    print("=== 마켓 인덱스 설정 ===\n")

    config = MarketIndexConfig()

    print(f"업데이트 주기: {config.get_update_interval_minutes()}분")
    print(f"WebSocket URL: {config.get_websocket_url()}")
    print("전체 설정:")

    import json
    print(json.dumps(config.to_dict(), indent=2))

    print("\n설정 변경 예시:")
    config.set_update_interval(10)
    print(f"변경 후 주기: {config.get_update_interval_minutes()}분 ({config.get_update_interval_seconds()}초)")
