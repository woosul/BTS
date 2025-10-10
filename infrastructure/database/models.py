"""
BTS SQLAlchemy ORM 모델

데이터베이스 테이블 정의
Pydantic 모델과 분리되어 있음
"""
from typing import Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    Numeric,
    DateTime,
    Text,
    Enum,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.connection import Base
from core.enums import (
    OrderType,
    OrderSide,
    OrderStatus,
    PositionSide,
    StrategyStatus,
    WalletType,
    TransactionType,
    TimeFrame,
)


# ===== 지갑 모델 =====
class WalletORM(Base):
    """지갑 테이블"""
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    wallet_type: Mapped[WalletType] = mapped_column(
        Enum(WalletType),
        nullable=False,
        default=WalletType.VIRTUAL
    )
    balance_krw: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
        default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # 관계
    orders: Mapped[list["OrderORM"]] = relationship(
        "OrderORM",
        back_populates="wallet",
        cascade="all, delete-orphan"
    )
    trades: Mapped[list["TradeORM"]] = relationship(
        "TradeORM",
        back_populates="wallet",
        cascade="all, delete-orphan"
    )
    positions: Mapped[list["PositionORM"]] = relationship(
        "PositionORM",
        back_populates="wallet",
        cascade="all, delete-orphan"
    )
    transactions: Mapped[list["TransactionORM"]] = relationship(
        "TransactionORM",
        back_populates="wallet",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Wallet(id={self.id}, name={self.name}, balance={self.balance_krw})>"


# ===== 자산 보유 모델 =====
class AssetHoldingORM(Base):
    """자산 보유 테이블"""
    __tablename__ = "asset_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=Decimal("0")
    )
    avg_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
        default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_wallet_symbol", "wallet_id", "symbol", unique=True),
    )

    def __repr__(self) -> str:
        return f"<AssetHolding(wallet_id={self.wallet_id}, symbol={self.symbol}, qty={self.quantity})>"


# ===== 주문 모델 =====
class OrderORM(Base):
    """주문 테이블"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )
    strategy_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType),
        nullable=False
    )
    order_side: Mapped[OrderSide] = mapped_column(
        Enum(OrderSide),
        nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        nullable=False,
        default=OrderStatus.PENDING
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False
    )
    price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2),
        nullable=True
    )
    filled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=Decimal("0")
    )
    filled_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2),
        nullable=True
    )
    fee: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
        default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # 관계
    wallet: Mapped["WalletORM"] = relationship("WalletORM", back_populates="orders")
    strategy: Mapped[Optional["StrategyORM"]] = relationship(
        "StrategyORM",
        back_populates="orders"
    )
    trades: Mapped[list["TradeORM"]] = relationship(
        "TradeORM",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, symbol={self.symbol}, side={self.order_side}, status={self.status})>"


# ===== 거래 모델 =====
class TradeORM(Base):
    """거래 테이블"""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    wallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[OrderSide] = mapped_column(
        Enum(OrderSide),
        nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False
    )
    fee: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
        default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True
    )

    # 관계
    order: Mapped["OrderORM"] = relationship("OrderORM", back_populates="trades")
    wallet: Mapped["WalletORM"] = relationship("WalletORM", back_populates="trades")

    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, qty={self.quantity})>"


# ===== 전략 모델 =====
class StrategyORM(Base):
    """전략 테이블"""
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[StrategyStatus] = mapped_column(
        Enum(StrategyStatus),
        nullable=False,
        default=StrategyStatus.INACTIVE
    )
    timeframe: Mapped[TimeFrame] = mapped_column(
        Enum(TimeFrame),
        nullable=False,
        default=TimeFrame.HOUR_1
    )
    parameters: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}"
    )  # JSON 문자열로 저장
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # 관계
    orders: Mapped[list["OrderORM"]] = relationship(
        "OrderORM",
        back_populates="strategy"
    )
    positions: Mapped[list["PositionORM"]] = relationship(
        "PositionORM",
        back_populates="strategy"
    )

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name={self.name}, status={self.status})>"


# ===== 포지션 모델 =====
class PositionORM(Base):
    """포지션 테이블"""
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )
    strategy_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[PositionSide] = mapped_column(
        Enum(PositionSide),
        nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False
    )
    entry_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
        default=Decimal("0")
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # 관계
    wallet: Mapped["WalletORM"] = relationship("WalletORM", back_populates="positions")
    strategy: Mapped[Optional["StrategyORM"]] = relationship(
        "StrategyORM",
        back_populates="positions"
    )

    def __repr__(self) -> str:
        return f"<Position(id={self.id}, symbol={self.symbol}, side={self.side}, qty={self.quantity})>"


# ===== 거래 내역 모델 =====
class TransactionORM(Base):
    """거래 내역 테이블"""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType),
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False
    )
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True
    )

    # 관계
    wallet: Mapped["WalletORM"] = relationship(
        "WalletORM",
        back_populates="transactions"
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type={self.transaction_type}, amount={self.amount})>"


# ===== 필터 프로파일 모델 =====
class FilterProfileORM(Base):
    """필터 프로파일 테이블"""
    __tablename__ = "filter_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # KRW, BTC
    
    # 필터 조건 (JSON 형태로 저장)
    conditions_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 메타데이터
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<FilterProfile(id={self.id}, name={self.name}, market={self.market})>"


# ===== 필터링 결과 모델 =====
class FilteredSymbolORM(Base):
    """필터링된 종목 테이블 - 마지막 필터링 결과만 저장"""
    __tablename__ = "filtered_symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    profile_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    filtered_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        index=True
    )
    
    # 필터링 결과 상세 데이터
    korean_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trading_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)  # 거래대금
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2), nullable=True)  # 시가총액
    listing_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 상장기간 (일)
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), nullable=True)  # 현재가
    volatility: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)  # 변동성 (%)
    spread: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)  # 스프레드 (%)
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 비고

    def __repr__(self):
        return f"<FilteredSymbol(id={self.id}, symbol={self.symbol}, profile_name={self.profile_name}, filtered_at={self.filtered_at})>"


if __name__ == "__main__":
    # ORM 모델 테스트
    from infrastructure.database.connection import engine, init_db

    print("=== SQLAlchemy ORM 모델 테스트 ===")

    # 테이블 생성
    init_db()
    print("✓ 테이블 생성 완료")

    # 테이블 목록 출력
    print("\n생성된 테이블:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
