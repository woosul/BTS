"""
BTS Upbit 거래소 클라이언트

Upbit API 연동 (pyupbit 기반)
"""
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import pyupbit

from infrastructure.exchanges.base_exchange import BaseExchange
from core.models import OHLCV, MarketPrice
from core.enums import OrderSide, TimeFrame
from core.exceptions import (
    ExchangeConnectionError,
    ExchangeAPIError,
    InsufficientBalanceError,
    InvalidOrderError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class UpbitClient(BaseExchange):
    """
    Upbit 거래소 클라이언트

    pyupbit 라이브러리 사용
    """

    def __init__(self, api_key: str = "", api_secret: str = ""):
        super().__init__(api_key, api_secret, "Upbit")
        self.upbit = None

        # 인증 정보가 있으면 자동 연결
        if api_key and api_secret:
            self.connect()

    # ===== 연결 관리 =====
    def connect(self) -> bool:
        """
        Upbit 연결

        Returns:
            bool: 연결 성공 여부
        """
        try:
            if self.api_key and self.api_secret:
                self.upbit = pyupbit.Upbit(self.api_key, self.api_secret)
                # 연결 테스트
                self.upbit.get_balances()
                self._is_connected = True
                logger.info("Upbit 연결 성공 (인증됨)")
            else:
                # 공개 API만 사용
                self.upbit = None
                self._is_connected = True
                logger.info("Upbit 연결 성공 (공개 API)")

            return True

        except Exception as e:
            logger.error(f"Upbit 연결 실패: {e}")
            raise ExchangeConnectionError(
                f"Upbit 연결 실패: {str(e)}",
                {"error": str(e)}
            )

    def disconnect(self) -> None:
        """Upbit 연결 해제"""
        self.upbit = None
        self._is_connected = False
        logger.info("Upbit 연결 해제")

    def check_connection(self) -> bool:
        """
        연결 상태 확인

        Returns:
            bool: 연결 가능 여부
        """
        try:
            # 공개 API 호출로 연결 테스트
            pyupbit.get_current_price("KRW-BTC")
            return True
        except Exception as e:
            logger.error(f"Upbit 연결 확인 실패: {e}")
            return False

    # ===== 시장 정보 =====
    def get_markets(self) -> List[str]:
        """
        KRW 마켓 목록 조회

        Returns:
            List[str]: 마켓 심볼 목록
        """
        try:
            all_markets = pyupbit.get_tickers(fiat="KRW")
            return all_markets

        except Exception as e:
            logger.error(f"마켓 목록 조회 실패: {e}")
            raise ExchangeAPIError(
                f"마켓 목록 조회 실패: {str(e)}",
                {"error": str(e)}
            )

    def get_market_symbols(self, market: str = "KRW") -> List[str]:
        """
        특정 마켓의 심볼 목록 조회

        Args:
            market: 마켓 종류 (KRW, BTC, USDT 등)

        Returns:
            List[str]: 심볼 목록 (예: ["KRW-BTC", "KRW-ETH", ...])
        """
        try:
            if market == "KRW":
                symbols = pyupbit.get_tickers(fiat="KRW")
            elif market == "BTC":
                symbols = pyupbit.get_tickers(fiat="BTC")
            elif market == "USDT":
                symbols = pyupbit.get_tickers(fiat="USDT")
            else:
                # 기본적으로 KRW 마켓
                symbols = pyupbit.get_tickers(fiat="KRW")

            logger.info(f"{market} 마켓 심볼 {len(symbols)}개 조회")
            return symbols

        except Exception as e:
            logger.error(f"마켓 심볼 목록 조회 실패: {e}")
            raise ExchangeAPIError(
                f"마켓 심볼 목록 조회 실패: {str(e)}",
                {"market": market, "error": str(e)}
            )

    def get_ticker(self, symbol: str) -> MarketPrice:
        """
        현재가 조회

        Args:
            symbol: 거래 심볼

        Returns:
            MarketPrice: 현재가 정보
        """
        try:
            price = pyupbit.get_current_price(symbol)

            if price is None:
                raise ExchangeAPIError(
                    f"현재가 조회 실패: {symbol}",
                    {"symbol": symbol}
                )

            return MarketPrice(
                symbol=symbol,
                price=Decimal(str(price)),
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"현재가 조회 실패: {e}")
            raise ExchangeAPIError(
                f"현재가 조회 실패: {str(e)}",
                {"symbol": symbol, "error": str(e)}
            )

    def get_orderbook(self, symbol: str) -> Dict:
        """
        호가 정보 조회

        Args:
            symbol: 거래 심볼

        Returns:
            Dict: 호가 정보
        """
        try:
            orderbook = pyupbit.get_orderbook(symbol)

            if not orderbook:
                raise ExchangeAPIError(
                    f"호가 조회 실패: {symbol}",
                    {"symbol": symbol}
                )

            return {
                "symbol": symbol,
                "bids": orderbook[0]["orderbook_units"],  # 매수 호가
                "asks": orderbook[0]["orderbook_units"],  # 매도 호가
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error(f"호가 조회 실패: {e}")
            raise ExchangeAPIError(
                f"호가 조회 실패: {str(e)}",
                {"symbol": symbol, "error": str(e)}
            )

    def get_ohlcv(
        self,
        symbol: str,
        interval: str = "60",  # Upbit: 1, 3, 5, 15, 10, 30, 60, 240, day, week, month
        limit: int = 100
    ) -> List[OHLCV]:
        """
        OHLCV 데이터 조회

        Args:
            symbol: 거래 심볼
            interval: 시간 간격 (분 단위 또는 day/week/month)
            limit: 조회 개수

        Returns:
            List[OHLCV]: OHLCV 데이터
        """
        try:
            # pyupbit는 count로 개수 제한
            df = pyupbit.get_ohlcv(symbol, interval=interval, count=limit)

            if df is None or df.empty:
                raise ExchangeAPIError(
                    f"OHLCV 조회 실패: {symbol}",
                    {"symbol": symbol, "interval": interval}
                )

            # DataFrame을 OHLCV 모델 리스트로 변환
            ohlcv_list = []
            for index, row in df.iterrows():
                ohlcv = OHLCV(
                    symbol=symbol,
                    timestamp=index.to_pydatetime(),
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    volume=Decimal(str(row["volume"]))
                )
                ohlcv_list.append(ohlcv)

            return ohlcv_list

        except Exception as e:
            logger.error(f"OHLCV 조회 실패: {e}")
            raise ExchangeAPIError(
                f"OHLCV 조회 실패: {str(e)}",
                {"symbol": symbol, "error": str(e)}
            )

    # ===== 잔고 조회 =====
    def get_balance(self, currency: str = "KRW") -> Decimal:
        """
        특정 화폐 잔고 조회

        Args:
            currency: 화폐 코드

        Returns:
            Decimal: 잔고
        """
        self._check_auth()

        try:
            balance = self.upbit.get_balance(currency)
            return Decimal(str(balance))

        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            raise ExchangeAPIError(
                f"잔고 조회 실패: {str(e)}",
                {"currency": currency, "error": str(e)}
            )

    def get_all_balances(self) -> Dict[str, Decimal]:
        """
        전체 잔고 조회

        Returns:
            Dict[str, Decimal]: {화폐: 잔고}
        """
        self._check_auth()

        try:
            balances = self.upbit.get_balances()
            result = {}

            for balance in balances:
                currency = balance["currency"]
                amount = Decimal(str(balance["balance"]))
                if amount > 0:
                    result[currency] = amount

            return result

        except Exception as e:
            logger.error(f"전체 잔고 조회 실패: {e}")
            raise ExchangeAPIError(
                f"전체 잔고 조회 실패: {str(e)}",
                {"error": str(e)}
            )

    # ===== 주문 =====
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
            amount: 주문 금액 (매수 시)

        Returns:
            Dict: 주문 결과
        """
        self._check_auth()

        try:
            if side == OrderSide.BUY:
                if amount is None:
                    raise InvalidOrderError(
                        "시장가 매수는 금액(amount)이 필요합니다",
                        {"side": "buy"}
                    )
                result = self.upbit.buy_market_order(symbol, float(amount))

            else:  # SELL
                if quantity is None:
                    raise InvalidOrderError(
                        "시장가 매도는 수량(quantity)이 필요합니다",
                        {"side": "sell"}
                    )
                result = self.upbit.sell_market_order(symbol, float(quantity))

            if result is None:
                raise ExchangeAPIError("주문 실패: 응답 없음")

            logger.info(
                f"시장가 주문 완료: {symbol} {side.value.upper()} "
                f"{'금액 ' + str(amount) if amount else '수량 ' + str(quantity)}"
            )

            return result

        except Exception as e:
            logger.error(f"시장가 주문 실패: {e}")
            raise ExchangeAPIError(
                f"시장가 주문 실패: {str(e)}",
                {"symbol": symbol, "side": side.value, "error": str(e)}
            )

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
        """
        self._check_auth()

        try:
            if side == OrderSide.BUY:
                result = self.upbit.buy_limit_order(
                    symbol,
                    float(price),
                    float(quantity)
                )
            else:  # SELL
                result = self.upbit.sell_limit_order(
                    symbol,
                    float(price),
                    float(quantity)
                )

            if result is None:
                raise ExchangeAPIError("주문 실패: 응답 없음")

            logger.info(
                f"지정가 주문 완료: {symbol} {side.value.upper()} "
                f"{quantity} @ {price:,.0f}"
            )

            return result

        except Exception as e:
            logger.error(f"지정가 주문 실패: {e}")
            raise ExchangeAPIError(
                f"지정가 주문 실패: {str(e)}",
                {"symbol": symbol, "side": side.value, "error": str(e)}
            )

    def cancel_order(self, order_id: str) -> bool:
        """
        주문 취소

        Args:
            order_id: 주문 ID (UUID)

        Returns:
            bool: 취소 성공 여부
        """
        self._check_auth()

        try:
            result = self.upbit.cancel_order(order_id)
            logger.info(f"주문 취소: {order_id}")
            return result is not None

        except Exception as e:
            logger.error(f"주문 취소 실패: {e}")
            raise ExchangeAPIError(
                f"주문 취소 실패: {str(e)}",
                {"order_id": order_id, "error": str(e)}
            )

    def get_order(self, order_id: str) -> Dict:
        """
        주문 정보 조회

        Args:
            order_id: 주문 ID

        Returns:
            Dict: 주문 정보
        """
        self._check_auth()

        try:
            result = self.upbit.get_order(order_id)
            return result

        except Exception as e:
            logger.error(f"주문 조회 실패: {e}")
            raise ExchangeAPIError(
                f"주문 조회 실패: {str(e)}",
                {"order_id": order_id, "error": str(e)}
            )

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        미체결 주문 조회

        Args:
            symbol: 거래 심볼 (선택)

        Returns:
            List[Dict]: 미체결 주문 목록
        """
        self._check_auth()

        try:
            if symbol:
                orders = self.upbit.get_order(symbol, state="wait")
            else:
                orders = self.upbit.get_order(state="wait")

            return orders if orders else []

        except Exception as e:
            logger.error(f"미체결 주문 조회 실패: {e}")
            raise ExchangeAPIError(
                f"미체결 주문 조회 실패: {str(e)}",
                {"error": str(e)}
            )

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
        """
        self._check_auth()

        try:
            # Upbit는 체결된 주문만 조회 가능
            if symbol:
                orders = self.upbit.get_order(symbol, state="done")
            else:
                orders = self.upbit.get_order(state="done")

            return orders[:limit] if orders else []

        except Exception as e:
            logger.error(f"주문 내역 조회 실패: {e}")
            raise ExchangeAPIError(
                f"주문 내역 조회 실패: {str(e)}",
                {"error": str(e)}
            )

    # ===== 거래 내역 =====
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
        """
        # Upbit는 주문 내역으로 거래 확인
        return self.get_order_history(symbol, limit)

    # ===== 수수료 =====
    def get_trading_fee(self, symbol: str) -> Dict[str, Decimal]:
        """
        거래 수수료 조회

        Upbit 기본 수수료: 0.05%

        Args:
            symbol: 거래 심볼

        Returns:
            Dict[str, Decimal]: {maker_fee, taker_fee}
        """
        # Upbit는 maker/taker 구분 없이 0.05% 고정
        default_fee = Decimal("0.0005")

        return {
            "maker_fee": default_fee,
            "taker_fee": default_fee
        }

    # ===== 유틸리티 =====
    def _check_auth(self) -> None:
        """인증 필요 메서드 검증"""
        if self.upbit is None:
            raise ExchangeConnectionError(
                "인증이 필요한 작업입니다. API 키를 설정하세요.",
                {"authenticated": False}
            )


if __name__ == "__main__":
    from config.settings import settings

    print("=== Upbit 클라이언트 테스트 ===")

    # 공개 API 테스트
    client = UpbitClient()

    # 마켓 조회
    markets = client.get_markets()
    print(f"\n1. KRW 마켓: {len(markets)}개")
    print(f"   예시: {markets[:5]}")

    # 현재가 조회
    ticker = client.get_ticker("KRW-BTC")
    print(f"\n2. BTC 현재가: {ticker.price:,.0f} KRW")

    # OHLCV 조회
    ohlcv = client.get_ohlcv("KRW-BTC", interval="60", limit=10)
    print(f"\n3. OHLCV 데이터: {len(ohlcv)}개")
    if ohlcv:
        latest = ohlcv[-1]
        print(f"   최신: {latest.close:,.0f} KRW @ {latest.timestamp}")

    # 인증 API 테스트 (설정에 키가 있는 경우)
    if settings.upbit_access_key and settings.upbit_secret_key:
        auth_client = UpbitClient(
            settings.upbit_access_key,
            settings.upbit_secret_key
        )

        # 잔고 조회
        krw_balance = auth_client.get_balance("KRW")
        print(f"\n4. KRW 잔고: {krw_balance:,.0f} KRW")

        all_balances = auth_client.get_all_balances()
        print(f"\n5. 전체 잔고: {len(all_balances)}개")
        for currency, balance in all_balances.items():
            print(f"   {currency}: {balance}")
    else:
        print("\n4-5. 인증 테스트 스킵 (API 키 미설정)")
