"""
BTS RSI 매도 전략

RSI 지표 기반 매도 전략
"""
from typing import Dict, List
from decimal import Decimal
import pandas as pd

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_rsi

logger = get_logger(__name__)


class RSIExitStrategy(BaseExitStrategy):
    """
    RSI 매도 전략

    매도 조건:
    - RSI > 과매수 기준 (기본 70)
    - RSI가 하락 전환 중일 때 더 높은 확신도

    파라미터:
    - rsi_period: RSI 기간 (기본 14)
    - overbought: 과매수 기준 (기본 70)
    - extreme_overbought: 극단적 과매수 기준 (기본 80, 확신도 증가)
    - min_profit_pct: 최소 익절률 (기본 2%)
    - max_loss_pct: 최대 손절률 (기본 -5%)
    """

    def __init__(
        self,
        id: int,
        name: str = "RSI Exit Strategy",
        description: str = "RSI 지표 기반 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "rsi_period": 14,
            "overbought": 70,
            "extreme_overbought": 80,
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
        rsi_period = self.get_parameter("rsi_period")
        overbought = self.get_parameter("overbought")
        extreme_overbought = self.get_parameter("extreme_overbought")

        if not isinstance(rsi_period, int) or rsi_period < 2:
            raise ValueError("RSI 기간은 2 이상의 정수여야 합니다")

        if not (0 < overbought < extreme_overbought < 100):
            raise ValueError("0 < overbought < extreme_overbought < 100 범위여야 합니다")

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

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        RSI 매도 조건 체크

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        rsi = indicators["rsi"]
        rsi_previous = indicators["rsi_previous"]
        overbought = Decimal(str(self.get_parameter("overbought")))
        extreme_overbought = Decimal(str(self.get_parameter("extreme_overbought")))

        # 1. 과매수 구간이 아니면 매도 안 함
        if rsi <= overbought:
            return False, Decimal("0"), "RSI 과매수 아님"

        # 2. 기본 확신도 계산 (RSI가 높을수록 높음)
        confidence = (rsi - overbought) / (Decimal("100") - overbought)

        # 3. 극단적 과매수 구간이면 확신도 증가
        if rsi >= extreme_overbought:
            confidence = confidence * Decimal("1.2")

        # 4. RSI 하락 전환 중이면 확신도 증가
        if rsi < rsi_previous:
            confidence = confidence * Decimal("1.15")

        # 5. 손익률에 따라 확신도 조정
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        # 수익 중이면 확신도 증가
        if profit_loss_pct > 0:
            confidence = confidence * Decimal("1.1")
        # 손실 중이면 확신도 감소 (손실 중 매도는 신중하게)
        elif profit_loss_pct < -2:
            confidence = confidence * Decimal("0.9")

        # 확신도 범위 조정 (0-1)
        confidence = min(Decimal("1"), confidence)

        reason = f"RSI 과매수 ({rsi:.2f}), 손익률 {profit_loss_pct:.2f}%"

        logger.info(
            f"RSI 매도 조건 충족: RSI={rsi:.2f}, "
            f"손익률={profit_loss_pct:.2f}%, 확신도={confidence:.2%}"
        )

        return True, confidence, reason

    def get_minimum_data_points(self) -> int:
        """최소 데이터 개수"""
        rsi_period = self.get_parameter("rsi_period")
        return max(rsi_period * 2, 30)

    def __repr__(self) -> str:
        return (
            f"<RSIExitStrategy(name={self.name}, "
            f"period={self.get_parameter('rsi_period')}, "
            f"overbought={self.get_parameter('overbought')})>"
        )
