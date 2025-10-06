"""
BTS 지갑 도메인 엔티티

비즈니스 로직을 포함하는 지갑 엔티티
"""
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime

from core.enums import WalletType, TransactionType
from core.exceptions import InsufficientFundsError, InvalidTransactionError
from utils.logger import get_logger

logger = get_logger(__name__)


class Wallet:
    """
    지갑 도메인 엔티티

    비즈니스 규칙:
    - 잔고는 0 이상이어야 함
    - 출금 시 잔고 확인 필수
    - 모든 거래는 추적 가능해야 함
    """

    def __init__(
        self,
        id: int,
        name: str,
        wallet_type: WalletType,
        balance_krw: Decimal = Decimal("0"),
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.wallet_type = wallet_type
        self._balance_krw = balance_krw
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

        # 자산 보유 내역 (심볼 -> 수량, 평균가)
        self._holdings: Dict[str, Dict[str, Decimal]] = {}

    @property
    def balance_krw(self) -> Decimal:
        """원화 잔고 조회"""
        return self._balance_krw

    @property
    def total_value_krw(self) -> Decimal:
        """
        총 자산 가치 (KRW)

        원화 잔고 + 보유 코인 평가액
        """
        total = self._balance_krw

        for symbol, holding in self._holdings.items():
            quantity = holding.get("quantity", Decimal("0"))
            current_price = holding.get("current_price", Decimal("0"))
            total += quantity * current_price

        return total

    def is_virtual(self) -> bool:
        """가상지갑 여부"""
        return self.wallet_type == WalletType.VIRTUAL

    def is_real(self) -> bool:
        """실제지갑 여부"""
        return self.wallet_type == WalletType.REAL

    # ===== 잔고 관리 =====
    def deposit(self, amount: Decimal, description: str = "") -> Decimal:
        """
        입금

        Args:
            amount: 입금액
            description: 설명

        Returns:
            Decimal: 입금 후 잔고

        Raises:
            InvalidTransactionError: 잘못된 금액
        """
        if amount <= 0:
            raise InvalidTransactionError(
                "입금액은 0보다 커야 합니다",
                {"amount": amount}
            )

        self._balance_krw += amount
        self.updated_at = datetime.now()

        logger.info(
            f"입금 완료 | 지갑: {self.name} | "
            f"금액: {amount:,.0f} KRW | "
            f"잔고: {self._balance_krw:,.0f} KRW"
        )

        return self._balance_krw

    def withdraw(self, amount: Decimal, description: str = "") -> Decimal:
        """
        출금

        Args:
            amount: 출금액
            description: 설명

        Returns:
            Decimal: 출금 후 잔고

        Raises:
            InvalidTransactionError: 잘못된 금액
            InsufficientFundsError: 잔고 부족
        """
        if amount <= 0:
            raise InvalidTransactionError(
                "출금액은 0보다 커야 합니다",
                {"amount": amount}
            )

        if self._balance_krw < amount:
            raise InsufficientFundsError(
                "잔고가 부족합니다",
                {
                    "required": amount,
                    "available": self._balance_krw,
                    "shortage": amount - self._balance_krw
                }
            )

        self._balance_krw -= amount
        self.updated_at = datetime.now()

        logger.info(
            f"출금 완료 | 지갑: {self.name} | "
            f"금액: {amount:,.0f} KRW | "
            f"잔고: {self._balance_krw:,.0f} KRW"
        )

        return self._balance_krw

    def can_afford(self, amount: Decimal) -> bool:
        """
        구매 가능 여부 확인

        Args:
            amount: 필요 금액

        Returns:
            bool: 구매 가능 여부
        """
        return self._balance_krw >= amount

    # ===== 자산 관리 =====
    def add_asset(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal
    ) -> None:
        """
        자산 추가 (매수)

        Args:
            symbol: 코인 심볼
            quantity: 수량
            price: 매수가
        """
        if quantity <= 0:
            raise InvalidTransactionError(
                "수량은 0보다 커야 합니다",
                {"quantity": quantity}
            )

        if symbol not in self._holdings:
            # 신규 보유
            self._holdings[symbol] = {
                "quantity": quantity,
                "avg_price": price,
                "current_price": price,
            }
        else:
            # 추가 매수 (평균 단가 계산)
            holding = self._holdings[symbol]
            old_quantity = holding["quantity"]
            old_avg_price = holding["avg_price"]

            new_quantity = old_quantity + quantity
            new_avg_price = (
                (old_quantity * old_avg_price + quantity * price) / new_quantity
            )

            self._holdings[symbol]["quantity"] = new_quantity
            self._holdings[symbol]["avg_price"] = new_avg_price

        self.updated_at = datetime.now()

        logger.info(
            f"자산 추가 | 지갑: {self.name} | {symbol} | "
            f"수량: +{quantity:.8f} | "
            f"평균가: {self._holdings[symbol]['avg_price']:,.0f} KRW"
        )

    def remove_asset(self, symbol: str, quantity: Decimal) -> None:
        """
        자산 제거 (매도)

        Args:
            symbol: 코인 심볼
            quantity: 수량

        Raises:
            InsufficientFundsError: 보유 수량 부족
        """
        if symbol not in self._holdings:
            raise InsufficientFundsError(
                f"{symbol} 보유 내역이 없습니다",
                {"symbol": symbol}
            )

        holding = self._holdings[symbol]
        current_quantity = holding["quantity"]

        if current_quantity < quantity:
            raise InsufficientFundsError(
                f"{symbol} 보유 수량이 부족합니다",
                {
                    "symbol": symbol,
                    "required": quantity,
                    "available": current_quantity
                }
            )

        new_quantity = current_quantity - quantity

        if new_quantity == 0:
            # 전량 매도
            del self._holdings[symbol]
        else:
            self._holdings[symbol]["quantity"] = new_quantity

        self.updated_at = datetime.now()

        logger.info(
            f"자산 제거 | 지갑: {self.name} | {symbol} | "
            f"수량: -{quantity:.8f} | "
            f"잔여: {new_quantity:.8f}"
        )

    def get_holding(self, symbol: str) -> Optional[Dict[str, Decimal]]:
        """
        자산 보유 내역 조회

        Args:
            symbol: 코인 심볼

        Returns:
            Optional[Dict]: 보유 내역 (quantity, avg_price, current_price)
        """
        return self._holdings.get(symbol)

    def get_all_holdings(self) -> Dict[str, Dict[str, Decimal]]:
        """모든 자산 보유 내역"""
        return self._holdings.copy()

    def has_asset(self, symbol: str, quantity: Decimal) -> bool:
        """
        자산 보유 여부 확인

        Args:
            symbol: 코인 심볼
            quantity: 필요 수량

        Returns:
            bool: 보유 여부
        """
        if symbol not in self._holdings:
            return False

        return self._holdings[symbol]["quantity"] >= quantity

    def update_asset_price(self, symbol: str, current_price: Decimal) -> None:
        """
        자산 현재가 업데이트

        Args:
            symbol: 코인 심볼
            current_price: 현재가
        """
        if symbol in self._holdings:
            self._holdings[symbol]["current_price"] = current_price

    # ===== 수익 계산 =====
    def calculate_asset_profit(self, symbol: str) -> Optional[Dict[str, Decimal]]:
        """
        특정 자산 수익 계산

        Args:
            symbol: 코인 심볼

        Returns:
            Optional[Dict]: 수익 정보 (profit, profit_rate)
        """
        holding = self.get_holding(symbol)
        if not holding:
            return None

        quantity = holding["quantity"]
        avg_price = holding["avg_price"]
        current_price = holding["current_price"]

        total_cost = quantity * avg_price
        current_value = quantity * current_price

        profit = current_value - total_cost
        profit_rate = (profit / total_cost) * 100 if total_cost > 0 else Decimal("0")

        return {
            "symbol": symbol,
            "quantity": quantity,
            "avg_price": avg_price,
            "current_price": current_price,
            "total_cost": total_cost,
            "current_value": current_value,
            "profit": profit,
            "profit_rate": profit_rate,
        }

    def calculate_total_profit(self) -> Dict[str, Decimal]:
        """
        전체 수익 계산

        Returns:
            Dict: 총 수익 정보
        """
        total_cost = Decimal("0")
        total_value = Decimal("0")

        for symbol in self._holdings:
            profit_info = self.calculate_asset_profit(symbol)
            if profit_info:
                total_cost += profit_info["total_cost"]
                total_value += profit_info["current_value"]

        total_profit = total_value - total_cost
        total_profit_rate = (
            (total_profit / total_cost) * 100 if total_cost > 0 else Decimal("0")
        )

        return {
            "total_cost": total_cost,
            "total_value": total_value,
            "total_profit": total_profit,
            "total_profit_rate": total_profit_rate,
            "balance_krw": self._balance_krw,
            "total_assets": total_value + self._balance_krw,
        }

    def __repr__(self) -> str:
        return (
            f"<Wallet(id={self.id}, name={self.name}, "
            f"type={self.wallet_type.value}, balance={self._balance_krw:,.0f} KRW)>"
        )


if __name__ == "__main__":
    # 지갑 엔티티 테스트
    print("=== 지갑 엔티티 테스트 ===")

    # 가상지갑 생성
    wallet = Wallet(
        id=1,
        name="테스트 가상지갑",
        wallet_type=WalletType.VIRTUAL,
        balance_krw=Decimal("10000000")
    )

    print(f"\n1. 지갑 생성: {wallet}")
    print(f"   총 자산: {wallet.total_value_krw:,.0f} KRW")

    # 입금
    wallet.deposit(Decimal("5000000"), "추가 입금")
    print(f"\n2. 입금 후 잔고: {wallet.balance_krw:,.0f} KRW")

    # 자산 추가 (BTC 매수)
    wallet.add_asset("BTC", Decimal("0.1"), Decimal("50000000"))
    print(f"\n3. BTC 매수")
    print(f"   보유: {wallet.get_holding('BTC')}")

    # 현재가 업데이트
    wallet.update_asset_price("BTC", Decimal("55000000"))
    print(f"\n4. BTC 현재가 업데이트: 55,000,000 KRW")

    # 수익 계산
    profit_info = wallet.calculate_asset_profit("BTC")
    print(f"\n5. BTC 수익:")
    print(f"   평균 매수가: {profit_info['avg_price']:,.0f} KRW")
    print(f"   현재가: {profit_info['current_price']:,.0f} KRW")
    print(f"   수익: {profit_info['profit']:,.0f} KRW ({profit_info['profit_rate']:.2f}%)")

    # 전체 수익
    total_profit = wallet.calculate_total_profit()
    print(f"\n6. 전체 자산:")
    print(f"   원화 잔고: {total_profit['balance_krw']:,.0f} KRW")
    print(f"   코인 평가액: {total_profit['total_value']:,.0f} KRW")
    print(f"   총 자산: {total_profit['total_assets']:,.0f} KRW")
    print(f"   총 수익: {total_profit['total_profit']:,.0f} KRW ({total_profit['total_profit_rate']:.2f}%)")
