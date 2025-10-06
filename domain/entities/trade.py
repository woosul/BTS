"""
BTS 거래 도메인 엔티티

비즈니스 로직을 포함하는 거래 엔티티
"""
from decimal import Decimal
from datetime import datetime
from typing import Optional

from core.enums import OrderSide
from core.exceptions import InvalidTransactionError
from utils.logger import get_logger

logger = get_logger(__name__)


class Trade:
    """
    거래 도메인 엔티티

    주문 체결의 결과로 생성되는 실제 거래 기록
    """

    def __init__(
        self,
        id: int,
        order_id: int,
        wallet_id: int,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal("0"),
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.order_id = order_id
        self.wallet_id = wallet_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.fee = fee
        self.created_at = created_at or datetime.now()

        # 생성 시 검증
        self._validate()

    def _validate(self) -> None:
        """거래 유효성 검증"""
        if self.quantity <= 0:
            raise InvalidTransactionError(
                "거래 수량은 0보다 커야 합니다",
                {"quantity": self.quantity}
            )

        if self.price <= 0:
            raise InvalidTransactionError(
                "거래 가격은 0보다 커야 합니다",
                {"price": self.price}
            )

        if self.fee < 0:
            raise InvalidTransactionError(
                "수수료는 0 이상이어야 합니다",
                {"fee": self.fee}
            )

    # ===== 거래 정보 =====
    def is_buy(self) -> bool:
        """매수 거래 여부"""
        return self.side == OrderSide.BUY

    def is_sell(self) -> bool:
        """매도 거래 여부"""
        return self.side == OrderSide.SELL

    def get_total_amount(self) -> Decimal:
        """
        총 거래 금액 (수수료 포함)

        Returns:
            Decimal: 총 금액
        """
        base_amount = self.quantity * self.price
        return base_amount + self.fee if self.is_buy() else base_amount - self.fee

    def get_base_amount(self) -> Decimal:
        """
        기본 거래 금액 (수수료 제외)

        Returns:
            Decimal: 기본 금액
        """
        return self.quantity * self.price

    def get_average_price(self) -> Decimal:
        """
        평균 단가 (수수료 포함)

        Returns:
            Decimal: 평균 단가
        """
        total_amount = self.get_total_amount()
        return total_amount / self.quantity if self.quantity > 0 else Decimal("0")

    # ===== 손익 계산 =====
    def calculate_profit(
        self,
        current_price: Decimal,
        exit_fee: Decimal = Decimal("0")
    ) -> dict:
        """
        현재가 기준 손익 계산

        Args:
            current_price: 현재 가격
            exit_fee: 청산 시 예상 수수료

        Returns:
            dict: 손익 정보
        """
        if self.is_buy():
            # 매수 거래: 현재가로 매도 시 손익
            entry_cost = self.get_total_amount()  # 매수 총액 (수수료 포함)
            exit_value = self.quantity * current_price - exit_fee
            profit = exit_value - entry_cost
            profit_rate = (profit / entry_cost) * 100 if entry_cost > 0 else Decimal("0")

        else:
            # 매도 거래: 현재가로 재매수 시 손익
            entry_value = self.get_total_amount()  # 매도 총액 (수수료 차감)
            exit_cost = self.quantity * current_price + exit_fee
            profit = entry_value - exit_cost
            profit_rate = (profit / exit_cost) * 100 if exit_cost > 0 else Decimal("0")

        return {
            "profit": profit,
            "profit_rate": profit_rate,
            "current_price": current_price,
            "entry_price": self.price,
        }

    def calculate_pnl_against_trade(self, other_trade: "Trade") -> dict:
        """
        다른 거래와의 손익 계산 (매수-매도 쌍)

        Args:
            other_trade: 반대 거래 (매수 ↔ 매도)

        Returns:
            dict: 손익 정보

        Raises:
            InvalidTransactionError: 같은 방향의 거래인 경우
        """
        if self.side == other_trade.side:
            raise InvalidTransactionError(
                "손익 계산은 반대 방향의 거래끼리만 가능합니다",
                {
                    "trade1_side": self.side.value,
                    "trade2_side": other_trade.side.value
                }
            )

        # 매수/매도 구분
        buy_trade = self if self.is_buy() else other_trade
        sell_trade = other_trade if self.is_buy() else self

        # 수량 확인 (작은 수량 기준)
        matched_quantity = min(buy_trade.quantity, sell_trade.quantity)

        # 손익 계산
        buy_cost = (buy_trade.quantity * buy_trade.price) + buy_trade.fee
        sell_value = (sell_trade.quantity * sell_trade.price) - sell_trade.fee

        # 수량 비율 적용
        buy_ratio = matched_quantity / buy_trade.quantity if buy_trade.quantity > 0 else Decimal("0")
        sell_ratio = matched_quantity / sell_trade.quantity if sell_trade.quantity > 0 else Decimal("0")

        matched_buy_cost = buy_cost * buy_ratio
        matched_sell_value = sell_value * sell_ratio

        profit = matched_sell_value - matched_buy_cost
        profit_rate = (profit / matched_buy_cost) * 100 if matched_buy_cost > 0 else Decimal("0")

        return {
            "matched_quantity": matched_quantity,
            "buy_price": buy_trade.price,
            "sell_price": sell_trade.price,
            "buy_cost": matched_buy_cost,
            "sell_value": matched_sell_value,
            "profit": profit,
            "profit_rate": profit_rate,
            "holding_period": (sell_trade.created_at - buy_trade.created_at).total_seconds() / 3600,  # 시간 단위
        }

    # ===== 통계 =====
    def get_trade_info(self) -> dict:
        """
        거래 정보 요약

        Returns:
            dict: 거래 정보
        """
        return {
            "id": self.id,
            "order_id": self.order_id,
            "wallet_id": self.wallet_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "total_amount": self.get_total_amount(),
            "base_amount": self.get_base_amount(),
            "fee": self.fee,
            "fee_rate": (self.fee / self.get_base_amount()) * 100 if self.get_base_amount() > 0 else Decimal("0"),
            "average_price": self.get_average_price(),
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"<Trade(id={self.id}, {self.symbol}, "
            f"{self.side.value.upper()} {self.quantity:.8f} @ {self.price:,.0f})>"
        )


if __name__ == "__main__":
    # 거래 엔티티 테스트
    print("=== 거래 엔티티 테스트 ===")

    # 매수 거래
    buy_trade = Trade(
        id=1,
        order_id=1,
        wallet_id=1,
        symbol="KRW-BTC",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
        price=Decimal("50000000"),
        fee=Decimal("25000"),
    )

    print(f"\n1. 매수 거래: {buy_trade}")
    print(f"   기본 금액: {buy_trade.get_base_amount():,.0f} KRW")
    print(f"   총 금액: {buy_trade.get_total_amount():,.0f} KRW")
    print(f"   평균 단가: {buy_trade.get_average_price():,.0f} KRW")

    # 현재가 기준 손익
    profit_info = buy_trade.calculate_profit(
        current_price=Decimal("55000000"),
        exit_fee=Decimal("27500")
    )
    print(f"\n2. 현재가 손익 (55,000,000 KRW):")
    print(f"   손익: {profit_info['profit']:,.0f} KRW")
    print(f"   수익률: {profit_info['profit_rate']:.2f}%")

    # 매도 거래
    sell_trade = Trade(
        id=2,
        order_id=2,
        wallet_id=1,
        symbol="KRW-BTC",
        side=OrderSide.SELL,
        quantity=Decimal("0.1"),
        price=Decimal("55000000"),
        fee=Decimal("27500"),
    )

    print(f"\n3. 매도 거래: {sell_trade}")

    # 매수-매도 손익 계산
    pnl = buy_trade.calculate_pnl_against_trade(sell_trade)
    print(f"\n4. 매수-매도 손익:")
    print(f"   매수가: {pnl['buy_price']:,.0f} KRW")
    print(f"   매도가: {pnl['sell_price']:,.0f} KRW")
    print(f"   손익: {pnl['profit']:,.0f} KRW")
    print(f"   수익률: {pnl['profit_rate']:.2f}%")
    print(f"   보유 시간: {pnl['holding_period']:.2f} 시간")

    # 거래 정보
    info = buy_trade.get_trade_info()
    print(f"\n5. 거래 정보:")
    print(f"   심볼: {info['symbol']}")
    print(f"   수량: {info['quantity']:.8f}")
    print(f"   수수료율: {info['fee_rate']:.2f}%")
