"""
BTS 주문 및 거래 Repository

주문/거래 데이터 접근 계층
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import OrderORM, TradeORM
from core.enums import OrderStatus, OrderSide
from utils.logger import get_logger

logger = get_logger(__name__)


class OrderRepository(BaseRepository[OrderORM]):
    """주문 Repository"""

    def __init__(self, db: Session):
        super().__init__(OrderORM, db)

    def get_by_wallet(self, wallet_id: int, limit: int = 100) -> List[OrderORM]:
        """
        지갑의 주문 목록 조회

        Args:
            wallet_id: 지갑 ID
            limit: 최대 조회 수

        Returns:
            List[OrderORM]: 주문 목록
        """
        stmt = (
            select(OrderORM)
            .where(OrderORM.wallet_id == wallet_id)
            .order_by(OrderORM.created_at.desc())
            .limit(limit)
        )
        result = self.db.execute(stmt).scalars().all()
        return list(result)

    def get_by_symbol(self, symbol: str, limit: int = 100) -> List[OrderORM]:
        """
        심볼별 주문 조회

        Args:
            symbol: 거래 심볼
            limit: 최대 조회 수

        Returns:
            List[OrderORM]: 주문 목록
        """
        return self.filter_by(symbol=symbol)[:limit]

    def get_active_orders(
        self,
        wallet_id: Optional[int] = None
    ) -> List[OrderORM]:
        """
        활성 주문 조회 (대기 중, 부분 체결)

        Args:
            wallet_id: 지갑 ID (선택)

        Returns:
            List[OrderORM]: 활성 주문 목록
        """
        stmt = select(OrderORM).where(
            OrderORM.status.in_([
                OrderStatus.PENDING,
                OrderStatus.SUBMITTED,
                OrderStatus.PARTIAL_FILLED
            ])
        )

        if wallet_id:
            stmt = stmt.where(OrderORM.wallet_id == wallet_id)

        stmt = stmt.order_by(OrderORM.created_at.desc())
        result = self.db.execute(stmt).scalars().all()
        return list(result)

    def get_by_strategy(
        self,
        strategy_id: int,
        limit: int = 100
    ) -> List[OrderORM]:
        """
        전략별 주문 조회

        Args:
            strategy_id: 전략 ID
            limit: 최대 조회 수

        Returns:
            List[OrderORM]: 주문 목록
        """
        stmt = (
            select(OrderORM)
            .where(OrderORM.strategy_id == strategy_id)
            .order_by(OrderORM.created_at.desc())
            .limit(limit)
        )
        result = self.db.execute(stmt).scalars().all()
        return list(result)

    def get_filled_orders(
        self,
        wallet_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[OrderORM]:
        """
        체결 완료 주문 조회

        Args:
            wallet_id: 지갑 ID
            start_date: 시작일
            end_date: 종료일

        Returns:
            List[OrderORM]: 체결 주문 목록
        """
        stmt = select(OrderORM).where(OrderORM.status == OrderStatus.FILLED)

        if wallet_id:
            stmt = stmt.where(OrderORM.wallet_id == wallet_id)

        if start_date:
            stmt = stmt.where(OrderORM.executed_at >= start_date)

        if end_date:
            stmt = stmt.where(OrderORM.executed_at <= end_date)

        stmt = stmt.order_by(OrderORM.executed_at.desc())
        result = self.db.execute(stmt).scalars().all()
        return list(result)


class TradeRepository(BaseRepository[TradeORM]):
    """거래 Repository"""

    def __init__(self, db: Session):
        super().__init__(TradeORM, db)

    def get_by_order(self, order_id: int) -> List[TradeORM]:
        """
        주문의 거래 내역 조회

        Args:
            order_id: 주문 ID

        Returns:
            List[TradeORM]: 거래 목록
        """
        return self.filter_by(order_id=order_id)

    def get_by_wallet(
        self,
        wallet_id: int,
        limit: int = 100
    ) -> List[TradeORM]:
        """
        지갑의 거래 내역 조회

        Args:
            wallet_id: 지갑 ID
            limit: 최대 조회 수

        Returns:
            List[TradeORM]: 거래 목록
        """
        stmt = (
            select(TradeORM)
            .where(TradeORM.wallet_id == wallet_id)
            .order_by(TradeORM.created_at.desc())
            .limit(limit)
        )
        result = self.db.execute(stmt).scalars().all()
        return list(result)

    def get_by_symbol(
        self,
        symbol: str,
        wallet_id: Optional[int] = None,
        limit: int = 100
    ) -> List[TradeORM]:
        """
        심볼별 거래 조회

        Args:
            symbol: 거래 심볼
            wallet_id: 지갑 ID (선택)
            limit: 최대 조회 수

        Returns:
            List[TradeORM]: 거래 목록
        """
        stmt = select(TradeORM).where(TradeORM.symbol == symbol)

        if wallet_id:
            stmt = stmt.where(TradeORM.wallet_id == wallet_id)

        stmt = stmt.order_by(TradeORM.created_at.desc()).limit(limit)
        result = self.db.execute(stmt).scalars().all()
        return list(result)

    def get_by_side(
        self,
        side: OrderSide,
        wallet_id: Optional[int] = None,
        limit: int = 100
    ) -> List[TradeORM]:
        """
        매수/매도별 거래 조회

        Args:
            side: 거래 방향
            wallet_id: 지갑 ID (선택)
            limit: 최대 조회 수

        Returns:
            List[TradeORM]: 거래 목록
        """
        stmt = select(TradeORM).where(TradeORM.side == side)

        if wallet_id:
            stmt = stmt.where(TradeORM.wallet_id == wallet_id)

        stmt = stmt.order_by(TradeORM.created_at.desc()).limit(limit)
        result = self.db.execute(stmt).scalars().all()
        return list(result)

    def get_trades_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        wallet_id: Optional[int] = None
    ) -> List[TradeORM]:
        """
        기간별 거래 조회

        Args:
            start_date: 시작일
            end_date: 종료일
            wallet_id: 지갑 ID (선택)

        Returns:
            List[TradeORM]: 거래 목록
        """
        stmt = select(TradeORM).where(
            and_(
                TradeORM.created_at >= start_date,
                TradeORM.created_at <= end_date
            )
        )

        if wallet_id:
            stmt = stmt.where(TradeORM.wallet_id == wallet_id)

        stmt = stmt.order_by(TradeORM.created_at.asc())
        result = self.db.execute(stmt).scalars().all()
        return list(result)


if __name__ == "__main__":
    from infrastructure.database.connection import get_db_session
    from decimal import Decimal
    from core.enums import OrderType, OrderSide, OrderStatus

    print("=== 주문/거래 Repository 테스트 ===")

    with get_db_session() as db:
        order_repo = OrderRepository(db)
        trade_repo = TradeRepository(db)

        # 주문 생성
        order = order_repo.create(
            wallet_id=1,
            symbol="KRW-BTC",
            order_type=OrderType.MARKET,
            order_side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            status=OrderStatus.FILLED,
            filled_quantity=Decimal("0.1"),
            filled_price=Decimal("50000000"),
            fee=Decimal("25000"),
            executed_at=datetime.now()
        )
        print(f"\n1. 주문 생성: {order.symbol} - {order.order_side.value}")

        # 거래 생성
        trade = trade_repo.create(
            order_id=order.id,
            wallet_id=1,
            symbol="KRW-BTC",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            price=Decimal("50000000"),
            fee=Decimal("25000")
        )
        print(f"\n2. 거래 생성: {trade.symbol} - {trade.quantity:.8f}")

        # 조회
        wallet_orders = order_repo.get_by_wallet(1)
        print(f"\n3. 지갑 주문: {len(wallet_orders)}개")

        wallet_trades = trade_repo.get_by_wallet(1)
        print(f"\n4. 지갑 거래: {len(wallet_trades)}개")
