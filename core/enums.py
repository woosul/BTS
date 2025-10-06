"""
BTS 열거형 상수 모듈

시스템 전반에서 사용되는 상수 정의
타입 안정성 및 일관성 보장
"""
from enum import Enum


class TradingMode(str, Enum):
    """거래 모드"""
    PAPER = "paper"  # 모의투자
    LIVE = "live"  # 실거래


class OrderType(str, Enum):
    """주문 유형"""
    MARKET = "market"  # 시장가
    LIMIT = "limit"  # 지정가


class OrderSide(str, Enum):
    """주문 방향"""
    BUY = "buy"  # 매수
    SELL = "sell"  # 매도


class OrderStatus(str, Enum):
    """주문 상태"""
    PENDING = "pending"  # 대기 중
    SUBMITTED = "submitted"  # 제출됨
    PARTIAL_FILLED = "partial_filled"  # 부분 체결
    FILLED = "filled"  # 체결 완료
    CANCELLED = "cancelled"  # 취소됨
    REJECTED = "rejected"  # 거부됨
    EXPIRED = "expired"  # 만료됨


class PositionSide(str, Enum):
    """포지션 방향"""
    LONG = "long"  # 롱 (매수)
    SHORT = "short"  # 숏 (매도)
    FLAT = "flat"  # 포지션 없음


class StrategySignal(str, Enum):
    """전략 시그널"""
    BUY = "buy"  # 매수 시그널
    SELL = "sell"  # 매도 시그널
    HOLD = "hold"  # 보유


class StrategyStatus(str, Enum):
    """전략 상태"""
    ACTIVE = "active"  # 활성
    INACTIVE = "inactive"  # 비활성
    PAUSED = "paused"  # 일시정지
    ERROR = "error"  # 에러


class TimeFrame(str, Enum):
    """시간 프레임"""
    MINUTE_1 = "1m"  # 1분
    MINUTE_3 = "3m"  # 3분
    MINUTE_5 = "5m"  # 5분
    MINUTE_15 = "15m"  # 15분
    MINUTE_30 = "30m"  # 30분
    HOUR_1 = "1h"  # 1시간
    HOUR_4 = "4h"  # 4시간
    DAY_1 = "1d"  # 1일
    WEEK_1 = "1w"  # 1주


class WalletType(str, Enum):
    """지갑 유형"""
    VIRTUAL = "virtual"  # 가상지갑 (모의투자)
    REAL = "real"  # 실제지갑 (실거래)


class TransactionType(str, Enum):
    """거래 유형"""
    DEPOSIT = "deposit"  # 입금
    WITHDRAWAL = "withdrawal"  # 출금
    TRADE_BUY = "trade_buy"  # 거래 매수
    TRADE_SELL = "trade_sell"  # 거래 매도
    FEE = "fee"  # 수수료
    TRANSFER = "transfer"  # 이체


class AssetType(str, Enum):
    """자산 유형"""
    FIAT = "fiat"  # 법정화폐 (KRW)
    CRYPTO = "crypto"  # 암호화폐


class ExchangeName(str, Enum):
    """거래소 이름"""
    UPBIT = "upbit"
    BITHUMB = "bithumb"
    BINANCE = "binance"
    COINBASE = "coinbase"


class IndicatorType(str, Enum):
    """기술적 지표 유형"""
    RSI = "rsi"  # Relative Strength Index
    MACD = "macd"  # Moving Average Convergence Divergence
    MA = "ma"  # Moving Average (이동평균)
    EMA = "ema"  # Exponential Moving Average
    BBANDS = "bbands"  # Bollinger Bands
    STOCH = "stoch"  # Stochastic Oscillator
    ATR = "atr"  # Average True Range
    VOLUME = "volume"  # 거래량


class LogLevel(str, Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BacktestStatus(str, Enum):
    """백테스트 상태"""
    PENDING = "pending"  # 대기
    RUNNING = "running"  # 실행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패
    CANCELLED = "cancelled"  # 취소


# 상수 정의
DEFAULT_COMMISSION_RATE = 0.0005  # 기본 수수료율 0.05%
DEFAULT_SLIPPAGE_RATE = 0.001  # 기본 슬리피지 0.1%
MIN_ORDER_AMOUNT_KRW = 5000  # 최소 주문 금액 (원화)
MAX_RETRY_COUNT = 3  # 최대 재시도 횟수
REQUEST_TIMEOUT = 30  # API 요청 타임아웃 (초)


if __name__ == "__main__":
    # 열거형 테스트
    print("=== BTS 열거형 상수 ===")
    print(f"거래 모드: {[e.value for e in TradingMode]}")
    print(f"주문 유형: {[e.value for e in OrderType]}")
    print(f"주문 방향: {[e.value for e in OrderSide]}")
    print(f"주문 상태: {[e.value for e in OrderStatus]}")
    print(f"전략 시그널: {[e.value for e in StrategySignal]}")
    print(f"시간 프레임: {[e.value for e in TimeFrame]}")

    # 사용 예시
    signal = StrategySignal.BUY
    print(f"\n시그널 타입: {signal}")
    print(f"시그널 값: {signal.value}")
    print(f"시그널 이름: {signal.name}")
