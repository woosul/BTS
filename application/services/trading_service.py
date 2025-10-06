"""
BTS 트레이딩 서비스

주문 및 거래 비즈니스 로직
Streamlit과 FastAPI에서 공통 사용
"""
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

from infrastructure.repositories.order_repository import OrderRepository, TradeRepository
from infrastructure.repositories.wallet_repository import WalletRepository, AssetHoldingRepository
from infrastructure.exchanges.upbit_client import UpbitClient
from domain.entities.order import Order
from domain.entities.trade import Trade
from core.models import OrderCreate, OrderResponse, TradeResponse
from core.enums import OrderType, OrderSide, OrderStatus, WalletType
from core.exceptions import (
    InvalidOrderError,
    InsufficientFundsError,
    OrderExecutionError,
    WalletNotFoundError
)
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class TradingService:
    """
    트레이딩 서비스

    주문 생성, 체결, 취소 등 거래 관련 로직 처리
    """

    def __init__(self, db: Session, exchange: Optional[UpbitClient] = None):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.trade_repo = TradeRepository(db)
        self.wallet_repo = WalletRepository(db)
        self.holding_repo = AssetHoldingRepository(db)

        # 거래소 클라이언트
        self.exchange = exchange or UpbitClient(
            settings.upbit_access_key,
            settings.upbit_secret_key
        )

    # ===== 주문 생성 =====
    def create_order(self, order_data: OrderCreate) -> OrderResponse:
        """
        주문 생성

        Args:
            order_data: 주문 생성 데이터

        Returns:
            OrderResponse: 생성된 주문

        Raises:
            WalletNotFoundError: 지갑을 찾을 수 없음
            InvalidOrderError: 잘못된 주문
            InsufficientFundsError: 잔고 부족
        """
        # 지갑 조회
        wallet = self.wallet_repo.get_by_id_or_raise(order_data.wallet_id)

        # 최소 주문 금액 검증
        if order_data.order_type == OrderType.LIMIT and order_data.price:
            total_amount = order_data.quantity * order_data.price
            if total_amount < Decimal("5000"):
                raise InvalidOrderError(
                    "최소 주문 금액은 5,000원입니다",
                    {"amount": total_amount}
                )

        # 매수: 원화 잔고 확인
        if order_data.order_side == OrderSide.BUY:
            required_amount = self._calculate_required_amount(order_data)
            if wallet.balance_krw < required_amount:
                raise InsufficientFundsError(
                    "원화 잔고가 부족합니다",
                    {
                        "required": required_amount,
                        "available": wallet.balance_krw
                    }
                )

        # 매도: 코인 보유량 확인
        elif order_data.order_side == OrderSide.SELL:
            # 심볼에서 코인 추출 (KRW-BTC → BTC)
            coin = order_data.symbol.split("-")[1]
            holding = self.holding_repo.get_holding(wallet.id, coin)

            if not holding or holding.quantity < order_data.quantity:
                raise InsufficientFundsError(
                    f"{coin} 보유량이 부족합니다",
                    {
                        "required": order_data.quantity,
                        "available": holding.quantity if holding else Decimal("0")
                    }
                )

        # 주문 생성
        order_orm = self.order_repo.create(
            wallet_id=order_data.wallet_id,
            strategy_id=order_data.strategy_id,
            symbol=order_data.symbol,
            order_type=order_data.order_type,
            order_side=order_data.order_side,
            quantity=order_data.quantity,
            price=order_data.price,
            status=OrderStatus.PENDING
        )

        logger.info(
            f"주문 생성: {order_orm.symbol} {order_orm.order_side.value.upper()} "
            f"{order_orm.quantity}"
        )

        return self._to_order_response(order_orm)

    def execute_order(
        self,
        order_id: int,
        auto_execute: bool = True
    ) -> OrderResponse:
        """
        주문 실행

        Args:
            order_id: 주문 ID
            auto_execute: 자동 실행 여부 (False면 제출만)

        Returns:
            OrderResponse: 실행된 주문

        Raises:
            OrderExecutionError: 주문 실행 실패
        """
        order_orm = self.order_repo.get_by_id_or_raise(order_id)
        wallet = self.wallet_repo.get_by_id_or_raise(order_orm.wallet_id)

        # 도메인 엔티티로 변환
        order = Order(
            id=order_orm.id,
            wallet_id=order_orm.wallet_id,
            symbol=order_orm.symbol,
            order_type=order_orm.order_type,
            order_side=order_orm.order_side,
            quantity=order_orm.quantity,
            price=order_orm.price,
            strategy_id=order_orm.strategy_id,
            status=order_orm.status
        )

        # 주문 제출
        order.submit()
        self.order_repo.update(order_id, status=OrderStatus.SUBMITTED)

        # 모의투자: 즉시 체결 시뮬레이션
        if wallet.wallet_type == WalletType.VIRTUAL or not auto_execute:
            filled_price = self._get_market_price(order_orm.symbol)
            fee = self._calculate_fee(order_orm.quantity, filled_price)

            # 체결 처리
            order.fill(order_orm.quantity, filled_price, fee)

            # DB 업데이트
            self.order_repo.update(
                order_id,
                status=OrderStatus.FILLED,
                filled_quantity=order_orm.quantity,
                filled_price=filled_price,
                fee=fee,
                executed_at=datetime.now()
            )

            # 거래 기록 생성
            self._create_trade_record(order_orm, filled_price, fee)

            # 지갑 업데이트
            self._update_wallet_after_trade(
                order_orm.wallet_id,
                order_orm.symbol,
                order_orm.order_side,
                order_orm.quantity,
                filled_price,
                fee
            )

            logger.info(f"모의투자 주문 체결: {order_orm.symbol} @ {filled_price:,.0f}")

        # 실거래: 거래소 API 호출
        else:
            try:
                if order_orm.order_type == OrderType.MARKET:
                    # 시장가 주문
                    if order_orm.order_side == OrderSide.BUY:
                        amount = order_orm.quantity * self._get_market_price(order_orm.symbol)
                        result = self.exchange.create_market_order(
                            order_orm.symbol,
                            order_orm.order_side,
                            amount=amount
                        )
                    else:
                        result = self.exchange.create_market_order(
                            order_orm.symbol,
                            order_orm.order_side,
                            quantity=order_orm.quantity
                        )
                else:
                    # 지정가 주문
                    result = self.exchange.create_limit_order(
                        order_orm.symbol,
                        order_orm.order_side,
                        order_orm.quantity,
                        order_orm.price
                    )

                logger.info(f"실거래 주문 제출: {result.get('uuid', 'unknown')}")

            except Exception as e:
                logger.error(f"주문 실행 실패: {e}")
                order.reject(str(e))
                self.order_repo.update(order_id, status=OrderStatus.REJECTED)
                raise OrderExecutionError(
                    f"주문 실행 실패: {str(e)}",
                    {"order_id": order_id, "error": str(e)}
                )

        # 업데이트된 주문 반환
        order_orm = self.order_repo.get_by_id(order_id)
        return self._to_order_response(order_orm)

    def cancel_order(self, order_id: int) -> OrderResponse:
        """
        주문 취소

        Args:
            order_id: 주문 ID

        Returns:
            OrderResponse: 취소된 주문
        """
        order_orm = self.order_repo.get_by_id_or_raise(order_id)

        # 도메인 엔티티로 변환
        order = Order(
            id=order_orm.id,
            wallet_id=order_orm.wallet_id,
            symbol=order_orm.symbol,
            order_type=order_orm.order_type,
            order_side=order_orm.order_side,
            quantity=order_orm.quantity,
            price=order_orm.price,
            status=order_orm.status
        )

        # 취소
        order.cancel()
        self.order_repo.update(order_id, status=OrderStatus.CANCELLED)

        logger.info(f"주문 취소: {order_id}")
        return self._to_order_response(order_orm)

    # ===== 주문 조회 =====
    def get_order(self, order_id: int) -> OrderResponse:
        """주문 조회"""
        order_orm = self.order_repo.get_by_id_or_raise(order_id)
        return self._to_order_response(order_orm)

    def get_wallet_orders(
        self,
        wallet_id: int,
        limit: int = 100
    ) -> List[OrderResponse]:
        """지갑의 주문 목록 조회"""
        orders = self.order_repo.get_by_wallet(wallet_id, limit)
        return [self._to_order_response(o) for o in orders]

    def get_active_orders(
        self,
        wallet_id: Optional[int] = None
    ) -> List[OrderResponse]:
        """활성 주문 조회"""
        orders = self.order_repo.get_active_orders(wallet_id)
        return [self._to_order_response(o) for o in orders]

    # ===== 거래 내역 조회 =====
    def get_wallet_trades(
        self,
        wallet_id: int,
        limit: int = 100
    ) -> List[TradeResponse]:
        """지갑의 거래 내역 조회"""
        trades = self.trade_repo.get_by_wallet(wallet_id, limit)
        return [self._to_trade_response(t) for t in trades]

    # ===== 내부 메서드 =====
    def _calculate_required_amount(self, order_data: OrderCreate) -> Decimal:
        """매수 필요 금액 계산"""
        if order_data.order_type == OrderType.MARKET:
            price = self._get_market_price(order_data.symbol)
        else:
            price = order_data.price

        base_amount = order_data.quantity * price
        fee = self._calculate_fee(order_data.quantity, price)
        return base_amount + fee

    def _get_market_price(self, symbol: str) -> Decimal:
        """현재 시장가 조회"""
        ticker = self.exchange.get_ticker(symbol)
        return ticker.price

    def _calculate_fee(self, quantity: Decimal, price: Decimal) -> Decimal:
        """수수료 계산"""
        base_amount = quantity * price
        fee_rate = Decimal("0.0005")  # 0.05%
        return base_amount * fee_rate

    def _create_trade_record(
        self,
        order_orm,
        filled_price: Decimal,
        fee: Decimal
    ) -> None:
        """거래 기록 생성"""
        self.trade_repo.create(
            order_id=order_orm.id,
            wallet_id=order_orm.wallet_id,
            symbol=order_orm.symbol,
            side=order_orm.order_side,
            quantity=order_orm.quantity,
            price=filled_price,
            fee=fee
        )

    def _update_wallet_after_trade(
        self,
        wallet_id: int,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal
    ) -> None:
        """거래 후 지갑 업데이트"""
        wallet = self.wallet_repo.get_by_id_or_raise(wallet_id)
        coin = symbol.split("-")[1]  # KRW-BTC → BTC

        if side == OrderSide.BUY:
            # 원화 차감
            total_cost = quantity * price + fee
            new_balance = wallet.balance_krw - total_cost
            self.wallet_repo.update_balance(wallet_id, new_balance)

            # 코인 추가
            holding = self.holding_repo.get_holding(wallet_id, coin)
            if holding:
                new_quantity = holding.quantity + quantity
                new_avg_price = (
                    (holding.quantity * holding.avg_price + quantity * price) / new_quantity
                )
            else:
                new_quantity = quantity
                new_avg_price = price

            self.holding_repo.update_holding(
                wallet_id, coin, new_quantity, new_avg_price
            )

        else:  # SELL
            # 원화 추가
            total_value = quantity * price - fee
            new_balance = wallet.balance_krw + total_value
            self.wallet_repo.update_balance(wallet_id, new_balance)

            # 코인 차감
            holding = self.holding_repo.get_holding(wallet_id, coin)
            if holding:
                new_quantity = holding.quantity - quantity
                if new_quantity <= 0:
                    self.holding_repo.remove_holding(wallet_id, coin)
                else:
                    self.holding_repo.update_holding(
                        wallet_id, coin, new_quantity, holding.avg_price
                    )

    def _to_order_response(self, order_orm) -> OrderResponse:
        """ORM → Response 변환"""
        return OrderResponse(
            id=order_orm.id,
            wallet_id=order_orm.wallet_id,
            strategy_id=order_orm.strategy_id,
            symbol=order_orm.symbol,
            order_type=order_orm.order_type,
            order_side=order_orm.order_side,
            quantity=order_orm.quantity,
            price=order_orm.price,
            status=order_orm.status,
            filled_quantity=order_orm.filled_quantity,
            filled_price=order_orm.filled_price,
            total_amount=order_orm.quantity * (order_orm.filled_price or order_orm.price or Decimal("0")),
            fee=order_orm.fee,
            created_at=order_orm.created_at,
            updated_at=order_orm.updated_at,
            executed_at=order_orm.executed_at
        )

    def _to_trade_response(self, trade_orm) -> TradeResponse:
        """ORM → Response 변환"""
        return TradeResponse(
            id=trade_orm.id,
            order_id=trade_orm.order_id,
            wallet_id=trade_orm.wallet_id,
            symbol=trade_orm.symbol,
            side=trade_orm.side,
            quantity=trade_orm.quantity,
            price=trade_orm.price,
            fee=trade_orm.fee,
            total_amount=trade_orm.quantity * trade_orm.price,
            created_at=trade_orm.created_at
        )


if __name__ == "__main__":
    from infrastructure.database.connection import get_db_session

    print("=== 트레이딩 서비스 테스트 ===")

    with get_db_session() as db:
        service = TradingService(db)

        # 주문 생성
        order_data = OrderCreate(
            wallet_id=1,
            symbol="KRW-BTC",
            order_type=OrderType.MARKET,
            order_side=OrderSide.BUY,
            quantity=Decimal("0.001")
        )

        try:
            order = service.create_order(order_data)
            print(f"\n1. 주문 생성: {order.symbol} - {order.status.value}")

            # 주문 실행
            order = service.execute_order(order.id)
            print(f"\n2. 주문 실행: {order.status.value}")

        except Exception as e:
            print(f"\n오류: {e}")
