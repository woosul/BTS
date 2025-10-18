"""
BTS 마켓 인덱스 설정

백그라운드 업데이트 주기 및 WebSocket 설정

설정 구조:
1. API_MIN_INTERVAL_*: API 제공자 문서 기준 (참고용, 변경 금지)
2. SAFE_*: 실제 사용 주기 (API_MIN * 1.2 안전 여유, 필요시 조정 가능)
"""
import os
from typing import Dict


class MarketIndexConfig:
    """마켓 인덱스 설정"""

    # ========== API 최소 간격 (API 제공자 문서 기준) ==========
    # 초(s) 단위 - API 문서 기준값, 조정 필요시 이 값만 변경
    API_MIN_INTERVAL_UPBIT_SCRAPING = 5.0       # 업비트 웹스크래핑: 5초
    API_MIN_INTERVAL_UPBIT_API = 0.1            # 업비트 REST API: 100ms (10회/초)
    API_MIN_INTERVAL_BINANCE = 0.05             # Binance: 1200 requests/minute = 0.05초/회 (Weight 기반)
    API_MIN_INTERVAL_COINGECKO = 2.0            # CoinGecko: 30회/분 = 2초/회 (Demo Plan, 순차 호출: Global / Markets)
    API_MIN_INTERVAL_FXRATES = 3600.0           # FxRates: 1시간
    API_MIN_INTERVAL_CURRENCY_API = 86400.0     # Currency API: 1일

    # ========== 안전 여유 계수 ==========
    SAFETY_MARGIN_UPBIT = 1.2       # 업비트: +20%
    SAFETY_MARGIN_BINANCE = 1.0     # Binance: 여유 불필요 (Rate Limit 충분)
                                    # 주의: GlobalUpdater 스레드에서 CoinGecko와 번갈아 호출되므로
                                    # 실제 Binance 호출 주기는 CoinGecko 간격(3초)에 의해 자동 조절됨
    SAFETY_MARGIN_COINGECKO = 1.5   # CoinGecko: +50% (Demo Plan, 1분당 20회 = 30회 제한의 67%)
    SAFETY_MARGIN_DEFAULT = 1.0     # 환율 API: 여유 불필요 (무료 플랜 제한 없음)

    # ========== 실제 사용 주기 (자동 계산) ==========
    # 초(s) 단위 - API_MIN * SAFETY_MARGIN으로 자동 계산
    SAFE_UPBIT_SCRAPING = API_MIN_INTERVAL_UPBIT_SCRAPING * SAFETY_MARGIN_UPBIT        # 5초 * 1.2 = 6초
    SAFE_UPBIT_API = API_MIN_INTERVAL_UPBIT_API * SAFETY_MARGIN_UPBIT                  # 0.1초 * 1.2 = 0.12초
    SAFE_BINANCE = API_MIN_INTERVAL_BINANCE * SAFETY_MARGIN_BINANCE                    # 0.05초 * 1.0 = 0.05초
                                                                                        # (실제 호출 주기는 CoinGecko 간격에 의해 ~3초)
    SAFE_COINGECKO = API_MIN_INTERVAL_COINGECKO * SAFETY_MARGIN_COINGECKO              # 2초 * 1.5 = 3초 (순차 호출 간격, 총 루프 6초)
    SAFE_FXRATES = API_MIN_INTERVAL_FXRATES * SAFETY_MARGIN_DEFAULT                    # 3600초 * 1.0 = 3600초
    SAFE_CURRENCY_API = API_MIN_INTERVAL_CURRENCY_API * SAFETY_MARGIN_DEFAULT          # 86400초 * 1.0 = 86400초

    # ========== 백그라운드 모드 설정 ==========
    BACKGROUND_UPDATE_INTERVAL = 60.0  # 백그라운드 기본 수집 주기: 1분

    # ========== API 호출 ON/OFF 스위치 ==========
    ENABLE_BINANCE_API = True    # Binance API 호출 활성화 (Primary, 실시간 가격)
    ENABLE_COINGECKO_API = True  # CoinGecko API 호출 활성화 (Fallback + Global 데이터)
    # False: API 호출 중단, DB에 저장된 기존 데이터 사용 (Dashboard 정상 동작)
    # True: API 호출 재개 (Demo Plan으로 안정적 30회/분 보장)

    # ========== Binance 주요 코인 설정 ==========
    # 시가총액 기준 상위 코인 (USDT 제외, SOL 포함)
    BINANCE_TOP_COINS = [
        'BTC',   # Bitcoin (시총 1위)
        'ETH',   # Ethereum (시총 2위)
        'SOL',   # Solana (시총 5위)
        'BNB',   # BNB (시총 4위)
        'XRP',   # XRP (시총 6위)
        'USDC',  # USD Coin (스테이블코인)
        'ADA',   # Cardano
        'DOGE',  # Dogecoin
        'TRX',   # TRON
        'AVAX'   # Avalanche
    ]
    
    BINANCE_TOP_COINS_LIMIT = 10  # 기본 조회 개수

    # ========== CoinGecko API Key (Demo Plan) ==========
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', 'CG-fBNTwyjA4srLMRp7VCdDQmeh')

    # ========== WebSocket 설정 ==========
    WEBSOCKET_UPDATE_INTERVAL = 5.0  # 5초 (화면 업데이트 주기, 실시간성 우선)

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

    # ========== API Timeout 설정 (초 단위) ==========
    # HTTP 요청 시 서버 응답 대기 최대 시간
    TIMEOUT_UPBIT_API = 8                   # 업비트 API 응답 대기
    TIMEOUT_BINANCE_API = 8                # Binance API 응답 대기 (빠른 응답 보장)
    TIMEOUT_COINGECKO_API = 10              # CoinGecko API 응답 대기 (Markets API는 더 무거워서 증가)
    
    # Playwright 웹스크래핑 대기 시간
    TIMEOUT_UPBIT_WAIT_LOAD = 8             # 업비트 페이지 로드 대기
    TIMEOUT_UPBIT_WAIT_SELECTOR = 8         # 업비트 셀렉터 출현 대기

    # WebSocket 설정
    WEBSOCKET_HOST = "localhost"
    WEBSOCKET_PORT = 8765

    # ========== 캐시 TTL 설정 (초 단위) ==========
    # 캐시된 데이터 유효 시간 (만료 시 재수집)
    TTL_UPBIT = 300      # 업비트 지수: 5분
    TTL_GLOBAL = 300     # 글로벌 지수: 5분
    TTL_USD = 300        # USD/KRW 환율: 5분
    TTL_COIN = 60        # 개별 코인: 1분

    @classmethod
    def get_collection_interval(cls, source: str, is_dashboard_active: bool) -> float:
        """
        데이터 소스별 실제 수집 주기 반환
        
        Args:
            source: 'upbit', 'binance', 'coingecko', 'fxrates', 'currency_api'
            is_dashboard_active: Dashboard 활성 여부 (WebSocket ON)
        
        Returns:
            실제 사용할 수집 주기 (초)
        """
        if is_dashboard_active:
            # Dashboard 활성: 빠른 수집 (SAFE_* 사용)
            intervals = {
                'upbit': cls.SAFE_UPBIT_SCRAPING,      # 6초
                'binance': cls.SAFE_BINANCE,           # 0.05초 (실시간!)
                'coingecko': cls.SAFE_COINGECKO,       # 3초 (순차 호출 간격)
                'fxrates': cls.SAFE_FXRATES,           # 1시간
                'currency_api': cls.SAFE_CURRENCY_API  # 1일
            }
        else:
            # 백그라운드: UserSettings에서 사용자 설정값 조회
            user_interval = cls.get_update_interval_seconds()  # UserSettings에서 가져오기 (예: 300초)
            intervals = {
                'upbit': user_interval,                # 사용자 설정값 (예: 300초)
                'binance': user_interval,              # 사용자 설정값 (백그라운드는 느리게)
                'coingecko': user_interval,            # 사용자 설정값
                'fxrates': cls.SAFE_FXRATES,           # 1시간
                'currency_api': cls.SAFE_CURRENCY_API  # 1일
            }
        
        return intervals.get(source, user_interval if not is_dashboard_active else cls.SAFE_UPBIT_SCRAPING)

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
        return int(cls.BACKGROUND_UPDATE_INTERVAL)

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
    def get_websocket_url(cls) -> str:
        """WebSocket URL"""
        return f"ws://{cls.WEBSOCKET_HOST}:{cls.WEBSOCKET_PORT}"

    @classmethod
    def to_dict(cls) -> Dict:
        """설정을 딕셔너리로 변환"""
        return {
            'background_update_interval': cls.get_update_interval_seconds(),
            'websocket_host': cls.WEBSOCKET_HOST,
            'websocket_port': cls.WEBSOCKET_PORT,
            'websocket_url': cls.get_websocket_url(),
            'api_min_intervals': {
                'upbit_scraping_ms': cls.API_MIN_INTERVAL_UPBIT_SCRAPING,
                'upbit_api_ms': cls.API_MIN_INTERVAL_UPBIT_API,
                'coingecko_ms': cls.API_MIN_INTERVAL_COINGECKO,
                'fxrates_ms': cls.API_MIN_INTERVAL_FXRATES,
                'currency_api_ms': cls.API_MIN_INTERVAL_CURRENCY_API
            },
            'safe_intervals': {
                'upbit_scraping_s': cls.SAFE_UPBIT_SCRAPING,
                'upbit_api_s': cls.SAFE_UPBIT_API,
                'coingecko_s': cls.SAFE_COINGECKO,
                'fxrates_s': cls.SAFE_FXRATES,
                'currency_api_s': cls.SAFE_CURRENCY_API
            },
            'api_timeouts': {
                'upbit_api': cls.TIMEOUT_UPBIT_API,
                'upbit_wait_selector': cls.TIMEOUT_UPBIT_WAIT_SELECTOR,
                'upbit_wait_load': cls.TIMEOUT_UPBIT_WAIT_LOAD,
                'coingecko_api': cls.TIMEOUT_COINGECKO_API
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

    print(f"백그라운드 업데이트 주기: {config.get_update_interval_seconds()}초")
    print(f"WebSocket URL: {config.get_websocket_url()}")
    print("전체 설정:")

    import json
    print(json.dumps(config.to_dict(), indent=2))

    print("\n설정 변경 예시:")
    config.set_update_interval(10)
    print(f"변경 후 주기: {config.get_update_interval_seconds()}초")
