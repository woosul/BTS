"""
BTS Pydantic DTO 모델

API 요청/응답 및 데이터 전송용 모델
FastAPI/Streamlit에서 공통 사용
"""
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from core.enums import (
    OrderType,
    OrderSide,
    OrderStatus,
    PositionSide,
    StrategySignal,
    StrategyStatus,
    WalletType,
    TransactionType,
    TimeFrame,
)


# ===== 공통 베이스 모델 =====
class BTSBaseModel(BaseModel):
    """BTS 공통 베이스 모델"""
    model_config = ConfigDict(
        from_attributes=True,  # ORM 모델과 호환
        use_enum_values=False,
        validate_assignment=True,
    )


# ===== 지갑 관련 모델 =====
class WalletBase(BTSBaseModel):
    """지갑 기본 모델"""
    name: str = Field(..., description="지갑 이름")
    wallet_type: WalletType = Field(..., description="지갑 유형")


class WalletCreate(WalletBase):
    """지갑 생성 요청"""
    initial_balance: Decimal = Field(
        default=Decimal("0"),
        description="초기 잔고 (KRW)"
    )


class WalletUpdate(BTSBaseModel):
    """지갑 업데이트 요청"""
    name: Optional[str] = None


class WalletResponse(WalletBase):
    """지갑 응답"""
    id: int
    balance_krw: Decimal = Field(..., description="KRW 잔고")
    total_value_krw: Decimal = Field(..., description="총 자산 가치 (KRW)")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetBalance(BTSBaseModel):
    """자산 잔고"""
    symbol: str = Field(..., description="심볼 (예: BTC, ETH)")
    quantity: Decimal = Field(..., description="보유 수량")
    avg_price: Decimal = Field(..., description="평균 매수가")
    current_price: Decimal = Field(..., description="현재가")
    total_value: Decimal = Field(..., description="평가 금액")
    profit_loss: Decimal = Field(..., description="손익")
    profit_loss_rate: Decimal = Field(..., description="수익률")


# ===== 주문 관련 모델 =====
class OrderBase(BTSBaseModel):
    """주문 기본 모델"""
    symbol: str = Field(..., description="거래 심볼 (예: KRW-BTC)")
    order_type: OrderType = Field(..., description="주문 유형")
    order_side: OrderSide = Field(..., description="주문 방향")
    quantity: Decimal = Field(..., gt=0, description="주문 수량")
    price: Optional[Decimal] = Field(None, description="주문 가격 (지정가)")


class OrderCreate(OrderBase):
    """주문 생성 요청"""
    wallet_id: int = Field(..., description="지갑 ID")
    strategy_id: Optional[int] = Field(None, description="전략 ID")


class OrderUpdate(BTSBaseModel):
    """주문 업데이트 요청"""
    status: Optional[OrderStatus] = None
    filled_quantity: Optional[Decimal] = None
    filled_price: Optional[Decimal] = None


class OrderResponse(OrderBase):
    """주문 응답"""
    id: int
    wallet_id: int
    strategy_id: Optional[int]
    status: OrderStatus
    filled_quantity: Decimal
    filled_price: Optional[Decimal]
    total_amount: Decimal = Field(..., description="총 주문 금액")
    fee: Decimal = Field(default=Decimal("0"), description="수수료")
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ===== 거래 관련 모델 =====
class TradeBase(BTSBaseModel):
    """거래 기본 모델"""
    symbol: str = Field(..., description="거래 심볼")
    side: OrderSide = Field(..., description="거래 방향")
    quantity: Decimal = Field(..., gt=0, description="거래 수량")
    price: Decimal = Field(..., gt=0, description="거래 가격")


class TradeCreate(TradeBase):
    """거래 생성 요청"""
    order_id: int = Field(..., description="주문 ID")
    wallet_id: int = Field(..., description="지갑 ID")
    fee: Decimal = Field(default=Decimal("0"), description="수수료")


class TradeResponse(TradeBase):
    """거래 응답"""
    id: int
    order_id: int
    wallet_id: int
    fee: Decimal
    total_amount: Decimal = Field(..., description="총 거래 금액")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===== 전략 관련 모델 =====
class StrategyBase(BTSBaseModel):
    """전략 기본 모델"""
    name: str = Field(..., description="전략 이름")
    description: Optional[str] = Field(None, description="전략 설명")
    timeframe: TimeFrame = Field(..., description="시간 프레임")


class StrategyCreate(StrategyBase):
    """전략 생성 요청"""
    parameters: dict = Field(default_factory=dict, description="전략 파라미터")


