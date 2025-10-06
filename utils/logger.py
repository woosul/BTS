"""
BTS 로깅 모듈

Loguru를 사용한 구조화된 로깅
Streamlit과 FastAPI에서 공통 사용
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import settings


def setup_logger() -> None:
    """
    Loguru 로거 초기화

    - 콘솔 출력: 컬러 포맷
    - 파일 출력: JSON 포맷 (rotation, retention)
    - 레벨별 필터링
    """
    # 기본 핸들러 제거
    logger.remove()

    # 콘솔 핸들러 추가 (컬러 출력)
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 로그 디렉토리 생성
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 파일 핸들러 추가 (JSON 포맷)
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=settings.log_level,
        rotation="10 MB",  # 10MB마다 로테이션
        retention="30 days",  # 30일간 보관
        compression="zip",  # 압축 저장
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    # 에러 전용 로그 파일 추가
    error_log_path = log_path.parent / "error.log"
    logger.add(
        str(error_log_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",  # 에러 로그는 90일간 보관
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    logger.info(f"로거 초기화 완료 - 레벨: {settings.log_level}")


def get_logger(name: str = None):
    """
    특정 모듈용 로거 반환

    사용 예:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Trading started")
    """
    if name:
        return logger.bind(name=name)
    return logger


# 애플리케이션 시작 시 자동 초기화
setup_logger()


# 편의 함수들
def log_trade(symbol: str, side: str, quantity: float, price: float) -> None:
    """거래 로그 기록"""
    logger.info(
        f"거래 실행 | {symbol} | {side.upper()} | "
        f"수량: {quantity:.8f} | 가격: {price:,.0f} KRW"
    )


def log_strategy_signal(
    strategy_name: str,
    symbol: str,
    signal: str,
    confidence: float
) -> None:
    """전략 시그널 로그 기록"""
    logger.info(
        f"전략 시그널 | {strategy_name} | {symbol} | "
        f"{signal.upper()} | 확신도: {confidence:.2%}"
    )


def log_error_with_context(error: Exception, context: dict) -> None:
    """컨텍스트 포함 에러 로그"""
    logger.error(
        f"에러 발생: {type(error).__name__} | "
        f"메시지: {str(error)} | "
        f"컨텍스트: {context}"
    )


if __name__ == "__main__":
    # 로깅 테스트
    logger.debug("디버그 메시지")
    logger.info("정보 메시지")
    logger.warning("경고 메시지")
    logger.error("에러 메시지")

    log_trade("KRW-BTC", "buy", 0.001, 50000000)
    log_strategy_signal("RSI", "KRW-BTC", "buy", 0.85)

    try:
        raise ValueError("테스트 에러")
    except Exception as e:
        log_error_with_context(e, {"symbol": "KRW-BTC", "action": "test"})
