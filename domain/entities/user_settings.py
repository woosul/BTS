"""
BTS 사용자 설정 엔티티

사용자 설정을 관리하는 도메인 엔티티
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserSettings:
    """사용자 설정 엔티티"""

    setting_key: str
    setting_value: str
    description: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 설정 키 상수
    DASHBOARD_REFRESH_INTERVAL = "dashboard_refresh_interval"
    GENERAL_UPDATE_INTERVAL = "general_update_interval"

    @classmethod
    def create(cls, key: str, value: str, description: Optional[str] = None) -> "UserSettings":
        """설정 생성"""
        return cls(
            setting_key=key,
            setting_value=value,
            description=description
        )

    @classmethod
    def create_dashboard_refresh_interval(cls, interval_seconds: int) -> "UserSettings":
        """대시보드 리프레시 간격 설정 생성"""
        return cls.create(
            key=cls.DASHBOARD_REFRESH_INTERVAL,
            value=str(interval_seconds),
            description="대시보드 페이지 자동 갱신 간격 (초)"
        )

    @classmethod
    def create_general_update_interval(cls, interval_seconds: int) -> "UserSettings":
        """일반 업데이트 간격 설정 생성"""
        return cls.create(
            key=cls.GENERAL_UPDATE_INTERVAL,
            value=str(interval_seconds),
            description="백그라운드 일반 업데이트 간격 (초)"
        )

    def get_value_as_int(self) -> int:
        """설정값을 정수로 반환"""
        return int(self.setting_value)

    def update_value(self, new_value: str):
        """설정값 업데이트"""
        self.setting_value = new_value
        self.updated_at = datetime.now()


if __name__ == "__main__":
    print("=== 사용자 설정 엔티티 테스트 ===\n")

    # 대시보드 리프레시 간격 설정
    dashboard_setting = UserSettings.create_dashboard_refresh_interval(60)
    print(f"대시보드 리프레시 간격: {dashboard_setting.get_value_as_int()}초")
    print(f"설명: {dashboard_setting.description}")

    # 일반 업데이트 간격 설정
    general_setting = UserSettings.create_general_update_interval(300)
    print(f"\n일반 업데이트 간격: {general_setting.get_value_as_int()}초")
    print(f"설명: {general_setting.description}")

    # 설정값 업데이트
    dashboard_setting.update_value("30")
    print(f"\n업데이트 후: {dashboard_setting.get_value_as_int()}초")
