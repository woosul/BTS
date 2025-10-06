"""
BTS 주문 도메인 엔티티

비즈니스 로직을 포함하는 주문 엔티티
"""
from typing import Optional
from decimal import Decimal
from datetime import datetime

from core.enums import OrderType, OrderSide, OrderStatus
from core.exceptions import InvalidOrderError, OrderValidationError
from utils.logger import get_logger

logger = get_logger(__name__)


class Order:
    """
    주문 도메인 엔티티

    비즈니스 규칙:
    - 주문 수량은 0보다 커야 함
    - 지정가 주문은 가격 필수
    - 시장가 주문은 가격 불필요
    - 체결 수량은 주문 수량을 초과할 수 없음
    """

    def __init__(
        self,
        id: int,
        wallet_id: int,
        symbol: str,
        order_type: OrderType,
        order_side: OrderSide,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        strategy_id: Optional[int] = None,
        status: OrderStatus = OrderStatus.PENDING,
        filled_quantity: Decimal = Decimal("0"),
        filled_price: Optional[Decimal] = None,
        fee: Decimal = Decimal("0"),
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        executed_at: Optional[datetime] = None,
    ):
        self.id = id
        self.wallet_id = wallet_id
        self.symbol = symbol
        self.order_type = order_type
        self.order_side = order_side
        self.quantity = quantity
        self.price = price
        self.strategy_id = strategy_id
        self.status = status
        self.filled_quantity = filled_quantity
        self.filled_price = filled_price
        self.fee = fee
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.executed_at = executed_at

        # 생성 시 검증
        self._validate()

    def _validate(self) -> None:
        """주문 유효성 검증"""
        # 수량 검증
        if self.quantity <= 0:
            raise OrderValidationError(
                "주문 수량은 0보다 커야 합니다",
                {"quantity": self.quantity}
            )

        # 지정가 주문 가격 검증
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise OrderValidationError(
                "지정가 주문은 가격이 필요합니다",
                {"order_type": self.order_type.value}
            )

        if self.price is not None and self.price <= 0:
            raise OrderValidationError(
                "주문 가격은 0보다 커야 합니다",
                {"price": self.price}
            )

    # ===== 상태 확인 =====
    def is_pending(self) -> bool:
        """대기 중 여부"""
        return self.status == OrderStatus.PENDING

    def is_submitted(self) -> bool:
        """제출됨 여부"""
        return self.status == OrderStatus.SUBMITTED

    def is_filled(self) -> bool:
        """체결 완료 여부"""
        return self.status == OrderStatus.FILLED

    def is_partial_filled(self) -> bool:
        """부분 체결 여부"""
        return self.status == OrderStatus.PARTIAL_FILLED

    def is_cancelled(self) -> bool:
        """취소됨 여부"""
        return self.status == OrderStatus.CANCELLED

    def is_active(self) -> bool:
        """활성 상태 여부 (대기 중 또는 부분 체결)"""
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIAL_FILLED
        ]

    def is_completed(self) -> bool:
        """완료 상태 여부 (체결 또는 취소)"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]

    def is_buy(self) -> bool:
        """매수 주문 여부"""
        return self.order_side == OrderSide.BUY

    def is_sell(self) -> bool:
        """매도 주문 여부"""
        return self.order_side == OrderSide.SELL

    def is_market_order(self) -> bool:
        """시장가 주문 여부"""
        return self.order_type == OrderType.MARKET

    def is_limit_order(self) -> bool:
        """지정가 주문 여부"""
        return self.order_type == OrderType.LIMIT

    # ===== 상태 변경 =====
    def submit(self) -> None:
        """주문 제출"""
        if not self.is_pending():
            raise InvalidOrderError(
                "대기 중인 주문만 제출할 수 있습니다",
                {"current_status": self.status.value}
            )

        self.status = OrderStatus.SUBMITTED
        self.updated_at = datetime.now()

        logger.info(
            f"주문 제출 | ID: {self.id} | {self.symbol} | "
            f"{self.order_side.value.upper()} {self.quantity:.8f}"
        )

    def fill(
        self,
        filled_quantity: Decimal,
        filled_price: Decimal,
        fee: Decimal = Decimal("0")
    ) -> None:
        """
        주문 체결

        Args:
            filled_quantity: 체결 수량
            filled_price: 체결 가격
            fee: 수수료
        """
        if not self.is_active():
            raise InvalidOrderError(
                "활성 상태의 주문만 체결할 수 있습니다",
                {"current_status": self.status.value}
            )

        if filled_quantity <= 0:
            raise OrderValidationError(
                "체결 수량은 0보다 커야 합니다",
                {"filled_quantity": filled_quantity}
            )

        if self.filled_quantity + filled_quantity > self.quantity:
            raise OrderValidationError(
                "체결 수량이 주문 수량을 초과할 수 없습니다",
                {
                    "order_quantity": self.quantity,
                    "already_filled": self.filled_quantity,
                    "new_fill": filled_quantity,
                    "total": self.filled_quantity + filled_quantity
                }
            )

        # 체결 정보 업데이트
        self.filled_quantity += filled_quantity
        self.filled_price = filled_price
        self.fee += fee
        self.updated_at = datetime.now()

        # 상태 업데이트
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
            self.executed_at = datetime.now()
            logger.info(
                f"주문 완전 체결 | ID: {self.id} | {self.symbol} | "
                f"{self.order_side.value.upper()} {self.filled_quantity:.8f} @ {filled_price:,.0f}"
            )
        else:
            self.status = OrderStatus.PARTIAL_FILLED
            logger.info(
                f"주문 부분 체결 | ID: {self.id} | {self.symbol} | "
                f"{filled_quantity:.8f} / {self.quantity:.8f}"
            )

    def cancel(self, reason: str = "") -> None:
        """
        주문 취소

        Args:
            reason: 취소 사유
        """
        if not self.is_active():
            raise InvalidOrderError(
                "활성 상태의 주문만 취소할 수 있습니다",
                {"current_status": self.status.value}
            )

        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now()

        logger.info(
            f"주문 취소 | ID: {self.id} | {self.symbol} | "
            f"사유: {reason or '없음'}"
        )

    def reject(self, reason: str = "") -> None:
        """
        주문 거부

        Args:
            reason: 거부 사유
        """
        self.status = OrderStatus.REJECTED
        self.updated_at = datetime.now()

        logger.warning(
            f"주문 거부 | ID: {self.id} | {self.symbol} | "
            f"사유: {reason or '없음'}"
        )

    # ===== 계산 =====
    def get_total_amount(self) -> Decimal:
        """
        총 주문 금액 계산

        Returns:
            Decimal: 총 금액 (수량 * 가격)
        """
        if self.price is None:
            return Decimal("0")

        return self.quantity * self.price

    def get_filled_amount(self) -> Decimal:
        """
        체결된 금액 계산

        Returns:
            Decimal: 체결 금액
        """
        if self.filled_price is None:
            return Decimal("0")

        return self.filled_quantity * self.filled_price

    def get_remaining_quantity(self) -> Decimal:
        """
        미체결 수량

        Returns:
            Decimal: 남은 수량
        """
        return self.quantity - self.filled_quantity

    def get_fill_percentage(self) -> Decimal:
        """
        체결률

        Returns:
            Decimal: 체결률 (0-100)
        """
        if self.quantity == 0:
            return Decimal("0")

        return (self.filled_quantity / self.quantity) * 100

    def get_net_amount(self) -> Decimal:
        """
        순 금액 (수수료 차감)

        Returns:
            Decimal: 순 금액
        """
        return self.get_filled_amount() - self.fee

    # ===== 전략 연관 =====
    def is_from_strategy(self) -> bool:
        """전략 주문 여부"""
        return self.strategy_id is not None

    def is_manual(self) -> bool:
        """수동 주문 여부"""
        return self.strategy_id is None

    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, {self.symbol}, "
            f"{self.order_side.value} {self.order_type.value}, "
            f"qty={self.quantity:.8f}, status={self.status.value})>"
        )


if __name__ == "__main__":
    # 주문 엔티티 테스트
    print("=== 주문 엔티티 테스트 ===")

    # 시장가 매수 주문
    order = Order(
        id=1,
        wallet_id=1,
        symbol="KRW-BTC",
        order_type=OrderType.MARKET,
        order_side=OrderSide.BUY,
        quantity=Decimal("0.1"),
    )

    print(f"\n1. 주문 생성: {order}")
    print(f"   상태: {order.status.value}")

    # 주문 제출
    order.submit()
    print(f"\n2. 주문 제출됨: {order.status.value}")

    # 부분 체결
    order.fill(
        filled_quantity=Decimal("0.05"),
        filled_price=Decimal("50000000"),
        fee=Decimal("12500")
    )
    print(f"\n3. 부분 체결:")
    print(f"   체결 수량: {order.filled_quantity:.8f}")
    print(f"   체결률: {order.get_fill_percentage():.2f}%")
    print(f"   상태: {order.status.value}")

    # 완전 체결
    order.fill(
        filled_quantity=Decimal("0.05"),
        filled_price=Decimal("50000000"),
        fee=Decimal("12500")
    )
    print(f"\n4. 완전 체결:")
    print(f"   체결 수량: {order.filled_quantity:.8f}")
    print(f"   체결 금액: {order.get_filled_amount():,.0f} KRW")
    print(f"   수수료: {order.fee:,.0f} KRW")
    print(f"   순 금액: {order.get_net_amount():,.0f} KRW")
    print(f"   상태: {order.status.value}")

    # 지정가 주문
    limit_order = Order(
        id=2,
        wallet_id=1,
        symbol="KRW-ETH",
        order_type=OrderType.LIMIT,
        order_side=OrderSide.SELL,
        quantity=Decimal("1.0"),
        price=Decimal("3000000"),
    )

    print(f"\n5. 지정가 주문: {limit_order}")
    print(f"   총 주문 금액: {limit_order.get_total_amount():,.0f} KRW")