class StrategyUpdate(BTSBaseModel):
    """전략 업데이트 요청"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StrategyStatus] = None
    parameters: Optional[dict] = None


class StrategyResponse(StrategyBase):
    """전략 응답"""
    id: int
    status: StrategyStatus
    parameters: dict
    total_trades: int = Field(default=0, description="총 거래 횟수")
    win_rate: Decimal = Field(default=Decimal("0"), description="승률")
    total_profit: Decimal = Field(default=Decimal("0"), description="총 수익")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategySignalData(BTSBaseModel):
    """전략 시그널 데이터"""
    strategy_id: int
    strategy_name: str
    symbol: str
    signal: StrategySignal
    confidence: Decimal = Field(..., ge=0, le=1, description="확신도 (0-1)")
    indicators: dict = Field(default_factory=dict, description="지표 값")
    timestamp: datetime


# ===== 포지션 관련 모델 =====
class PositionBase(BTSBaseModel):
    """포지션 기본 모델"""
    symbol: str = Field(..., description="거래 심볼")
    side: PositionSide = Field(..., description="포지션 방향")


class PositionResponse(PositionBase):
    """포지션 응답"""
    id: int
    wallet_id: int
    strategy_id: Optional[int]
    quantity: Decimal = Field(..., description="보유 수량")
    entry_price: Decimal = Field(..., description="진입 가격")
    current_price: Decimal = Field(..., description="현재 가격")
    unrealized_pnl: Decimal = Field(..., description="미실현 손익")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="실현 손익")
    opened_at: datetime
    closed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ===== 거래 내역 관련 모델 =====
class TransactionBase(BTSBaseModel):
    """거래 내역 기본 모델"""
    transaction_type: TransactionType
    amount: Decimal = Field(..., description="거래 금액")
    description: Optional[str] = Field(None, description="설명")


class TransactionCreate(TransactionBase):
    """거래 내역 생성 요청"""
    wallet_id: int


class TransactionResponse(TransactionBase):
    """거래 내역 응답"""
    id: int
    wallet_id: int
    balance_after: Decimal = Field(..., description="거래 후 잔고")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===== 백테스팅 관련 모델 =====
class BacktestRequest(BTSBaseModel):
    """백테스트 요청"""
    strategy_id: int
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_balance: Decimal = Field(default=Decimal("10000000"))
    timeframe: TimeFrame = Field(default=TimeFrame.HOUR_1)


class BacktestResult(BTSBaseModel):
    """백테스트 결과"""
    strategy_id: int
    symbol: str
    initial_balance: Decimal
    final_balance: Decimal
    total_return: Decimal = Field(..., description="총 수익률")
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    max_drawdown: Decimal = Field(..., description="최대 낙폭")
    sharpe_ratio: Decimal = Field(..., description="샤프 비율")
    profit_factor: Decimal = Field(..., description="수익 팩터")
    start_date: datetime
    end_date: datetime
    trades: List[TradeResponse] = Field(default_factory=list)


# ===== 통계 관련 모델 =====
class TradingStats(BTSBaseModel):
    """트레이딩 통계"""
    total_trades: int
    total_volume: Decimal
    total_profit: Decimal
    win_rate: Decimal
    avg_profit_per_trade: Decimal
    max_profit: Decimal
    max_loss: Decimal
    sharpe_ratio: Decimal


class DailyStats(BTSBaseModel):
    """일별 통계"""
    date: datetime
    trades: int
    volume: Decimal
    profit: Decimal
    balance: Decimal


# ===== 시장 데이터 관련 모델 =====
class MarketPrice(BTSBaseModel):
    """시장 가격"""
    symbol: str
    price: Decimal
    timestamp: datetime


class OHLCV(BTSBaseModel):
    """OHLCV 데이터"""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


if __name__ == "__main__":
    # 모델 테스트
    print("=== BTS Pydantic 모델 테스트 ===")

    # 주문 생성 예시
    order = OrderCreate(
        wallet_id=1,
        symbol="KRW-BTC",
        order_type=OrderType.MARKET,
        order_side=OrderSide.BUY,
        quantity=Decimal("0.001"),
    )
    print(f"주문 생성: {order.model_dump_json(indent=2)}")

    # 전략 시그널 예시
    signal = StrategySignalData(
        strategy_id=1,
        strategy_name="RSI Strategy",
        symbol="KRW-BTC",
        signal=StrategySignal.BUY,
        confidence=Decimal("0.85"),
        indicators={"rsi": 30.5, "price": 50000000},
        timestamp=datetime.now(),
    )
    print(f"\n전략 시그널: {signal.model_dump_json(indent=2)}")
