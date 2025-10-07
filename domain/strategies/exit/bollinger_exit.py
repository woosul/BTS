"""
BTS 볼린저 밴드 매도 전략

볼린저 밴드 상단 터치/돌파 기반 매도 전략
"""
from typing import Dict, List
from decimal import Decimal
import pandas as pd

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_bollinger_bands

logger = get_logger(__name__)


class BollingerExitStrategy(BaseExitStrategy):
    """
    볼린저 밴드 매도 전략

    매도 조건:
    - 가격이 볼린저 밴드 상단을 터치하거나 돌파
    - 상단으로부터의 반락 시그널 포착

    파라미터:
    - period: 볼린저 밴드 기간 (기본 20)
    - std_dev: 표준편차 배수 (기본 2.0)
    - signal_mode: 시그널 모드 (touch/breakout, 기본 touch)
      - touch: 상단 터치 시 매도
      - breakout: 상단 돌파 후 재진입 시 매도
    - touch_threshold: 상단 터치 기준 (기본 0.98, 상단의 98% 이상)
    - min_profit_pct: 최소 익절률 (기본 2%)
    - max_loss_pct: 최대 손절률 (기본 -5%)
    """

    def __init__(
        self,
        id: int,
        name: str = "Bollinger Exit Strategy",
        description: str = "볼린저 밴드 기반 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "period": 20,
            "std_dev": 2.0,
            "signal_mode": "touch",  # touch or breakout
            "touch_threshold": 0.98,  # 상단의 98% 이상
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
        period = self.get_parameter("period")
        std_dev = self.get_parameter("std_dev")
        signal_mode = self.get_parameter("signal_mode")

        if not isinstance(period, int) or period < 2:
            raise ValueError("볼린저 밴드 기간은 2 이상의 정수여야 합니다")

        if std_dev <= 0:
            raise ValueError("표준편차 배수는 0보다 커야 합니다")

        if signal_mode not in ["touch", "breakout"]:
            raise ValueError("시그널 모드는 touch 또는 breakout이어야 합니다")

        return True

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """볼린저 밴드 지표 계산"""
        try:
            df = pd.DataFrame([
                {
                    "timestamp": candle.timestamp,
                    "close": float(candle.close),
                    "high": float(candle.high),
                }
                for candle in ohlcv_data
            ])

            period = self.get_parameter("period")
            std_dev = self.get_parameter("std_dev")

            # 볼린저 밴드 계산
            df["bb_upper"], df["bb_middle"], df["bb_lower"] = calculate_bollinger_bands(
                df["close"], period, std_dev
            )

            # 밴드 폭 계산 (변동성 지표)
            df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

            # 최신 값 추출
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            return {
                "bb_upper": Decimal(str(latest["bb_upper"])),
                "bb_middle": Decimal(str(latest["bb_middle"])),
                "bb_lower": Decimal(str(latest["bb_lower"])),
                "bb_width": Decimal(str(latest["bb_width"])),
                "price": Decimal(str(latest["close"])),
                "high": Decimal(str(latest["high"])),
                "price_prev": Decimal(str(previous["close"])),
            }

        except Exception as e:
            logger.error(f"볼린저 밴드 지표 계산 실패: {e}")
            raise IndicatorCalculationError(f"볼린저 밴드 계산 실패: {str(e)}")

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        볼린저 밴드 매도 조건 체크

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        bb_upper = indicators["bb_upper"]
        bb_middle = indicators["bb_middle"]
        bb_width = indicators["bb_width"]
        price = indicators["price"]
        high = indicators["high"]
        price_prev = indicators["price_prev"]
        signal_mode = self.get_parameter("signal_mode")
        touch_threshold = Decimal(str(self.get_parameter("touch_threshold")))

        # 1. 시그널 모드에 따른 조건 체크
        if signal_mode == "touch":
            # 상단 터치: 현재가 또는 고가가 상단 근처 (threshold 이상)
            touch_price = bb_upper * touch_threshold
            is_touch = high >= touch_price or price >= touch_price

            if not is_touch:
                return False, Decimal("0"), "볼린저 밴드 상단 미터치"

            # 상단에 가까울수록 확신도 증가
            distance_to_upper = abs(bb_upper - price) / bb_upper
            confidence = Decimal("0.75") + min((Decimal("1") - distance_to_upper) * Decimal("0.2"), Decimal("0.2"))

        else:  # breakout
            # 상단 돌파 후 재진입: 이전에 상단 위였다가 현재 아래로 내려옴
            prev_above = price_prev > bb_upper
            now_below = price <= bb_upper

            if not (prev_above and now_below):
                return False, Decimal("0"), "볼린저 밴드 상단 재진입 아님"

            # 재진입 강도에 따라 확신도 계산
            reentry_strength = (bb_upper - price) / (bb_upper - bb_middle)
            confidence = Decimal("0.85") + min(reentry_strength * Decimal("0.15"), Decimal("0.15"))

        # 2. 밴드 폭이 넓을수록 (변동성이 클수록) 확신도 증가
        # 밴드 폭이 3% 이상이면 확신도 증가
        if bb_width > Decimal("0.03"):
            confidence = confidence * Decimal("1.1")

        # 3. 가격이 중심선보다 위에 있으면 확신도 증가
        if price > bb_middle:
            confidence = confidence * Decimal("1.05")

        # 4. 손익률에 따라 확신도 조정
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        # 수익이 클수록 확신도 증가
        if profit_loss_pct > 10:
            confidence = confidence * Decimal("1.2")
        elif profit_loss_pct > 5:
            confidence = confidence * Decimal("1.1")
        elif profit_loss_pct > 0:
            confidence = confidence * Decimal("1.05")
        # 손실 중이면 확신도 감소
        elif profit_loss_pct < -3:
            confidence = confidence * Decimal("0.9")

        # 확신도 범위 조정 (0-1)
        confidence = min(Decimal("1"), confidence)

        reason = (
            f"볼린저 밴드 상단 터치 (가격={price:.2f}, 상단={bb_upper:.2f}), "
            f"손익률 {profit_loss_pct:.2f}%"
        )

        logger.info(
            f"볼린저 밴드 매도 조건 충족: 가격={price:.2f}, "
            f"상단={bb_upper:.2f}, 손익률={profit_loss_pct:.2f}%, "
            f"확신도={confidence:.2%}"
        )

        return True, confidence, reason

    def get_minimum_data_points(self) -> int:
        """최소 데이터 개수"""
        period = self.get_parameter("period")
        return max(period + 20, 40)

    def __repr__(self) -> str:
        return (
            f"<BollingerExitStrategy(name={self.name}, "
            f"period={self.get_parameter('period')}, "
            f"std_dev={self.get_parameter('std_dev')})>"
        )
