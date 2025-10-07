"""
BTS 볼린저 밴드 매수 전략

볼린저 밴드 하단 터치/돌파 기반 매수 전략
"""
from typing import Dict, List
from decimal import Decimal
import pandas as pd

from domain.strategies.entry.base_entry import BaseEntryStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_bollinger_bands

logger = get_logger(__name__)


class BollingerEntryStrategy(BaseEntryStrategy):
    """
    볼린저 밴드 매수 전략

    매수 조건:
    - 가격이 볼린저 밴드 하단을 터치하거나 돌파
    - 하단으로부터의 반등 시그널 포착

    파라미터:
    - period: 볼린저 밴드 기간 (기본 20)
    - std_dev: 표준편차 배수 (기본 2.0)
    - signal_mode: 시그널 모드 (touch/breakout, 기본 touch)
      - touch: 하단 터치 시 매수
      - breakout: 하단 돌파 후 재진입 시 매수
    - touch_threshold: 하단 터치 기준 (기본 1.02, 하단의 102% 이내)
    """

    def __init__(
        self,
        id: int,
        name: str = "Bollinger Entry Strategy",
        description: str = "볼린저 밴드 기반 매수 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "period": 20,
            "std_dev": 2.0,
            "signal_mode": "touch",  # touch or breakout
            "touch_threshold": 1.02,  # 하단의 102% 이내
            "min_confidence": 0.6,
            "volume_check": True,
            "trend_check": False,  # 볼린저 밴드는 역추세 전략
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
                    "low": float(candle.low),
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
                "low": Decimal(str(latest["low"])),
                "price_prev": Decimal(str(previous["close"])),
            }

        except Exception as e:
            logger.error(f"볼린저 밴드 지표 계산 실패: {e}")
            raise IndicatorCalculationError(f"볼린저 밴드 계산 실패: {str(e)}")

    def check_entry_condition(
        self,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> tuple[bool, Decimal]:
        """
        볼린저 밴드 매수 조건 체크

        Returns:
            tuple: (매수 조건 만족 여부, 기본 확신도)
        """
        bb_lower = indicators["bb_lower"]
        bb_middle = indicators["bb_middle"]
        bb_width = indicators["bb_width"]
        price = indicators["price"]
        low = indicators["low"]
        price_prev = indicators["price_prev"]
        signal_mode = self.get_parameter("signal_mode")
        touch_threshold = Decimal(str(self.get_parameter("touch_threshold")))

        # 1. 시그널 모드에 따른 조건 체크
        if signal_mode == "touch":
            # 하단 터치: 현재가 또는 저가가 하단 근처 (threshold 이내)
            touch_price = bb_lower * touch_threshold
            is_touch = low <= touch_price or price <= touch_price

            if not is_touch:
                return False, Decimal("0")

            # 하단에 가까울수록 확신도 증가
            distance_to_lower = abs(price - bb_lower) / bb_lower
            base_confidence = Decimal("0.7") - min(distance_to_lower * 10, Decimal("0.2"))

        else:  # breakout
            # 하단 돌파 후 재진입: 이전에 하단 아래였다가 현재 위로 올라옴
            prev_below = price_prev < bb_lower
            now_above = price >= bb_lower

            if not (prev_below and now_above):
                return False, Decimal("0")

            # 재진입 강도에 따라 확신도 계산
            reentry_strength = (price - bb_lower) / (bb_middle - bb_lower)
            base_confidence = Decimal("0.8") - min(reentry_strength * Decimal("0.3"), Decimal("0.2"))

        # 2. 밴드 폭이 넓을수록 (변동성이 클수록) 확신도 증가
        # 밴드 폭이 3% 이상이면 확신도 증가
        if bb_width > Decimal("0.03"):
            base_confidence = base_confidence * Decimal("1.1")

        # 3. 가격이 중심선보다 아래에 있으면 확신도 증가
        if price < bb_middle:
            base_confidence = base_confidence * Decimal("1.05")

        # 확신도 범위 조정 (0-1)
        base_confidence = min(Decimal("1"), base_confidence)

        logger.info(
            f"볼린저 밴드 매수 조건 충족: 가격={price:.2f}, "
            f"하단={bb_lower:.2f}, 확신도={base_confidence:.2%}"
        )

        return True, base_confidence

    def get_minimum_data_points(self) -> int:
        """최소 데이터 개수"""
        period = self.get_parameter("period")
        return max(period + 20, 40)

    def __repr__(self) -> str:
        return (
            f"<BollingerEntryStrategy(name={self.name}, "
            f"period={self.get_parameter('period')}, "
            f"std_dev={self.get_parameter('std_dev')})>"
        )
