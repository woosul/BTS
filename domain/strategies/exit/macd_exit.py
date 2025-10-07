"""
BTS MACD 매도 전략

MACD 데드 크로스 기반 매도 전략
"""
from typing import Dict, List
from decimal import Decimal
import pandas as pd

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_macd

logger = get_logger(__name__)


class MACDExitStrategy(BaseExitStrategy):
    """
    MACD 매도 전략 (Moving Average Convergence Divergence)

    매도 조건:
    - MACD 선이 시그널 선을 하향 돌파 (데드 크로스)
    - 히스토그램이 양수에서 음수로 전환
    - MACD 선이 0선 아래로 하락

    파라미터:
    - fast_period: 단기 EMA 기간 (기본 12)
    - slow_period: 장기 EMA 기간 (기본 26)
    - signal_period: 시그널 EMA 기간 (기본 9)
    - cross_mode: 크로스 모드 (signal/zero/both, 기본 signal)
      - signal: 시그널 선 데드 크로스
      - zero: 0선 하향 돌파
      - both: 두 조건 모두
    - min_profit_pct: 최소 익절률 (기본 2%)
    - max_loss_pct: 최대 손절률 (기본 -5%)
    """

    def __init__(
        self,
        id: int,
        name: str = "MACD Exit Strategy",
        description: str = "MACD 데드 크로스 기반 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "cross_mode": "signal",  # signal, zero, both
            "min_confidence": 0.7,
            "min_profit_pct": 2,
            "max_loss_pct": -5,
            "check_volume": False,
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(
            id=id,
            name=name,
            description=description,
            timeframe=timeframe,
            parameters=default_params
        )

    def validate_parameters(self) -> bool:
        """파라미터 검증"""
        fast_period = self.get_parameter("fast_period")
        slow_period = self.get_parameter("slow_period")
        signal_period = self.get_parameter("signal_period")
        cross_mode = self.get_parameter("cross_mode")

        if not isinstance(fast_period, int) or fast_period < 2:
            raise ValueError("단기 EMA 기간은 2 이상의 정수여야 합니다")

        if not isinstance(slow_period, int) or slow_period <= fast_period:
            raise ValueError("장기 EMA 기간은 단기보다 커야 합니다")

        if not isinstance(signal_period, int) or signal_period < 2:
            raise ValueError("시그널 기간은 2 이상의 정수여야 합니다")

        if cross_mode not in ["signal", "zero", "both"]:
            raise ValueError("크로스 모드는 signal, zero, both 중 하나여야 합니다")

        return True

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """MACD 지표 계산"""
        try:
            df = pd.DataFrame([
                {
                    "timestamp": candle.timestamp,
                    "close": float(candle.close),
                }
                for candle in ohlcv_data
            ])

            fast_period = self.get_parameter("fast_period")
            slow_period = self.get_parameter("slow_period")
            signal_period = self.get_parameter("signal_period")

            # MACD 계산
            macd_line, signal_line, histogram = calculate_macd(
                df["close"], fast_period, slow_period, signal_period
            )

            df["macd"] = macd_line
            df["signal"] = signal_line
            df["histogram"] = histogram

            # 최신 및 이전 값 추출
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            return {
                "macd": Decimal(str(latest["macd"])),
                "signal": Decimal(str(latest["signal"])),
                "histogram": Decimal(str(latest["histogram"])),
                "macd_prev": Decimal(str(previous["macd"])),
                "signal_prev": Decimal(str(previous["signal"])),
                "histogram_prev": Decimal(str(previous["histogram"])),
                "price": Decimal(str(latest["close"])),
            }

        except Exception as e:
            logger.error(f"MACD 지표 계산 실패: {e}")
            raise IndicatorCalculationError(f"MACD 계산 실패: {str(e)}")

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        MACD 매도 조건 체크

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        macd = indicators["macd"]
        signal = indicators["signal"]
        histogram = indicators["histogram"]
        macd_prev = indicators["macd_prev"]
        signal_prev = indicators["signal_prev"]
        histogram_prev = indicators["histogram_prev"]

        cross_mode = self.get_parameter("cross_mode")

        # 1. 시그널 선 데드 크로스 확인
        signal_dead_cross = (macd_prev > signal_prev) and (macd <= signal)

        # 2. 0선 하향 돌파 확인
        zero_cross_down = (macd_prev > 0) and (macd <= 0)

        # 3. 히스토그램 음전환 확인
        histogram_negative = (histogram_prev > 0) and (histogram <= 0)

        # 4. 크로스 모드에 따른 조건 체크
        if cross_mode == "signal":
            # 시그널 데드 크로스만
            if not signal_dead_cross:
                return False, Decimal("0"), "MACD 데드 크로스 아님"
            base_confidence = Decimal("0.75")

        elif cross_mode == "zero":
            # 0선 하향 돌파만
            if not zero_cross_down:
                return False, Decimal("0"), "MACD 0선 하향 돌파 아님"
            base_confidence = Decimal("0.8")

        else:  # both
            # 두 조건 모두 필요
            if not (signal_dead_cross or zero_cross_down):
                return False, Decimal("0"), "MACD 매도 조건 미충족"

            # 둘 다 만족하면 확신도 증가
            if signal_dead_cross and zero_cross_down:
                base_confidence = Decimal("0.9")
            else:
                base_confidence = Decimal("0.75")

        # 5. 히스토그램 음전환 시 확신도 증가
        if histogram_negative:
            base_confidence = base_confidence * Decimal("1.1")

        # 6. MACD 선의 위치에 따라 확신도 조정
        if macd < 0:
            # MACD가 0 아래에 있으면 하락 추세 강화
            base_confidence = base_confidence * Decimal("1.05")

        # 7. 손익률에 따라 확신도 조정
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        if profit_loss_pct > 5:
            # 큰 수익 중이면 확신도 증가 (이익 실현)
            base_confidence = base_confidence * Decimal("1.15")
        elif profit_loss_pct > 0:
            base_confidence = base_confidence * Decimal("1.05")
        elif profit_loss_pct < -5:
            # 큰 손실 중이면 확신도 증가 (손절)
            base_confidence = base_confidence * Decimal("1.2")

        # 확신도 범위 조정
        confidence = min(Decimal("1"), base_confidence)

        # 이유 문자열 생성
        conditions = []
        if signal_dead_cross:
            conditions.append("데드 크로스")
        if zero_cross_down:
            conditions.append("0선 하향 돌파")
        if histogram_negative:
            conditions.append("히스토그램 음전환")

        reason = (
            f"MACD {', '.join(conditions)} "
            f"(MACD={macd:.2f}, Signal={signal:.2f}), "
            f"손익률 {profit_loss_pct:.2f}%"
        )

        logger.info(
            f"MACD 매도 조건 충족: {', '.join(conditions)}, "
            f"MACD={macd:.2f}, Signal={signal:.2f}, "
            f"손익률={profit_loss_pct:.2f}%, 확신도={confidence:.2%}"
        )

        return True, confidence, reason

    def get_minimum_data_points(self) -> int:
        """최소 데이터 개수"""
        slow_period = self.get_parameter("slow_period")
        signal_period = self.get_parameter("signal_period")
        return max(slow_period + signal_period + 20, 50)

    def __repr__(self) -> str:
        return (
            f"<MACDExitStrategy(name={self.name}, "
            f"MACD({self.get_parameter('fast_period')}/"
            f"{self.get_parameter('slow_period')}/"
            f"{self.get_parameter('signal_period')}), "
            f"mode={self.get_parameter('cross_mode')})>"
        )
