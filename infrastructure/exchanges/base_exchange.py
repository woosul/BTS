"""
BTS 거래소 베이스 클래스

모든 거래소 클라이언트의 기반이 되는 추상 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from core.models import OHLCV, MarketPrice
from core.enums import OrderType, OrderSide
from core.exceptions import (
    ExchangeError,
    ExchangeConnectionError,
    ExchangeAPIError,
    InsufficientBalanceError,
    InvalidOrderError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseExchange(ABC):
    """
    거래소 베이스 클래스

    모든 거래소 클라이언트는 이 클래스를 상속받아 구현
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        name: str = "BaseExchange"
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.name = name
        self._is_connected = False

        logger.info(f"거래소 클라이언트 초기화: {self.name}")

    # ===== 연결 관리 =====
    @abstractmethod
    def connect(self) -> bool:
        """
        거래소 연결

        Returns:
            bool: 연결 성공 여부

        Raises:
            ExchangeConnectionError: 연결 실패
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """거래소 연결 해제"""
        pass

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected

    @abstractmethod
    def check_connection(self) -> bool:
        """
        연결 상태 확인 (실제 API 요청)

        Returns:
            bool: 연결 가능 여부
        """
        pass

    # ===== 시장 정보 =====
    @abstractmethod
    def get_markets(self) -> List[str]:
        """
        거래 가능한 마켓 목록 조회

        Returns:
            List[str]: 마켓 심볼 목록 (예: ["KRW-BTC", "KRW-ETH"])

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> MarketPrice:
        """
        현재가 조회

        Args:
            symbol: 거래 심볼

        Returns:
            MarketPrice: 현재가 정보

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def get_orderbook(self, symbol: str) -> Dict:
        """
        호가 정보 조회

        Args:
            symbol: 거래 심볼

        Returns:
            Dict: 호가 정보 (매수/매도 호가)

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> List[OHLCV]:
        """
        OHLCV 데이터 조회

        Args:
            symbol: 거래 심볼
            interval: 시간 간격 (1m, 5m, 1h, 1d 등)
            limit: 조회 개수

        Returns:
            List[OHLCV]: OHLCV 데이터 목록

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    # ===== 잔고 조회 =====
    @abstractmethod
    def get_balance(self, currency: str = "KRW") -> Decimal:
        """
        특정 화폐 잔고 조회

        Args:
            currency: 화폐 코드 (KRW, BTC, ETH 등)

        Returns:
            Decimal: 잔고

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def get_all_balances(self) -> Dict[str, Decimal]:
        """
        전체 잔고 조회

        Returns:
            Dict[str, Decimal]: {화폐: 잔고} 딕셔너리

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    # ===== 주문 =====
    @abstractmethod
    def create_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Optional[Decimal] = None,
        amount: Optional[Decimal] = None
    ) -> Dict:
        """
        시장가 주문

        Args:
            symbol: 거래 심볼
            side: 매수/매도
            quantity: 주문 수량 (매도 시)
            amount: 주문 금액 (매수 시, KRW)

        Returns:
            Dict: 주문 결과

        Raises:
            InvalidOrderError: 잘못된 주문
            InsufficientBalanceError: 잔고 부족
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def create_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal
    ) -> Dict:
        """
        지정가 주문

        Args:
            symbol: 거래 심볼
            side: 매수/매도
            quantity: 주문 수량
            price: 주문 가격

        Returns:
            Dict: 주문 결과

        Raises:
            InvalidOrderError: 잘못된 주문
            InsufficientBalanceError: 잔고 부족
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        주문 취소

        Args:
            order_id: 주문 ID

        Returns:
            bool: 취소 성공 여부

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Dict:
        """
        주문 정보 조회

        Args:
            order_id: 주문 ID

        Returns:
            Dict: 주문 정보

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        미체결 주문 조회

        Args:
            symbol: 거래 심볼 (선택)

        Returns:
            List[Dict]: 미체결 주문 목록

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    @abstractmethod
    def get_order_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        주문 내역 조회

        Args:
            symbol: 거래 심볼 (선택)
            limit: 조회 개수

        Returns:
            List[Dict]: 주문 내역

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    # ===== 거래 내역 =====
    @abstractmethod
    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        거래 내역 조회

        Args:
            symbol: 거래 심볼 (선택)
            limit: 조회 개수

        Returns:
            List[Dict]: 거래 내역

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    # ===== 수수료 =====
    @abstractmethod
    def get_trading_fee(self, symbol: str) -> Dict[str, Decimal]:
        """
        거래 수수료 조회

        Args:
            symbol: 거래 심볼

        Returns:
            Dict[str, Decimal]: {maker_fee, taker_fee}

        Raises:
            ExchangeAPIError: API 요청 실패
        """
        pass

    # ===== 유틸리티 =====
    def validate_symbol(self, symbol: str) -> bool:
        """
        심볼 유효성 검증

        Args:
            symbol: 거래 심볼

        Returns:
            bool: 유효 여부
        """
        try:
            markets = self.get_markets()
            return symbol in markets
        except Exception as e:
            logger.error(f"심볼 검증 실패: {e}")
            return False

    def calculate_order_amount(
        self,
        quantity: Decimal,
        price: Decimal,
        fee_rate: Decimal = Decimal("0.0005")
    ) -> Dict[str, Decimal]:
        """
        주문 금액 계산

        Args:
            quantity: 수량
            price: 가격
            fee_rate: 수수료율

        Returns:
            Dict: {base_amount, fee, total_amount}
        """
        base_amount = quantity * price
        fee = base_amount * fee_rate
        total_amount = base_amount + fee

        return {
            "base_amount": base_amount,
            "fee": fee,
            "total_amount": total_amount
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(name={self.name}, "
            f"connected={self._is_connected})>"
        )


if __name__ == "__main__":
    # 베이스 클래스는 추상 클래스이므로 직접 테스트 불가
    print("=== 거래소 베이스 클래스 ===")
    print("BaseExchange는 추상 클래스입니다.")
    print("구체적인 거래소(Upbit, Bithumb 등)를 구현하여 사용하세요.")
