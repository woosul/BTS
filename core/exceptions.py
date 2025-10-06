"""
BTS 커스텀 예외 모듈

계층별, 기능별 예외 클래스 정의
명확한 에러 처리 및 로깅 지원
"""


# ===== 기본 예외 클래스 =====
class BTSException(Exception):
    """BTS 최상위 예외 클래스"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ===== 설정 관련 예외 =====
class ConfigurationError(BTSException):
    """설정 오류"""
    pass


class InvalidTradingModeError(ConfigurationError):
    """잘못된 거래 모드"""
    pass


class MissingAPIKeyError(ConfigurationError):
    """API 키 누락"""
    pass


# ===== 데이터베이스 관련 예외 =====
class DatabaseError(BTSException):
    """데이터베이스 오류"""
    pass


class DatabaseConnectionError(DatabaseError):
    """데이터베이스 연결 오류"""
    pass


class RecordNotFoundError(DatabaseError):
    """레코드를 찾을 수 없음"""
    pass


class DuplicateRecordError(DatabaseError):
    """중복 레코드"""
    pass


# ===== 거래소 관련 예외 =====
class ExchangeError(BTSException):
    """거래소 오류"""
    pass


class ExchangeConnectionError(ExchangeError):
    """거래소 연결 오류"""
    pass


class ExchangeAPIError(ExchangeError):
    """거래소 API 오류"""
    pass


class InsufficientBalanceError(ExchangeError):
    """잔고 부족"""
    pass


class InvalidOrderError(ExchangeError):
    """잘못된 주문"""
    pass


class OrderNotFoundError(ExchangeError):
    """주문을 찾을 수 없음"""
    pass


class RateLimitExceededError(ExchangeError):
    """API 요청 제한 초과"""
    pass


# ===== 지갑 관련 예외 =====
class WalletError(BTSException):
    """지갑 오류"""
    pass


class InsufficientFundsError(WalletError):
    """자금 부족"""
    pass


class InvalidTransactionError(WalletError):
    """잘못된 거래"""
    pass


class WalletNotFoundError(WalletError):
    """지갑을 찾을 수 없음"""
    pass


# ===== 주문 관련 예외 =====
class OrderError(BTSException):
    """주문 오류"""
    pass


class OrderValidationError(OrderError):
    """주문 검증 오류"""
    pass


class OrderExecutionError(OrderError):
    """주문 실행 오류"""
    pass


class OrderCancellationError(OrderError):
    """주문 취소 오류"""
    pass


class MinimumOrderAmountError(OrderError):
    """최소 주문 금액 미달"""
    pass


# ===== 전략 관련 예외 =====
class StrategyError(BTSException):
    """전략 오류"""
    pass


class StrategyNotFoundError(StrategyError):
    """전략을 찾을 수 없음"""
    pass


class StrategyInitializationError(StrategyError):
    """전략 초기화 오류"""
    pass


class StrategyExecutionError(StrategyError):
    """전략 실행 오류"""
    pass


class InvalidSignalError(StrategyError):
    """잘못된 시그널"""
    pass


class IndicatorCalculationError(StrategyError):
    """지표 계산 오류"""
    pass


# ===== 백테스팅 관련 예외 =====
class BacktestError(BTSException):
    """백테스팅 오류"""
    pass


class InvalidBacktestPeriodError(BacktestError):
    """잘못된 백테스팅 기간"""
    pass


class BacktestDataError(BacktestError):
    """백테스팅 데이터 오류"""
    pass


class BacktestExecutionError(BacktestError):
    """백테스팅 실행 오류"""
    pass


# ===== 데이터 관련 예외 =====
class DataError(BTSException):
    """데이터 오류"""
    pass


class DataFetchError(DataError):
    """데이터 조회 오류"""
    pass


class DataValidationError(DataError):
    """데이터 검증 오류"""
    pass


class MissingDataError(DataError):
    """데이터 누락"""
    pass


class InvalidTimeFrameError(DataError):
    """잘못된 시간 프레임"""
    pass


# ===== 인증/권한 관련 예외 =====
class AuthenticationError(BTSException):
    """인증 오류"""
    pass


class AuthorizationError(BTSException):
    """권한 오류"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """잘못된 인증 정보"""
    pass


# ===== 네트워크 관련 예외 =====
class NetworkError(BTSException):
    """네트워크 오류"""
    pass


class TimeoutError(NetworkError):
    """타임아웃"""
    pass


class ConnectionError(NetworkError):
    """연결 오류"""
    pass


# ===== 검증 관련 예외 =====
class ValidationError(BTSException):
    """검증 오류"""
    pass


class InvalidParameterError(ValidationError):
    """잘못된 파라미터"""
    pass


class InvalidSymbolError(ValidationError):
    """잘못된 심볼"""
    pass


class InvalidAmountError(ValidationError):
    """잘못된 금액"""
    pass


# ===== 리스크 관리 관련 예외 =====
class RiskManagementError(BTSException):
    """리스크 관리 오류"""
    pass


class MaxPositionSizeExceededError(RiskManagementError):
    """최대 포지션 크기 초과"""
    pass


class MaxDrawdownExceededError(RiskManagementError):
    """최대 손실률 초과"""
    pass


class DailyLossLimitExceededError(RiskManagementError):
    """일일 손실 한도 초과"""
    pass


# 예외 매핑 (외부 라이브러리 예외 → BTS 예외)
EXCEPTION_MAPPING = {
    "insufficient_funds": InsufficientBalanceError,
    "invalid_order": InvalidOrderError,
    "rate_limit": RateLimitExceededError,
    "not_found": RecordNotFoundError,
    "duplicate": DuplicateRecordError,
}


def map_external_exception(error_code: str, message: str) -> BTSException:
    """
    외부 에러 코드를 BTS 예외로 매핑

    Args:
        error_code: 외부 에러 코드
        message: 에러 메시지

    Returns:
        BTSException: 매핑된 BTS 예외
    """
    exception_class = EXCEPTION_MAPPING.get(error_code, BTSException)
    return exception_class(message, {"error_code": error_code})


if __name__ == "__main__":
    # 예외 테스트
    print("=== BTS 예외 클래스 ===")

    try:
        raise InsufficientBalanceError(
            "잔고가 부족합니다",
            {"required": 100000, "available": 50000}
        )
    except BTSException as e:
        print(f"예외 발생: {e}")

    try:
        raise InvalidOrderError("최소 주문 금액은 5,000원입니다")
    except BTSException as e:
        print(f"예외 발생: {e}")

    # 예외 매핑 테스트
    mapped_error = map_external_exception("insufficient_funds", "잔고 부족")
    print(f"매핑된 예외: {type(mapped_error).__name__} - {mapped_error}")
