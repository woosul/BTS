"""
BTS Stochastic 매수 전략

Stochastic Oscillator 지표 기반 매수 전략
- %K와 %D 골든 크로스
- 과매도 구간에서 반등
"""
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from domain.strategies.entry.base_entry import BaseEntryStrategy
from core.enums import StrategySignal, TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger

logger = get_logger(__name__)


class StochasticEntryStrategy(BaseEntryStrategy):
    """
    Stochastic 매수 전략

    %K와 %D 교차 및 과매도 구간 반등 시그널 포착
    """

    def __init__(
        self,
        id: int,
        name: str = "Stochastic Entry",
        description: str = "Stochastic 과매도 반등 매수 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "k_period": 14,  # %K 기간
            "d_period": 3,   # %D 기간 (SMA of %K)
            "smooth": 3,     # %K 스무딩
            "oversold": 20,  # 과매도 기준
            "overbought": 80,  # 과매수 기준
            "min_confidence": 0.65,
            "volume_check": True,
            "trend_check": False,  # 스토캐스틱은 역추세 전략
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        self.k_period = int(self.parameters["k_period"])
        self.d_period = int(self.parameters["d_period"])
        self.smooth = int(self.parameters["smooth"])
        self.oversold = Decimal(str(self.parameters["oversold"]))
        self.overbought = Decimal(str(self.parameters["overbought"]))

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        Stochastic 지표 계산

        %K = (현재가 - N일 최저가) / (N일 최고가 - N일 최저가) * 100
        %D = %K의 M일 이동평균

        Args:
            ohlcv_data: OHLCV 데이터 리스트

        Returns:
            Dict: %K, %D 값

        Raises:
            IndicatorCalculationError: 지표 계산 실패 시
        """
        try:
            required_length = self.k_period + self.smooth + self.d_period
            if len(ohlcv_data) < required_length:
                raise IndicatorCalculationError(
                    "Stochastic 계산을 위한 데이터가 부족합니다",
                    {"required": required_length, "provided": len(ohlcv_data)}
                )

            # %K 계산
            k_values = []
            for i in range(self.k_period - 1, len(ohlcv_data)):
                period_data = ohlcv_data[i - self.k_period + 1:i + 1]

                highest_high = max(candle.high for candle in period_data)
                lowest_low = min(candle.low for candle in period_data)
                current_close = ohlcv_data[i].close

                if highest_high == lowest_low:
                    k_values.append(Decimal("50"))  # 범위가 0이면 중간값
                else:
                    k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
                    k_values.append(k)

            # %K 스무딩 (SMA)
            if self.smooth > 1:
                smoothed_k = []
                for i in range(self.smooth - 1, len(k_values)):
                    smooth_avg = sum(k_values[i - self.smooth + 1:i + 1]) / self.smooth
                    smoothed_k.append(smooth_avg)
                k_values = smoothed_k

            # %D 계산 (%K의 SMA)
            d_values = []
            for i in range(self.d_period - 1, len(k_values)):
                d = sum(k_values[i - self.d_period + 1:i + 1]) / self.d_period
                d_values.append(d)

            # 최신 값
            current_k = k_values[-1] if k_values else Decimal("50")
            current_d = d_values[-1] if d_values else Decimal("50")

            # 이전 값 (크로스 감지용)
            prev_k = k_values[-2] if len(k_values) > 1 else current_k
            prev_d = d_values[-2] if len(d_values) > 1 else current_d

            return {
                "k": current_k,
                "d": current_d,
                "prev_k": prev_k,
                "prev_d": prev_d,
                "k_line": k_values,
                "d_line": d_values,
            }

        except Exception as e:
            logger.error(f"Stochastic 계산 실패: {e}")
            raise IndicatorCalculationError(f"Stochastic 계산 실패: {str(e)}")

    def check_entry_condition(
        self,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> tuple[bool, Decimal]:
        """
        Stochastic 매수 조건 체크

        조건:
        1. 골든 크로스: %K > %D AND 이전에 %K < %D
        2. 과매도 구간: %K < oversold

        Args:
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 Stochastic 지표

        Returns:
            tuple: (매수 조건 만족 여부, 확신도)
        """
        k = indicators["k"]
        d = indicators["d"]
        prev_k = indicators["prev_k"]
        prev_d = indicators["prev_d"]

        # 1. 골든 크로스 체크
        golden_cross = (prev_k <= prev_d) and (k > d)

        # 2. 과매도 구간 체크
        in_oversold = k < self.oversold

        # 3. 과매도에서 상승 반등
        oversold_reversal = in_oversold and (k > prev_k)

        # 4. 매수 조건: (골든 크로스 AND 과매도) 또는 과매도 반등
        entry_condition = (golden_cross and in_oversold) or oversold_reversal

        if not entry_condition:
            return False, Decimal("0.5")

        # 5. 확신도 계산
        confidence = self._calculate_stochastic_confidence(
            k, d, prev_k, golden_cross, in_oversold, oversold_reversal
        )

        return True, confidence

    def _calculate_stochastic_confidence(
        self,
        k: Decimal,
        d: Decimal,
        prev_k: Decimal,
        golden_cross: bool,
        in_oversold: bool,
        oversold_reversal: bool
    ) -> Decimal:
        """
        Stochastic 확신도 계산

        Args:
            k: %K 값
            d: %D 값
            prev_k: 이전 %K 값
            golden_cross: 골든 크로스 여부
            in_oversold: 과매도 구간 여부
            oversold_reversal: 과매도 반등 여부

        Returns:
            Decimal: 확신도 (0-1)
        """
        confidence = Decimal("0.5")

        # 골든 크로스 시 확신도 증가
        if golden_cross:
            confidence += Decimal("0.25")

        # 과매도 구간에서 확신도 증가
        if in_oversold:
            # 과매도 정도에 따라 추가 확신도 (20 미만일수록 높음)
            oversold_strength = (self.oversold - k) / self.oversold
            confidence += oversold_strength * Decimal("0.2")

        # 과매도 반등 시 확신도 증가
        if oversold_reversal:
            # 상승 강도에 따라 추가 확신도
            reversal_strength = (k - prev_k) / Decimal("10")  # 10 상승 시 0.1
            confidence += min(reversal_strength, Decimal("0.15"))

        # %K와 %D 차이에 따른 확신도
        if k > d:
            diff = min((k - d) / Decimal("10"), Decimal("0.1"))
            confidence += diff

        # 0-1 범위로 제한
        return max(Decimal("0"), min(Decimal("1"), confidence))

    def validate_parameters(self) -> bool:
        """
        Stochastic 파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            StrategyError: 파라미터가 유효하지 않은 경우
        """
        errors = []

        if self.k_period <= 0:
            errors.append("k_period는 0보다 커야 합니다")

        if self.d_period <= 0:
            errors.append("d_period는 0보다 커야 합니다")

        if self.smooth <= 0:
            errors.append("smooth는 0보다 커야 합니다")

        if not (0 < self.oversold < 50):
            errors.append("oversold는 0과 50 사이여야 합니다")

        if not (50 < self.overbought < 100):
            errors.append("overbought는 50과 100 사이여야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "Stochastic 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """
        필요한 최소 데이터 개수

        Returns:
            int: k_period + smooth + d_period + 10
        """
        return self.k_period + self.smooth + self.d_period + 10

    def __repr__(self) -> str:
        return (
            f"<StochasticEntryStrategy(name={self.name}, "
            f"k={self.k_period}, d={self.d_period}, oversold={self.oversold})>"
        )


if __name__ == "__main__":
    print("=== Stochastic 매수 전략 테스트 ===")

    # 테스트 데이터 생성 (하락 후 반등)
    from datetime import timedelta
    import random

    test_data = []
    base_price = Decimal("50000000")
    base_time = datetime.now()

    for i in range(100):
        # 하락 후 반등 시뮬레이션
        if i < 50:
            # 하락
            price = base_price - Decimal(str(i * 20000))
        else:
            # 반등
            price = base_price - Decimal(str((100 - i) * 20000))

        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=price - Decimal("50000"),
            high=price + Decimal("100000"),
            low=price - Decimal("100000"),
            close=price,
            volume=Decimal("100")
        )
        test_data.append(candle)

    # Stochastic 전략 생성
    strategy = StochasticEntryStrategy(
        id=1,
        parameters={
            "k_period": 14,
            "d_period": 3,
            "smooth": 3,
            "oversold": 20,
            "min_confidence": 0.6,
        }
    )

    # 전략 활성화
    strategy.activate()

    # 시그널 생성
    signal_data = strategy.analyze("KRW-BTC", test_data)

    print(f"\n시그널: {signal_data.signal.value.upper()}")
    print(f"확신도: {signal_data.confidence:.2%}")
    print(f"가격: {signal_data.price:,.0f} KRW")
    print(f"\n지표:")
    print(f"  %K: {signal_data.indicators['k']:.2f}")
    print(f"  %D: {signal_data.indicators['d']:.2f}")
