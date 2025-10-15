"""
BTS 마켓 인덱스 설정

백그라운드 업데이트 주기 및 WebSocket 설정
"""
from typing import Dict


class MarketIndexConfig:
    """마켓 인덱스 설정"""

    # 업데이트 주기 (초) - 기본값, 실제 값은 UserSettings에서 관리
    DEFAULT_UPDATE_INTERVAL_SECONDS = 300  # 5분 (기본값)

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
    def get_websocket_url(cls) -> str:
        """WebSocket URL"""
        return f"ws://{cls.WEBSOCKET_HOST}:{cls.WEBSOCKET_PORT}"

    @classmethod
    def to_dict(cls) -> Dict:
        """설정을 딕셔너리로 변환"""
        return {
            'update_interval_seconds': cls.UPDATE_INTERVAL_SECONDS,
            'update_interval_minutes': cls.get_update_interval_minutes(),
            'websocket_host': cls.WEBSOCKET_HOST,
            'websocket_port': cls.WEBSOCKET_PORT,
            'websocket_url': cls.get_websocket_url(),
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
    print(f"\n전체 설정:")

    import json
    print(json.dumps(config.to_dict(), indent=2))

    print("\n설정 변경 예시:")
    config.set_update_interval(10)
    print(f"변경 후 주기: {config.get_update_interval_minutes()}분 ({config.UPDATE_INTERVAL_SECONDS}초)")
