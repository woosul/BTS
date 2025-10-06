"""
BTS MACD 매수 전략

MACD(Moving Average Convergence Divergence) 지표 기반 매수 전략
- MACD 골든 크로스: MACD 선이 시그널 선을 상향 돌파
- 히스토그램 반전: 음수에서 양수로 전환
"""
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from domain.strategies.entry.base_entry import BaseEntryStrategy
from core.enums import StrategySignal, TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_ema

logger = get_logger(__name__)


class MACDEntryStrategy(BaseEntryStrategy):
    """
    MACD 매수 전략

    골든 크로스 및 히스토그램 반전 시그널 포착
    """

    def __init__(
        self,
        id: int,
        name: str = "MACD Entry",
        description: str = "MACD 골든 크로스 매수 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "histogram_threshold": 0,  # 히스토그램이 이 값보다 클 때 매수
            "min_confidence": 0.65,
            "volume_check": True,
            "trend_check": True,
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        self.fast_period = int(self.parameters["fast_period"])
        self.slow_period = int(self.parameters["slow_period"])
        self.signal_period = int(self.parameters["signal_period"])
        self.histogram_threshold = Decimal(str(self.parameters["histogram_threshold"]))

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        MACD 지표 계산

        Args:
            ohlcv_data: OHLCV 데이터 리스트

        Returns:
            Dict: MACD, Signal, Histogram 값

        Raises:
            IndicatorCalculationError: 지표 계산 실패 시
        """
        try:
            if len(ohlcv_data) < self.slow_period + self.signal_period:
                raise IndicatorCalculationError(
                    "MACD 계산을 위한 데이터가 부족합니다",
                    {"required": self.slow_period + self.signal_period, "provided": len(ohlcv_data)}
                )

            # 종가 추출
            closes = [float(candle.close) for candle in ohlcv_data]

            # 1. Fast EMA (12일)
            fast_ema = calculate_ema(closes, self.fast_period)

            # 2. Slow EMA (26일)
            slow_ema = calculate_ema(closes, self.slow_period)

            # 3. MACD Line = Fast EMA - Slow EMA
            macd_line = [fast - slow for fast, slow in zip(fast_ema, slow_ema)]

            # 4. Signal Line = MACD의 9일 EMA
            signal_line = calculate_ema(macd_line, self.signal_period)

            # 5. Histogram = MACD - Signal
            histogram = [macd - signal for macd, signal in zip(macd_line, signal_line)]

            # 최신 값들
            current_macd = Decimal(str(macd_line[-1]))
            current_signal = Decimal(str(signal_line[-1]))
            current_histogram = Decimal(str(histogram[-1]))

            # 이전 값들 (크로스 감지용)
            prev_macd = Decimal(str(macd_line[-2])) if len(macd_line) > 1 else current_macd
            prev_signal = Decimal(str(signal_line[-2])) if len(signal_line) > 1 else current_signal
            prev_histogram = Decimal(str(histogram[-2])) if len(histogram) > 1 else current_histogram

            return {
                "macd": current_macd,
                "signal": current_signal,
                "histogram": current_histogram,
                "prev_macd": prev_macd,
                "prev_signal": prev_signal,
                "prev_histogram": prev_histogram,
                "macd_line": [Decimal(str(v)) for v in macd_line],
                "signal_line": [Decimal(str(v)) for v in signal_line],
                "histogram_line": [Decimal(str(v)) for v in histogram],
            }

        except Exception as e:
            logger.error(f"MACD 계산 실패: {e}")
            raise IndicatorCalculationError(f"MACD 계산 실패: {str(e)}")

    def check_entry_condition(
        self,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> tuple[bool, Decimal]:
        """
        MACD 매수 조건 체크

        조건:
        1. 골든 크로스: MACD > Signal AND 이전에 MACD < Signal
        2. 히스토그램 양수 전환: Histogram > threshold AND 이전 Histogram < threshold

        Args:
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 MACD 지표

        Returns:
            tuple: (매수 조건 만족 여부, 확신도)
        """
        macd = indicators["macd"]
        signal = indicators["signal"]
        histogram = indicators["histogram"]
        prev_macd = indicators["prev_macd"]
        prev_signal = indicators["prev_signal"]
        prev_histogram = indicators["prev_histogram"]

        # 1. 골든 크로스 체크
        golden_cross = (prev_macd <= prev_signal) and (macd > signal)

        # 2. 히스토그램 양수 전환
        histogram_positive = (
            prev_histogram <= self.histogram_threshold and
            histogram > self.histogram_threshold
        )

        # 3. 매수 조건: 골든 크로스 또는 히스토그램 양수 전환
        entry_condition = golden_cross or histogram_positive

        if not entry_condition:
            return False, Decimal("0.5")

        # 4. 확신도 계산
        confidence = self._calculate_macd_confidence(
            macd, signal, histogram, golden_cross, histogram_positive
        )

        return True, confidence

    def _calculate_macd_confidence(
        self,
        macd: Decimal,
        signal: Decimal,
        histogram: Decimal,
        golden_cross: bool,
        histogram_positive: bool
    ) -> Decimal:
        """
        MACD 확신도 계산

        Args:
            macd: MACD 값
            signal: Signal 값
            histogram: Histogram 값
            golden_cross: 골든 크로스 여부
            histogram_positive: 히스토그램 양수 전환 여부

        Returns:
            Decimal: 확신도 (0-1)
        """
        confidence = Decimal("0.5")

        # 골든 크로스 시 기본 확신도 증가
        if golden_cross:
            confidence += Decimal("0.2")

        # 히스토그램 양수 전환 시 추가 확신도
        if histogram_positive:
            confidence += Decimal("0.15")

        # 히스토그램이 클수록 확신도 증가
        histogram_strength = min(abs(histogram) / 1000, Decimal("0.2"))
        confidence += histogram_strength

        # MACD와 Signal 차이가 클수록 확신도 증가
        diff = abs(macd - signal)
        diff_strength = min(diff / 1000, Decimal("0.15"))
        confidence += diff_strength

        # 0-1 범위로 제한
        return max(Decimal("0"), min(Decimal("1"), confidence))

    def validate_parameters(self) -> bool:
        """
        MACD 파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            StrategyError: 파라미터가 유효하지 않은 경우
        """
        errors = []

        if self.fast_period <= 0:
            errors.append("fast_period는 0보다 커야 합니다")

        if self.slow_period <= 0:
            errors.append("slow_period는 0보다 커야 합니다")

        if self.signal_period <= 0:
            errors.append("signal_period는 0보다 커야 합니다")

        if self.fast_period >= self.slow_period:
            errors.append("fast_period는 slow_period보다 작아야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "MACD 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """
        필요한 최소 데이터 개수

        Returns:
            int: slow_period + signal_period + 10
        """
        return self.slow_period + self.signal_period + 10

    def __repr__(self) -> str:
        return (
            f"<MACDEntryStrategy(name={self.name}, "
            f"fast={self.fast_period}, slow={self.slow_period}, signal={self.signal_period})>"
        )


if __name__ == "__main__":
    print("=== MACD 매수 전략 테스트 ===")

    # 테스트 데이터 생성
    from datetime import timedelta

    test_data = []
    base_price = Decimal("50000000")  # 5천만원
    base_time = datetime.now()

    for i in range(100):
        # 상승 추세 시뮬레이션
        price_change = Decimal(str(i * 10000))
        close_price = base_price + price_change

        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=close_price - Decimal("50000"),
            high=close_price + Decimal("100000"),
            low=close_price - Decimal("100000"),
            close=close_price,
            volume=Decimal("100")
        )
        test_data.append(candle)

    # MACD 전략 생성
    strategy = MACDEntryStrategy(
        id=1,
        parameters={
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
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
    print(f"  MACD: {signal_data.indicators['macd']:.2f}")
    print(f"  Signal: {signal_data.indicators['signal']:.2f}")
    print(f"  Histogram: {signal_data.indicators['histogram']:.2f}")
