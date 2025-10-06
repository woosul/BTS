"""
BTS 데이터베이스 연결 모듈

SQLAlchemy 엔진 및 세션 관리
SQLite 시작, PostgreSQL 확장 가능
"""
from typing import Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import StaticPool

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ===== SQLAlchemy 베이스 클래스 =====
class Base(DeclarativeBase):
    """모든 ORM 모델의 베이스 클래스"""
    pass


# ===== 엔진 생성 함수 =====
def get_engine() -> Engine:
    """
    데이터베이스 엔진 생성

    SQLite 설정:
    - WAL 모드: 동시성 향상
    - Foreign Key 활성화
    - StaticPool: 단일 연결 재사용 (Streamlit 호환)
    """
    connect_args = {}
    poolclass = None

    if settings.database_url.startswith("sqlite"):
        # SQLite 전용 설정
        connect_args = {
            "check_same_thread": False,  # 멀티스레드 허용
        }
        poolclass = StaticPool  # 단일 연결 재사용
        logger.info("SQLite 데이터베이스 연결 설정")

    else:
        # PostgreSQL 등 다른 DB 설정
        logger.info("PostgreSQL 데이터베이스 연결 설정")

    # 절대 경로로 변환된 DB URL 사용
    db_url = settings.get_absolute_database_url()

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        poolclass=poolclass,
        echo=settings.log_level == "DEBUG",  # 디버그 모드에서 SQL 쿼리 로깅
    )

    # SQLite WAL 모드 및 Foreign Key 활성화
    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """SQLite 연결 시 프라그마 설정"""
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")  # WAL 모드
            cursor.execute("PRAGMA foreign_keys=ON")  # Foreign Key 활성화
            cursor.execute("PRAGMA synchronous=NORMAL")  # 성능 최적화
            cursor.close()

    logger.info(f"데이터베이스 엔진 생성 완료: {db_url}")
    return engine


# ===== 전역 엔진 및 세션 팩토리 =====
engine = get_engine()
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ===== 데이터베이스 초기화 =====
def init_db() -> None:
    """
    데이터베이스 테이블 생성

    주의: 프로덕션에서는 Alembic 마이그레이션 사용
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


# ===== 세션 관리 =====
def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 의존성

    FastAPI 사용 예시:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()

    Streamlit 사용 예시:
        with get_db_session() as db:
            users = db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"데이터베이스 세션 오류: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    컨텍스트 매니저 기반 세션

    사용 예시:
        with get_db_session() as db:
            user = db.query(User).first()
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"데이터베이스 트랜잭션 오류: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# ===== 데이터베이스 헬스체크 =====
def check_database_connection() -> bool:
    """
    데이터베이스 연결 확인

    Returns:
        bool: 연결 성공 여부
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("데이터베이스 연결 확인 성공")
        return True
    except Exception as e:
        logger.error(f"데이터베이스 연결 확인 실패: {e}")
        return False


# ===== 데이터베이스 정리 =====
def drop_all_tables() -> None:
    """
    모든 테이블 삭제 (개발/테스트 전용)

    경고: 프로덕션에서 사용 금지!
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("모든 데이터베이스 테이블 삭제 완료")
    except Exception as e:
        logger.error(f"테이블 삭제 실패: {e}")
        raise


# ===== 데이터베이스 리셋 =====
def reset_database() -> None:
    """
    데이터베이스 리셋 (개발/테스트 전용)

    경고: 모든 데이터 삭제됨!
    """
    try:
        drop_all_tables()
        init_db()
        logger.warning("데이터베이스 리셋 완료")
    except Exception as e:
        logger.error(f"데이터베이스 리셋 실패: {e}")
        raise


if __name__ == "__main__":
    # 데이터베이스 연결 테스트
    print("=== 데이터베이스 연결 테스트 ===")

    if check_database_connection():
        print("✓ 데이터베이스 연결 성공")

        # 세션 테스트
        with get_db_session() as db:
            print(f"✓ 세션 생성 성공: {db}")

    else:
        print("✗ 데이터베이스 연결 실패")
