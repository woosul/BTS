"""
BTS ATR 기반 손절 매도 전략

변동성(ATR)을 고려한 동적 손절
"""
from typing import Dict, List, Optional
from decimal import Decimal

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger

logger = get_logger(__name__)


class ATRStopExitStrategy(BaseExitStrategy):
    """
    ATR 손절 매도 전략

    Average True Range(ATR)를 이용한 변동성 기반 손절
    - 변동성이 클 때는 손절폭 확대
    - 변동성이 작을 때는 손절폭 축소
    """

    def __init__(
        self,
        id: int,
        name: str = "ATR Stop Exit",
        description: str = "ATR 기반 동적 손절 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "atr_period": 14,           # ATR 계산 기간
            "atr_multiplier": 2.0,      # ATR 승수
            "target_profit_pct": 15.0,  # 목표 수익률
            "min_stop_loss_pct": -3.0,  # 최소 손절률
            "max_stop_loss_pct": -10.0, # 최대 손절률
            "min_confidence": 0.85,
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        self.atr_period = int(self.parameters["atr_period"])
        self.atr_multiplier = Decimal(str(self.parameters["atr_multiplier"]))
        self.target_profit_pct = Decimal(str(self.parameters["target_profit_pct"]))
        self.min_stop_loss_pct = Decimal(str(self.parameters["min_stop_loss_pct"]))
        self.max_stop_loss_pct = Decimal(str(self.parameters["max_stop_loss_pct"]))

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        ATR 지표 계산

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Dict: ATR 값

        Raises:
            IndicatorCalculationError: 지표 계산 실패 시
        """
        try:
            if len(ohlcv_data) < self.atr_period:
                raise IndicatorCalculationError(
                    "ATR 계산을 위한 데이터가 부족합니다",
                    {"required": self.atr_period, "provided": len(ohlcv_data)}
                )

            # True Range 계산
            true_ranges = []
            for i in range(1, len(ohlcv_data)):
                high = ohlcv_data[i].high
                low = ohlcv_data[i].low
                prev_close = ohlcv_data[i - 1].close

                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)

            # ATR 계산 (단순 이동평균)
            if len(true_ranges) < self.atr_period:
                atr = sum(true_ranges) / len(true_ranges)
            else:
                atr = sum(true_ranges[-self.atr_period:]) / self.atr_period

            return {
                "atr": Decimal(str(atr)),
                "current_price": ohlcv_data[-1].close,
                "atr_multiplier": self.atr_multiplier
            }

        except Exception as e:
            logger.error(f"ATR 계산 실패: {e}")
            raise IndicatorCalculationError(f"ATR 계산 실패: {str(e)}")

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        매도 조건 체크

        Args:
            entry_price: 매수 가격
            current_price: 현재 가격
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표
            holding_period: 보유 기간

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)
        atr = indicators["atr"]

        # 1. 목표 수익 달성
        if profit_loss_pct >= self.target_profit_pct:
            return True, Decimal("0.95"), f"목표 수익 달성 ({profit_loss_pct:.2f}%)"

        # 2. ATR 기반 동적 손절가 계산
        atr_stop_price = entry_price - (atr * self.atr_multiplier)
        atr_stop_loss_pct = ((atr_stop_price - entry_price) / entry_price) * 100

        # 손절률 범위 제한
        atr_stop_loss_pct = max(
            self.max_stop_loss_pct,
            min(self.min_stop_loss_pct, atr_stop_loss_pct)
        )

        # 3. ATR 손절 체크
        if profit_loss_pct <= atr_stop_loss_pct:
            return (
                True,
                Decimal("0.9"),
                f"ATR 손절 ({profit_loss_pct:.2f}% ≤ {atr_stop_loss_pct:.2f}%, ATR: {atr:,.0f})"
            )

        return False, Decimal("0.5"), "조건 미충족"

    def calculate_atr_stop_price(
        self,
        entry_price: Decimal,
        atr: Decimal
    ) -> Decimal:
        """
        ATR 기반 손절가 계산

        Args:
            entry_price: 진입 가격
            atr: ATR 값

        Returns:
            Decimal: 손절 가격
        """
        stop_price = entry_price - (atr * self.atr_multiplier)

        # 최소/최대 손절가 적용
        min_stop_price = self.calculate_stop_loss_price(entry_price, self.min_stop_loss_pct)
        max_stop_price = self.calculate_stop_loss_price(entry_price, self.max_stop_loss_pct)

        return max(max_stop_price, min(min_stop_price, stop_price))

    def validate_parameters(self) -> bool:
        """
        파라미터 검증

        Returns:
            bool: 검증 성공 여부
        """
        errors = []

        if self.atr_period <= 0:
            errors.append("atr_period는 0보다 커야 합니다")

        if self.atr_multiplier <= 0:
            errors.append("atr_multiplier는 0보다 커야 합니다")

        if self.target_profit_pct <= 0:
            errors.append("target_profit_pct는 0보다 커야 합니다")

        if self.min_stop_loss_pct >= 0:
            errors.append("min_stop_loss_pct는 0보다 작아야 합니다")

        if self.max_stop_loss_pct >= 0:
            errors.append("max_stop_loss_pct는 0보다 작아야 합니다")

        if self.min_stop_loss_pct < self.max_stop_loss_pct:
            errors.append("min_stop_loss_pct는 max_stop_loss_pct보다 커야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "ATR Stop Exit 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """필요한 최소 데이터 개수"""
        return self.atr_period + 10

    def __repr__(self) -> str:
        return (
            f"<ATRStopExitStrategy(name={self.name}, "
            f"period={self.atr_period}, multiplier={self.atr_multiplier})>"
        )


if __name__ == "__main__":
    print("=== ATR 손절 매도 전략 테스트 ===")

    from datetime import datetime, timedelta
    import random

    # 테스트 데이터 생성 (변동성 포함)
    test_data = []
    base_price = Decimal("50000000")
    entry_price = Decimal("50000000")
    base_time = datetime.now()

    for i in range(30):
        volatility = random.uniform(-0.02, 0.02)
        price = base_price * (1 + Decimal(str(volatility)))

        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=price,
            high=price * Decimal("1.01"),
            low=price * Decimal("0.99"),
            close=price,
            volume=Decimal("100")
        )
        test_data.append(candle)

    # 전략 생성
    strategy = ATRStopExitStrategy(
        id=1,
        parameters={
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "target_profit_pct": 15.0,
            "min_stop_loss_pct": -3.0,
            "max_stop_loss_pct": -10.0,
        }
    )

    strategy.activate()

    # 매도 평가
    signal_data = strategy.evaluate_exit(
        symbol="KRW-BTC",
        entry_price=entry_price,
        ohlcv_data=test_data
    )

    print(f"\n시그널: {signal_data.signal.value.upper()}")
    print(f"확신도: {signal_data.confidence:.2%}")
    print(f"현재가: {signal_data.price:,.0f} KRW")
    print(f"진입가: {entry_price:,.0f} KRW")
    print(f"손익률: {signal_data.indicators['profit_loss_pct']:.2f}%")
    print(f"ATR: {signal_data.indicators['atr']:,.0f} KRW")
    print(f"이유: {signal_data.metadata.get('reason', 'N/A')}")

    # ATR 손절가 계산
    atr_stop = strategy.calculate_atr_stop_price(
        entry_price,
        signal_data.indicators['atr']
    )
    print(f"\nATR 손절가: {atr_stop:,.0f} KRW")
