"""
BTS 스토캐스틱 매도 전략

스토캐스틱 과매수 구간 기반 매도 전략
"""
from typing import Dict, List
from decimal import Decimal
import pandas as pd

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_stochastic

logger = get_logger(__name__)


class StochasticExitStrategy(BaseExitStrategy):
    """
    스토캐스틱 매도 전략 (Stochastic Oscillator)

    매도 조건:
    - %K가 과매수 구간(기본 80) 이상
    - %K가 %D를 하향 돌파 (데드 크로스)
    - 과매수 구간에서 하락 반전 시그널

    파라미터:
    - k_period: %K 기간 (기본 14)
    - d_period: %D 기간 (기본 3)
    - smooth: 평활 기간 (기본 3)
    - overbought: 과매수 기준 (기본 80)
    - extreme_overbought: 극단적 과매수 기준 (기본 90, 확신도 증가)
    - cross_required: %K/%D 데드 크로스 필수 여부 (기본 False)
    - min_profit_pct: 최소 익절률 (기본 2%)
    - max_loss_pct: 최대 손절률 (기본 -5%)
    """

    def __init__(
        self,
        id: int,
        name: str = "Stochastic Exit Strategy",
        description: str = "스토캐스틱 과매수 기반 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "k_period": 14,
            "d_period": 3,
            "smooth": 3,
            "overbought": 80,
            "extreme_overbought": 90,
            "cross_required": False,  # 데드 크로스 필수 여부
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
        k_period = self.get_parameter("k_period")
        d_period = self.get_parameter("d_period")
        smooth = self.get_parameter("smooth")
        overbought = self.get_parameter("overbought")
        extreme_overbought = self.get_parameter("extreme_overbought")

        if not isinstance(k_period, int) or k_period < 2:
            raise ValueError("%K 기간은 2 이상의 정수여야 합니다")

        if not isinstance(d_period, int) or d_period < 1:
            raise ValueError("%D 기간은 1 이상의 정수여야 합니다")

        if not isinstance(smooth, int) or smooth < 1:
            raise ValueError("평활 기간은 1 이상의 정수여야 합니다")

        if not (0 < overbought < extreme_overbought <= 100):
            raise ValueError("0 < overbought < extreme_overbought <= 100 범위여야 합니다")

        return True

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """스토캐스틱 지표 계산"""
        try:
            df = pd.DataFrame([
                {
                    "timestamp": candle.timestamp,
                    "high": float(candle.high),
                    "low": float(candle.low),
                    "close": float(candle.close),
                }
                for candle in ohlcv_data
            ])

            k_period = self.get_parameter("k_period")
            d_period = self.get_parameter("d_period")
            smooth = self.get_parameter("smooth")

            # 스토캐스틱 계산
            df["stoch_k"], df["stoch_d"] = calculate_stochastic(
                df["high"], df["low"], df["close"],
                k_period, d_period, smooth
            )

            # 최신 및 이전 값 추출
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            return {
                "stoch_k": Decimal(str(latest["stoch_k"])),
                "stoch_d": Decimal(str(latest["stoch_d"])),
                "stoch_k_prev": Decimal(str(previous["stoch_k"])),
                "stoch_d_prev": Decimal(str(previous["stoch_d"])),
                "price": Decimal(str(latest["close"])),
            }

        except Exception as e:
            logger.error(f"스토캐스틱 지표 계산 실패: {e}")
            raise IndicatorCalculationError(f"스토캐스틱 계산 실패: {str(e)}")

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        스토캐스틱 매도 조건 체크

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        stoch_k = indicators["stoch_k"]
        stoch_d = indicators["stoch_d"]
        stoch_k_prev = indicators["stoch_k_prev"]
        stoch_d_prev = indicators["stoch_d_prev"]

        overbought = Decimal(str(self.get_parameter("overbought")))
        extreme_overbought = Decimal(str(self.get_parameter("extreme_overbought")))
        cross_required = self.get_parameter("cross_required")

        # 1. 과매수 구간 확인
        is_overbought = stoch_k >= overbought
        is_extreme_overbought = stoch_k >= extreme_overbought

        if not is_overbought:
            return False, Decimal("0"), f"스토캐스틱 과매수 아님 (%K={stoch_k:.2f})"

        # 2. 데드 크로스 확인 (%K가 %D를 하향 돌파)
        dead_cross = (stoch_k_prev > stoch_d_prev) and (stoch_k <= stoch_d)

        # 3. cross_required가 True면 데드 크로스 필수
        if cross_required and not dead_cross:
            return False, Decimal("0"), "스토캐스틱 데드 크로스 필요"

        # 4. 기본 확신도 계산
        # %K가 높을수록 확신도 증가
        k_strength = (stoch_k - overbought) / (Decimal("100") - overbought)
        base_confidence = Decimal("0.7") + min(k_strength * Decimal("0.2"), Decimal("0.2"))

        # 5. 극단적 과매수 구간이면 확신도 증가
        if is_extreme_overbought:
            base_confidence = base_confidence * Decimal("1.2")

        # 6. 데드 크로스 발생 시 확신도 증가
        if dead_cross:
            base_confidence = base_confidence * Decimal("1.15")

        # 7. %K 하락 전환 확인 (추가 확신도)
        k_falling = stoch_k < stoch_k_prev
        if k_falling:
            base_confidence = base_confidence * Decimal("1.05")

        # 8. 손익률에 따라 확신도 조정
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        if profit_loss_pct > 10:
            # 큰 수익 중이면 확신도 증가 (이익 실현)
            base_confidence = base_confidence * Decimal("1.2")
        elif profit_loss_pct > 5:
            base_confidence = base_confidence * Decimal("1.1")
        elif profit_loss_pct > 0:
            base_confidence = base_confidence * Decimal("1.05")
        elif profit_loss_pct < -3:
            # 손실 중이면 확신도 감소 (손실 중 매도는 신중)
            base_confidence = base_confidence * Decimal("0.9")

        # 확신도 범위 조정
        confidence = min(Decimal("1"), base_confidence)

        # 이유 문자열 생성
        conditions = []
        if is_extreme_overbought:
            conditions.append(f"극단적 과매수 (%K={stoch_k:.2f})")
        else:
            conditions.append(f"과매수 (%K={stoch_k:.2f})")

        if dead_cross:
            conditions.append("데드 크로스")

        if k_falling:
            conditions.append("하락 전환")

        reason = (
            f"스토캐스틱 {', '.join(conditions)}, "
            f"손익률 {profit_loss_pct:.2f}%"
        )

        logger.info(
            f"스토캐스틱 매도 조건 충족: %K={stoch_k:.2f}, %D={stoch_d:.2f}, "
            f"손익률={profit_loss_pct:.2f}%, 확신도={confidence:.2%}"
        )

        return True, confidence, reason

    def get_minimum_data_points(self) -> int:
        """최소 데이터 개수"""
        k_period = self.get_parameter("k_period")
        smooth = self.get_parameter("smooth")
        return max(k_period + smooth + 10, 30)

    def __repr__(self) -> str:
        return (
            f"<StochasticExitStrategy(name={self.name}, "
            f"%K={self.get_parameter('k_period')}, "
            f"%D={self.get_parameter('d_period')}, "
            f"overbought={self.get_parameter('overbought')})>"
        )
