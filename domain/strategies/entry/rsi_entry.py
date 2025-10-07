"""
BTS RSI 매수 전략

RSI 지표 기반 매수 전략
"""
from typing import Dict, List
from decimal import Decimal
import pandas as pd

from domain.strategies.entry.base_entry import BaseEntryStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_rsi

logger = get_logger(__name__)


class RSIEntryStrategy(BaseEntryStrategy):
    """
    RSI 매수 전략

    매수 조건:
    - RSI < 과매도 기준 (기본 30)
    - RSI가 상승 전환 중일 때 더 높은 확신도

    파라미터:
    - rsi_period: RSI 기간 (기본 14)
    - oversold: 과매도 기준 (기본 30)
    - extreme_oversold: 극단적 과매도 기준 (기본 20, 확신도 증가)
    """

    def __init__(
        self,
        id: int,
        name: str = "RSI Entry Strategy",
        description: str = "RSI 지표 기반 매수 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "rsi_period": 14,
            "oversold": 30,
            "extreme_oversold": 20,
            "min_confidence": 0.6,
            "volume_check": True,
            "trend_check": False,  # RSI 전략은 역추세 매매이므로 추세 체크 비활성화
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
        rsi_period = self.get_parameter("rsi_period")
        oversold = self.get_parameter("oversold")
        extreme_oversold = self.get_parameter("extreme_oversold")

        if not isinstance(rsi_period, int) or rsi_period < 2:
            raise ValueError("RSI 기간은 2 이상의 정수여야 합니다")

        if not (0 < extreme_oversold < oversold < 100):
            raise ValueError("0 < extreme_oversold < oversold < 100 범위여야 합니다")

        return True

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """RSI 지표 계산"""
        try:
            df = pd.DataFrame([
                {
                    "timestamp": candle.timestamp,
                    "close": float(candle.close),
                }
                for candle in ohlcv_data
            ])

            # RSI 계산
            rsi_period = self.get_parameter("rsi_period")
            df["rsi"] = calculate_rsi(df["close"], rsi_period)

            # 최신 및 이전 값 추출
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            return {
                "rsi": Decimal(str(latest["rsi"])),
                "rsi_previous": Decimal(str(previous["rsi"])),
            }

        except Exception as e:
            logger.error(f"RSI 지표 계산 실패: {e}")
            raise IndicatorCalculationError(f"RSI 계산 실패: {str(e)}")

    def check_entry_condition(
        self,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> tuple[bool, Decimal]:
        """
        RSI 매수 조건 체크

        Returns:
            tuple: (매수 조건 만족 여부, 기본 확신도)
        """
        rsi = indicators["rsi"]
        rsi_previous = indicators["rsi_previous"]
        oversold = Decimal(str(self.get_parameter("oversold")))
        extreme_oversold = Decimal(str(self.get_parameter("extreme_oversold")))

        # 1. 과매도 구간이 아니면 매수 안 함
        if rsi >= oversold:
            return False, Decimal("0")

        # 2. 기본 확신도 계산 (RSI가 낮을수록 높음)
        base_confidence = (oversold - rsi) / oversold

        # 3. 극단적 과매도 구간이면 확신도 증가
        if rsi < extreme_oversold:
            base_confidence = base_confidence * Decimal("1.2")

        # 4. RSI 상승 전환 중이면 확신도 증가
        if rsi > rsi_previous:
            base_confidence = base_confidence * Decimal("1.1")

        # 확신도 범위 조정 (0-1)
        base_confidence = min(Decimal("1"), base_confidence)

        logger.info(
            f"RSI 매수 조건 충족: RSI={rsi:.2f}, "
            f"확신도={base_confidence:.2%}"
        )

        return True, base_confidence

    def get_minimum_data_points(self) -> int:
        """최소 데이터 개수"""
        rsi_period = self.get_parameter("rsi_period")
        return max(rsi_period * 2, 30)

    def __repr__(self) -> str:
        return (
            f"<RSIEntryStrategy(name={self.name}, "
            f"period={self.get_parameter('rsi_period')}, "
            f"oversold={self.get_parameter('oversold')})>"
        )
