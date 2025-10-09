"""
필터 프로파일 Repository

필터 프로파일 데이터베이스 작업 처리
"""
import json
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import FilterProfileORM
from domain.entities.filter_profile import (
    FilterProfile,
    FilterProfileCreate,
    FilterProfileUpdate,
    FilterCondition
)
from utils.logger import get_logger

logger = get_logger(__name__)


class FilterProfileRepository(BaseRepository):
    """필터 프로파일 Repository"""
    
    def __init__(self, db: Session):
        super().__init__(FilterProfileORM, db)
    
    def _to_entity(self, orm: FilterProfileORM) -> FilterProfile:
        """ORM 모델을 도메인 엔티티로 변환"""
        conditions_dict = json.loads(orm.conditions_json)
        conditions = FilterCondition(**conditions_dict)
        
        return FilterProfile(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            market=orm.market,
            conditions=conditions,
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )
    
    def _to_orm_dict(self, entity: FilterProfileCreate | FilterProfileUpdate) -> dict:
        """도메인 엔티티를 ORM dict로 변환"""
        data = entity.model_dump(exclude_unset=True)
        
        # FilterCondition을 JSON 문자열로 변환
        if 'conditions' in data:
            # data['conditions']는 이미 dict로 변환됨 (model_dump에 의해)
            data['conditions_json'] = json.dumps(data['conditions'])
            del data['conditions']
        
        return data
    
    def create(self, entity: FilterProfileCreate) -> FilterProfile:
        """필터 프로파일 생성"""
        orm_data = self._to_orm_dict(entity)
        orm = super().create(**orm_data)
        return self._to_entity(orm)
    
    def get_by_id(self, id: int) -> Optional[FilterProfile]:
        """ID로 프로파일 조회"""
        orm = super().get_by_id(id)
        return self._to_entity(orm) if orm else None
    
    def get_all(self) -> List[FilterProfile]:
        """전체 프로파일 조회"""
        orms = super().get_all()
        return [self._to_entity(orm) for orm in orms]
    
    def get_by_name(self, name: str) -> Optional[FilterProfile]:
        """이름으로 프로파일 조회"""
        stmt = select(self.model).where(self.model.name == name)
        orm = self.db.execute(stmt).scalar_one_or_none()
        return self._to_entity(orm) if orm else None
    
    def get_active_profiles(self, market: Optional[str] = None) -> List[FilterProfile]:
        """활성화된 프로파일 목록 조회"""
        stmt = select(self.model).where(self.model.is_active.is_(True))
        
        if market:
            stmt = stmt.where(self.model.market == market)
        
        stmt = stmt.order_by(self.model.name)
        orms = self.db.execute(stmt).scalars().all()
        
        return [self._to_entity(orm) for orm in orms]
    
    def get_by_market(self, market: str) -> List[FilterProfile]:
        """특정 시장의 프로파일 목록 조회"""
        stmt = select(self.model).where(
            self.model.market == market
        ).order_by(self.model.name)
        
        orms = self.db.execute(stmt).scalars().all()
        return [self._to_entity(orm) for orm in orms]
    
    def deactivate(self, profile_id: int) -> bool:
        """프로파일 비활성화"""
        try:
            stmt = select(self.model).where(self.model.id == profile_id)
            orm = self.db.execute(stmt).scalar_one_or_none()
            
            if not orm:
                return False
            
            orm.is_active = False
            self.db.commit()
            
            logger.info(f"필터 프로파일 비활성화: {orm.name} (ID: {profile_id})")
            return True
            
        except Exception as e:
            logger.error(f"필터 프로파일 비활성화 실패: {e}")
            self.db.rollback()
            return False
    
    def activate(self, profile_id: int) -> bool:
        """프로파일 활성화"""
        try:
            stmt = select(self.model).where(self.model.id == profile_id)
            orm = self.db.execute(stmt).scalar_one_or_none()
            
            if not orm:
                return False
            
            orm.is_active = True
            self.db.commit()
            
            logger.info(f"필터 프로파일 활성화: {orm.name} (ID: {profile_id})")
            return True
            
        except Exception as e:
            logger.error(f"필터 프로파일 활성화 실패: {e}")
            self.db.rollback()
            return False
    
    def delete(self, profile_id: int) -> bool:
        """필터 프로파일 삭제 (ORM 객체 직접 처리)"""
        try:
            stmt = select(self.model).where(self.model.id == profile_id)
            orm = self.db.execute(stmt).scalar_one_or_none()
            
            if not orm:
                logger.warning(f"삭제할 필터 프로파일을 찾을 수 없음: ID={profile_id}")
                return False
            
            profile_name = orm.name
            self.db.delete(orm)
            self.db.commit()
            
            logger.info(f"필터 프로파일 삭제 완료: {profile_name} (ID: {profile_id})")
            return True
            
        except Exception as e:
            logger.error(f"필터 프로파일 삭제 실패 (ID={profile_id}): {e}")
            self.db.rollback()
            return False
