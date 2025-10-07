"""
BTS 이동평균 교차 매도 전략

데드 크로스 기반 매도 전략
"""
from typing import Dict, List
from decimal import Decimal
import pandas as pd

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from core.exceptions import IndicatorCalculationError
from utils.logger import get_logger
from utils.technical_indicators import calculate_sma, calculate_ema

logger = get_logger(__name__)


class MACrossExitStrategy(BaseExitStrategy):
    """
    이동평균 교차 매도 전략 (Dead Cross)

    매도 조건:
    - 단기 이동평균선이 장기 이동평균선을 하향 돌파 (데드 크로스)
    - 최근 교차일수록 높은 확신도

    파라미터:
    - short_period: 단기 이동평균 기간 (기본 20)
    - long_period: 장기 이동평균 기간 (기본 60)
    - ma_type: 이동평균 타입 (SMA/EMA, 기본 EMA)
    - cross_lookback: 교차 확인 기간 (기본 3, 최근 N개 캔들 내 교차 발생)
    - min_profit_pct: 최소 익절률 (기본 3%)
    - max_loss_pct: 최대 손절률 (기본 -5%)
    """

    def __init__(
        self,
        id: int,
        name: str = "MA Cross Exit Strategy",
        description: str = "데드 크로스 기반 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "short_period": 20,
            "long_period": 60,
            "ma_type": "EMA",  # SMA or EMA
            "cross_lookback": 3,
            "min_confidence": 0.7,
            "min_profit_pct": 3,
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
        short_period = self.get_parameter("short_period")
        long_period = self.get_parameter("long_period")
        ma_type = self.get_parameter("ma_type")

        if not isinstance(short_period, int) or short_period < 2:
            raise ValueError("단기 이동평균 기간은 2 이상의 정수여야 합니다")

        if not isinstance(long_period, int) or long_period < short_period:
            raise ValueError("장기 이동평균 기간은 단기보다 커야 합니다")

        if ma_type not in ["SMA", "EMA"]:
            raise ValueError("이동평균 타입은 SMA 또는 EMA여야 합니다")

        return True

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """이동평균 지표 계산"""
        try:
            df = pd.DataFrame([
                {
                    "timestamp": candle.timestamp,
                    "close": float(candle.close),
                }
                for candle in ohlcv_data
            ])

            short_period = self.get_parameter("short_period")
            long_period = self.get_parameter("long_period")
            ma_type = self.get_parameter("ma_type")

            # 이동평균 계산
            if ma_type == "EMA":
                df["ma_short"] = calculate_ema(df["close"], short_period)
                df["ma_long"] = calculate_ema(df["close"], long_period)
            else:  # SMA
                df["ma_short"] = calculate_sma(df["close"], short_period)
                df["ma_long"] = calculate_sma(df["close"], long_period)

            # 최신 값 추출
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            return {
                "ma_short": Decimal(str(latest["ma_short"])),
                "ma_long": Decimal(str(latest["ma_long"])),
                "ma_short_prev": Decimal(str(previous["ma_short"])),
                "ma_long_prev": Decimal(str(previous["ma_long"])),
                "price": Decimal(str(latest["close"])),
            }

        except Exception as e:
            logger.error(f"이동평균 지표 계산 실패: {e}")
            raise IndicatorCalculationError(f"이동평균 계산 실패: {str(e)}")

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        데드 크로스 매도 조건 체크

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        ma_short = indicators["ma_short"]
        ma_long = indicators["ma_long"]
        ma_short_prev = indicators["ma_short_prev"]
        ma_long_prev = indicators["ma_long_prev"]

        # 1. 데드 크로스 확인 (이전: 단기 > 장기, 현재: 단기 <= 장기)
        dead_cross = (ma_short_prev > ma_long_prev) and (ma_short <= ma_long)

        if not dead_cross:
            # 이미 데드 크로스 상태인지 확인 (cross_lookback 기간 내)
            cross_lookback = self.get_parameter("cross_lookback")
            if ma_short < ma_long:
                # 최근 교차 여부를 확인하기 위해 간격 계산
                gap = abs((ma_long - ma_short) / ma_long)
                # 갭이 작으면 최근 교차로 간주 (3% 이내)
                if gap <= Decimal("0.03"):
                    dead_cross = True
                else:
                    return False, Decimal("0"), "데드 크로스 아님"
            else:
                return False, Decimal("0"), "데드 크로스 아님"

        # 2. 기본 확신도 계산
        # 장기 MA와 단기 MA의 차이가 클수록 확신도 증가
        ma_diff = (ma_long - ma_short) / ma_long * 100  # %

        # 교차 후 갭이 클수록 확신도 증가 (최대 5%까지)
        if ma_diff <= 0:
            confidence = Decimal("0.6")
        else:
            confidence = Decimal("0.7") + min(ma_diff / Decimal("5"), Decimal("0.2"))

        # 3. 가격이 두 MA 아래에 있으면 확신도 증가
        price = indicators["price"]
        if price < ma_short and price < ma_long:
            confidence = confidence * Decimal("1.1")

        # 4. 손익률에 따라 확신도 조정
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        # 수익 중이면 확신도 증가 (이익 실현)
        if profit_loss_pct > 5:
            confidence = confidence * Decimal("1.15")
        elif profit_loss_pct > 0:
            confidence = confidence * Decimal("1.05")
        # 큰 손실 중이면 확신도 증가 (손절)
        elif profit_loss_pct < -5:
            confidence = confidence * Decimal("1.2")

        # 확신도 범위 조정 (0-1)
        confidence = min(Decimal("1"), confidence)

        reason = (
            f"데드 크로스 (단기MA={ma_short:.2f}, 장기MA={ma_long:.2f}), "
            f"손익률 {profit_loss_pct:.2f}%"
        )

        logger.info(
            f"데드 크로스 매도 조건 충족: 단기MA={ma_short:.2f}, "
            f"장기MA={ma_long:.2f}, 손익률={profit_loss_pct:.2f}%, "
            f"확신도={confidence:.2%}"
        )

        return True, confidence, reason

    def get_minimum_data_points(self) -> int:
        """최소 데이터 개수"""
        long_period = self.get_parameter("long_period")
        return max(long_period + 20, 80)

    def __repr__(self) -> str:
        return (
            f"<MACrossExitStrategy(name={self.name}, "
            f"{self.get_parameter('ma_type')}"
            f"({self.get_parameter('short_period')}/{self.get_parameter('long_period')}))>"
        )
