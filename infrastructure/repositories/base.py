"""
BTS Repository 베이스 클래스

제네릭 Repository 패턴 구현
CRUD 작업 추상화
"""
from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from infrastructure.database.connection import Base
from core.exceptions import RecordNotFoundError, DatabaseError
from utils.logger import get_logger

logger = get_logger(__name__)

# 타입 변수
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    제네릭 Repository 베이스 클래스

    모든 Repository의 공통 CRUD 작업 제공
    """

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Repository 초기화

        Args:
            model: SQLAlchemy ORM 모델 클래스
            db: 데이터베이스 세션
        """
        self.model = model
        self.db = db

    # ===== CREATE =====
    def create(self, **kwargs) -> ModelType:
        """
        새 레코드 생성

        Args:
            **kwargs: 모델 필드 값

        Returns:
            ModelType: 생성된 모델 인스턴스

        Raises:
            DatabaseError: 생성 실패 시
        """
        try:
            # 시간 필드를 명시적으로 로컬 시간으로 설정
            from datetime import datetime
            now = datetime.now()
            if 'created_at' not in kwargs:
                kwargs['created_at'] = now
            if 'updated_at' not in kwargs:
                kwargs['updated_at'] = now
            
            instance = self.model(**kwargs)
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            logger.info(f"{self.model.__name__} 생성 완료: id={instance.id}")
            return instance
        except Exception as e:
            self.db.rollback()
            logger.error(f"{self.model.__name__} 생성 실패: {e}")
            raise DatabaseError("레코드 생성 실패", {"error": str(e)}) from e

    def bulk_create(self, items: List[dict]) -> List[ModelType]:
        """
        다수 레코드 일괄 생성

        Args:
            items: 생성할 레코드 목록

        Returns:
            List[ModelType]: 생성된 모델 인스턴스 목록
        """
        try:
            # 시간 필드를 명시적으로 로컬 시간으로 설정
            from datetime import datetime
            now = datetime.now()
            
            for item in items:
                if 'created_at' not in item:
                    item['created_at'] = now
                if 'updated_at' not in item:
                    item['updated_at'] = now
            
            instances = [self.model(**item) for item in items]
            self.db.add_all(instances)
            self.db.commit()
            for instance in instances:
                self.db.refresh(instance)
            logger.info(f"{self.model.__name__} {len(instances)}개 일괄 생성 완료")
            return instances
        except Exception as e:
            self.db.rollback()
            logger.error(f"{self.model.__name__} 일괄 생성 실패: {e}")
            raise DatabaseError("일괄 생성 실패", {"error": str(e)}) from e

    # ===== READ =====
    def get_by_id(self, record_id: int) -> Optional[ModelType]:
        """
        ID로 레코드 조회

        Args:
            id: 레코드 ID

        Returns:
            Optional[ModelType]: 모델 인스턴스 또는 None
        """
        try:
            stmt = select(self.model).where(self.model.id == record_id)
            result = self.db.execute(stmt).scalar_one_or_none()
            return result
        except Exception as e:
            logger.error(f"{self.model.__name__} 조회 실패 (id={id}): {e}")
            raise DatabaseError("레코드 조회 실패", {"id": record_id, "error": str(e)}) from e

    def get_by_id_or_raise(self, record_id: int) -> ModelType:
        """
        ID로 레코드 조회 (없으면 예외 발생)

        Args:
            record_id: 레코드 ID

        Returns:
            ModelType: 모델 인스턴스

        Raises:
            RecordNotFoundError: 레코드를 찾을 수 없는 경우
        """
        instance = self.get_by_id(record_id)
        if instance is None:
            raise RecordNotFoundError(
                f"{self.model.__name__}을(를) 찾을 수 없습니다",
                {"id": id}
            )
        return instance

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[Any] = None
    ) -> List[ModelType]:
        """
        모든 레코드 조회 (페이징)

        Args:
            skip: 건너뛸 레코드 수
            limit: 최대 조회 수
            order_by: 정렬 기준

        Returns:
            List[ModelType]: 모델 인스턴스 목록
        """
        try:
            stmt = select(self.model)

            if order_by is not None:
                stmt = stmt.order_by(order_by)

            stmt = stmt.offset(skip).limit(limit)
            result = self.db.execute(stmt).scalars().all()
            return list(result)
        except Exception as e:
            logger.error(f"{self.model.__name__} 목록 조회 실패: {e}")
            raise DatabaseError("목록 조회 실패", {"error": str(e)}) from e

    def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """
        특정 필드로 레코드 조회

        Args:
            field_name: 필드 이름
            value: 필드 값

        Returns:
            Optional[ModelType]: 모델 인스턴스 또는 None
        """
        try:
            field = getattr(self.model, field_name)
            stmt = select(self.model).where(field == value)
            result = self.db.execute(stmt).scalar_one_or_none()
            return result
        except Exception as e:
            logger.error(f"{self.model.__name__} 조회 실패 ({field_name}={value}): {e}")
            raise DatabaseError(
                "레코드 조회 실패",
                {"field": field_name, "value": value, "error": str(e)}
            ) from e

    def filter_by(self, **filters) -> List[ModelType]:
        """
        필터 조건으로 레코드 조회

        Args:
            **filters: 필터 조건

        Returns:
            List[ModelType]: 모델 인스턴스 목록
        """
        try:
            stmt = select(self.model)
            for key, value in filters.items():
                field = getattr(self.model, key)
                stmt = stmt.where(field == value)
            result = self.db.execute(stmt).scalars().all()
            return list(result)
        except Exception as e:
            logger.error(f"{self.model.__name__} 필터 조회 실패: {e}")
            raise DatabaseError("필터 조회 실패", {"filters": filters, "error": str(e)}) from e

    def count(self, **filters) -> int:
        """
        레코드 개수 카운트

        Args:
            **filters: 필터 조건

        Returns:
            int: 레코드 개수
        """
        try:
            stmt = select(self.model)
            for key, value in filters.items():
                field = getattr(self.model, key)
                stmt = stmt.where(field == value)
            result = self.db.execute(stmt).scalars().all()
            return len(result)
        except Exception as e:
            logger.error(f"{self.model.__name__} 카운트 실패: {e}")
            raise DatabaseError("카운트 실패", {"error": str(e)}) from e

    def exists(self, record_id: int) -> bool:
        """
        레코드 존재 여부 확인

        Args:
            record_id: 레코드 ID

        Returns:
            bool: 존재 여부
        """
        return self.get_by_id(record_id) is not None

    # ===== UPDATE =====
    def update(self, record_id: int, **kwargs) -> ModelType:
        """
        레코드 업데이트

        Args:
            record_id: 레코드 ID
            **kwargs: 업데이트할 필드 값

        Returns:
            ModelType: 업데이트된 모델 인스턴스

        Raises:
            RecordNotFoundError: 레코드를 찾을 수 없는 경우
        """
        try:
            instance = self.get_by_id_or_raise(record_id)
            
            # updated_at을 명시적으로 로컬 시간으로 설정
            from datetime import datetime
            if 'updated_at' not in kwargs:
                kwargs['updated_at'] = datetime.now()

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            self.db.commit()
            self.db.refresh(instance)
            logger.info(f"{self.model.__name__} 업데이트 완료: id={id}")
            return instance
        except RecordNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"{self.model.__name__} 업데이트 실패 (id={id}): {e}")
            raise DatabaseError("업데이트 실패", {"id": record_id, "error": str(e)}) from e

    def bulk_update(self, updates: List[dict]) -> int:
        """
        다수 레코드 일괄 업데이트

        Args:
            updates: 업데이트할 레코드 목록 (id 포함)

        Returns:
            int: 업데이트된 레코드 수
        """
        try:
            count = 0
            for item in updates:
                record_id = item.pop("id")
                stmt = (
                    update(self.model)
                    .where(self.model.id == record_id)
                    .values(**item)
                )
                result = self.db.execute(stmt)
                count += result.rowcount

            self.db.commit()
            logger.info(f"{self.model.__name__} {count}개 일괄 업데이트 완료")
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"{self.model.__name__} 일괄 업데이트 실패: {e}")
            raise DatabaseError("일괄 업데이트 실패", {"error": str(e)}) from e

    # ===== DELETE =====
    def delete(self, record_id: int) -> bool:
        """
        레코드 삭제

        Args:
            record_id: 레코드 ID

        Returns:
            bool: 삭제 성공 여부

        Raises:
            RecordNotFoundError: 레코드를 찾을 수 없는 경우
        """
        try:
            instance = self.get_by_id_or_raise(record_id)
            self.db.delete(instance)
            self.db.commit()
            logger.info(f"{self.model.__name__} 삭제 완료: id={record_id}")
            return True
        except RecordNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"{self.model.__name__} 삭제 실패 (id={id}): {e}")
            raise DatabaseError("삭제 실패", {"id": record_id, "error": str(e)}) from e

    def delete_by_field(self, field_name: str, value: Any) -> int:
        """
        특정 필드 조건으로 레코드 삭제

        Args:
            field_name: 필드 이름
            value: 필드 값

        Returns:
            int: 삭제된 레코드 수
        """
        try:
            field = getattr(self.model, field_name)
            stmt = delete(self.model).where(field == value)
            result = self.db.execute(stmt)
            self.db.commit()
            count = result.rowcount
            logger.info(f"{self.model.__name__} {count}개 삭제 완료 ({field_name}={value})")
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"{self.model.__name__} 삭제 실패 ({field_name}={value}): {e}")
            raise DatabaseError(
                "삭제 실패",
                {"field": field_name, "value": value, "error": str(e)}
            ) from e

    # ===== 유틸리티 =====
    def refresh(self, instance: ModelType) -> ModelType:
        """
        인스턴스 새로고침

        Args:
            instance: 모델 인스턴스

        Returns:
            ModelType: 새로고침된 인스턴스
        """
        self.db.refresh(instance)
        return instance

    def commit(self) -> None:
        """트랜잭션 커밋"""
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"커밋 실패: {e}")
            raise DatabaseError("커밋 실패", {"error": str(e)}) from e

    def rollback(self) -> None:
        """트랜잭션 롤백"""
        self.db.rollback()
        logger.warning("트랜잭션 롤백")


if __name__ == "__main__":
    # Repository 베이스 클래스 테스트
    print("=== Repository 베이스 클래스 생성 완료 ===")
    print("✓ BaseRepository 클래스 정의됨")
    print("✓ CRUD 메서드 구현됨")
