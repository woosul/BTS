"""
BTS 사용자 설정 저장소

사용자 설정 데이터 접근 계층
"""
from typing import Optional
from datetime import datetime

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import UserSettingsORM
from domain.entities.user_settings import UserSettings


class UserSettingsRepository(BaseRepository[UserSettingsORM]):
    """사용자 설정 저장소"""

    def __init__(self, db: Optional[any] = None):
        if db is None:
            from infrastructure.database.connection import SessionLocal
            db = SessionLocal()
        super().__init__(UserSettingsORM, db)
        self.session = db

    def to_entity(self, orm_model: UserSettingsORM) -> UserSettings:
        """ORM → Entity 변환"""
        return UserSettings(
            id=orm_model.id,
            setting_key=orm_model.setting_key,
            setting_value=orm_model.setting_value,
            description=orm_model.description,
            created_at=orm_model.created_at,
            updated_at=orm_model.updated_at
        )

    def get_by_key(self, key: str) -> Optional[UserSettings]:
        """키로 설정 조회"""
        orm = self.session.query(self.model).filter(
            self.model.setting_key == key
        ).first()

        return self.to_entity(orm) if orm else None

    def upsert(self, key: str, value: str, description: Optional[str] = None) -> UserSettings:
        """설정 생성 또는 업데이트"""
        existing = self.session.query(self.model).filter(
            self.model.setting_key == key
        ).first()

        if existing:
            # 업데이트
            existing.setting_value = value
            if description:
                existing.description = description
            existing.updated_at = datetime.now()
            self.session.commit()
            self.session.refresh(existing)
            return self.to_entity(existing)
        else:
            # 생성
            new_setting = self.model(
                setting_key=key,
                setting_value=value,
                description=description
            )
            self.session.add(new_setting)
            self.session.commit()
            self.session.refresh(new_setting)
            return self.to_entity(new_setting)

    def delete_by_key(self, key: str) -> bool:
        """키로 설정 삭제"""
        setting = self.session.query(self.model).filter(
            self.model.setting_key == key
        ).first()

        if setting:
            self.session.delete(setting)
            self.session.commit()
            return True
        return False


if __name__ == "__main__":
    print("=== 사용자 설정 저장소 테스트 ===\n")

    repo = UserSettingsRepository()

    # 1. 설정 생성
    print("1. 대시보드 리프레시 간격 설정 생성")
    dashboard_setting = repo.upsert(
        key=UserSettings.DASHBOARD_REFRESH_INTERVAL,
        value="60",
        description="대시보드 페이지 자동 갱신 간격 (초)"
    )
    print(f"   생성됨: {dashboard_setting.setting_key} = {dashboard_setting.setting_value}")

    # 2. 설정 조회
    print("\n2. 설정 조회")
    retrieved = repo.get_by_key(UserSettings.DASHBOARD_REFRESH_INTERVAL)
    if retrieved:
        print(f"   조회됨: {retrieved.setting_key} = {retrieved.setting_value}")
        print(f"   설명: {retrieved.description}")

    # 3. 설정 업데이트
    print("\n3. 설정 업데이트")
    updated = repo.upsert(
        key=UserSettings.DASHBOARD_REFRESH_INTERVAL,
        value="30",
        description="대시보드 페이지 자동 갱신 간격 (초)"
    )
    print(f"   업데이트됨: {updated.setting_key} = {updated.setting_value}")

    # 4. 전체 설정 조회
    print("\n4. 전체 설정 조회")
    all_settings = repo.get_all()
    for setting in all_settings:
        entity = repo.to_entity(setting)
        print(f"   - {entity.setting_key}: {entity.setting_value}")

    print("\n✓ 테스트 완료")
