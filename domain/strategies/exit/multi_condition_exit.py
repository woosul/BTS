"""
BTS 복합 조건 매도 전략

여러 매도 조건을 OR 조합으로 평가
"""
from typing import Dict, List, Optional
from decimal import Decimal

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_rsi, calculate_ema

logger = get_logger(__name__)


class MultiConditionExitStrategy(BaseExitStrategy):
    """
    복합 조건 매도 전략

    다음 조건 중 하나라도 충족 시 매도:
    - 목표 수익률 달성
    - 손절률 도달
    - RSI 과매수
    - 보유 기간 초과
    - MA 데드 크로스
    """

    def __init__(
        self,
        id: int,
        name: str = "Multi-Condition Exit",
        description: str = "복합 조건 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            # 수익/손실 조건
            "use_profit_target": True,
            "target_profit_pct": 10.0,
            "use_stop_loss": True,
            "stop_loss_pct": -5.0,
            # RSI 조건
            "use_rsi": True,
            "rsi_period": 14,
            "rsi_overbought": 75,
            # 시간 조건
            "use_time_based": True,
            "max_holding_periods": 48,  # 48시간 (1시간봉 기준)
            # MA 조건
            "use_ma_cross": True,
            "ma_short_period": 20,
            "ma_long_period": 60,
            # 기타
            "min_confidence": 0.75,
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        # 조건 활성화 여부
        self.use_profit_target = self.parameters["use_profit_target"]
        self.use_stop_loss = self.parameters["use_stop_loss"]
        self.use_rsi = self.parameters["use_rsi"]
        self.use_time_based = self.parameters["use_time_based"]
        self.use_ma_cross = self.parameters["use_ma_cross"]

        # 파라미터
        self.target_profit_pct = Decimal(str(self.parameters["target_profit_pct"]))
        self.stop_loss_pct = Decimal(str(self.parameters["stop_loss_pct"]))
        self.rsi_period = int(self.parameters["rsi_period"])
        self.rsi_overbought = Decimal(str(self.parameters["rsi_overbought"]))
        self.max_holding_periods = int(self.parameters["max_holding_periods"])
        self.ma_short_period = int(self.parameters["ma_short_period"])
        self.ma_long_period = int(self.parameters["ma_long_period"])

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        복합 지표 계산

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Dict: 모든 지표 값
        """
        try:
            indicators = {"current_price": ohlcv_data[-1].close}
            closes = [float(candle.close) for candle in ohlcv_data]

            # 1. RSI 계산
            if self.use_rsi and len(ohlcv_data) >= self.rsi_period:
                rsi_values = calculate_rsi(closes, self.rsi_period)
                indicators["rsi"] = Decimal(str(rsi_values[-1])) if rsi_values else Decimal("50")

            # 2. MA 계산
            if self.use_ma_cross and len(ohlcv_data) >= self.ma_long_period:
                ma_short = calculate_ema(closes, self.ma_short_period)
                ma_long = calculate_ema(closes, self.ma_long_period)

                indicators["ma_short"] = Decimal(str(ma_short[-1]))
                indicators["ma_long"] = Decimal(str(ma_long[-1]))
                indicators["prev_ma_short"] = Decimal(str(ma_short[-2])) if len(ma_short) > 1 else indicators["ma_short"]
                indicators["prev_ma_long"] = Decimal(str(ma_long[-2])) if len(ma_long) > 1 else indicators["ma_long"]

            return indicators

        except Exception as e:
            logger.error(f"복합 지표 계산 실패: {e}")
            raise IndicatorCalculationError(f"복합 지표 계산 실패: {str(e)}")

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        복합 조건 체크 (OR 조합)

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
        reasons = []

        # 1. 목표 수익 체크
        if self.use_profit_target and profit_loss_pct >= self.target_profit_pct:
            return True, Decimal("0.95"), f"목표 수익 달성 ({profit_loss_pct:.2f}%)"

        # 2. 손절 체크
        if self.use_stop_loss and profit_loss_pct <= self.stop_loss_pct:
            return True, Decimal("0.98"), f"손절 ({profit_loss_pct:.2f}%)"

        # 3. RSI 과매수 체크
        if self.use_rsi and "rsi" in indicators:
            rsi = indicators["rsi"]
            if rsi >= self.rsi_overbought:
                return True, Decimal("0.8"), f"RSI 과매수 ({rsi:.2f} ≥ {self.rsi_overbought})"

        # 4. 보유 기간 초과 체크
        if self.use_time_based and holding_period >= self.max_holding_periods:
            confidence = Decimal("0.7") if profit_loss_pct > 0 else Decimal("0.85")
            return (
                True,
                confidence,
                f"보유 기간 초과 ({holding_period} ≥ {self.max_holding_periods}, 수익률: {profit_loss_pct:.2f}%)"
            )

        # 5. MA 데드 크로스 체크
        if self.use_ma_cross and "ma_short" in indicators:
            ma_short = indicators["ma_short"]
            ma_long = indicators["ma_long"]
            prev_ma_short = indicators["prev_ma_short"]
            prev_ma_long = indicators["prev_ma_long"]

            # 데드 크로스: 단기 MA가 장기 MA를 하향 돌파
            if prev_ma_short >= prev_ma_long and ma_short < ma_long:
                return True, Decimal("0.85"), "MA 데드 크로스"

        return False, Decimal("0.5"), "조건 미충족"

    def validate_parameters(self) -> bool:
        """
        파라미터 검증

        Returns:
            bool: 검증 성공 여부
        """
        errors = []

        # 최소 하나의 조건은 활성화되어야 함
        if not any([
            self.use_profit_target,
            self.use_stop_loss,
            self.use_rsi,
            self.use_time_based,
            self.use_ma_cross
        ]):
            errors.append("최소 하나의 매도 조건은 활성화해야 합니다")

        if self.use_profit_target and self.target_profit_pct <= 0:
            errors.append("target_profit_pct는 0보다 커야 합니다")

        if self.use_stop_loss and self.stop_loss_pct >= 0:
            errors.append("stop_loss_pct는 0보다 작아야 합니다")

        if self.use_rsi:
            if self.rsi_period <= 0:
                errors.append("rsi_period는 0보다 커야 합니다")
            if not (50 < self.rsi_overbought <= 100):
                errors.append("rsi_overbought는 50과 100 사이여야 합니다")

        if self.use_time_based and self.max_holding_periods <= 0:
            errors.append("max_holding_periods는 0보다 커야 합니다")

        if self.use_ma_cross:
            if self.ma_short_period <= 0:
                errors.append("ma_short_period는 0보다 커야 합니다")
            if self.ma_long_period <= 0:
                errors.append("ma_long_period는 0보다 커야 합니다")
            if self.ma_short_period >= self.ma_long_period:
                errors.append("ma_short_period는 ma_long_period보다 작아야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "Multi-Condition Exit 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """필요한 최소 데이터 개수"""
        min_points = 1

        if self.use_rsi:
            min_points = max(min_points, self.rsi_period + 10)

        if self.use_ma_cross:
            min_points = max(min_points, self.ma_long_period + 10)

        return min_points

    def __repr__(self) -> str:
        active_conditions = []
        if self.use_profit_target:
            active_conditions.append(f"Target={self.target_profit_pct}%")
        if self.use_stop_loss:
            active_conditions.append(f"Stop={self.stop_loss_pct}%")
        if self.use_rsi:
            active_conditions.append("RSI")
        if self.use_time_based:
            active_conditions.append("Time")
        if self.use_ma_cross:
            active_conditions.append("MA")

        return (
            f"<MultiConditionExitStrategy(name={self.name}, "
            f"conditions=[{', '.join(active_conditions)}])>"
        )


if __name__ == "__main__":
    print("=== 복합 조건 매도 전략 테스트 ===")

    from datetime import datetime, timedelta

    # 테스트 데이터 생성
    test_data = []
    base_price = Decimal("50000000")
    entry_price = Decimal("50000000")
    base_time = datetime.now()

    for i in range(70):
        # 상승 후 하락 패턴
        if i < 30:
            price = base_price + Decimal(str(i * 100000))
        else:
            price = base_price + Decimal(str((60 - i) * 100000))

        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=price,
            high=price + Decimal("50000"),
            low=price - Decimal("50000"),
            close=price,
            volume=Decimal("100")
        )
        test_data.append(candle)

    # 전략 생성
    strategy = MultiConditionExitStrategy(
        id=1,
        parameters={
            "use_profit_target": True,
            "target_profit_pct": 10.0,
            "use_stop_loss": True,
            "stop_loss_pct": -5.0,
            "use_rsi": True,
            "use_time_based": True,
            "max_holding_periods": 48,
            "use_ma_cross": True,
        }
    )

    strategy.activate()

    # 매도 평가 (50시간 보유)
    signal_data = strategy.evaluate_exit(
        symbol="KRW-BTC",
        entry_price=entry_price,
        ohlcv_data=test_data,
        holding_period=50
    )

    print(f"\n시그널: {signal_data.signal.value.upper()}")
    print(f"확신도: {signal_data.confidence:.2%}")
    print(f"현재가: {signal_data.price:,.0f} KRW")
    print(f"손익률: {signal_data.indicators['profit_loss_pct']:.2f}%")
    print(f"보유 기간: {signal_data.metadata.get('holding_period', 0)} 시간")
    print(f"이유: {signal_data.metadata.get('reason', 'N/A')}")
