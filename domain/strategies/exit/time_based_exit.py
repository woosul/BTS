"""
BTS 시간 기반 매도 전략

보유 기간 경과 시 자동 매도하는 전략
"""
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class TimeBasedExitStrategy(BaseExitStrategy):
    """
    시간 기반 매도 전략

    매도 조건:
    - 보유 기간이 설정된 기간을 초과하면 자동 매도
    - 날짜/시간 제약 조건 지원 (ON/OFF 가능)
    - 장기 보유, 스윙 트레이딩, 단타 등 다양한 보유 전략에 활용

    파라미터:
    - holding_periods: 보유 기간 (캔들 개수 기준, 기본 24)
    - holding_hours: 보유 시간 (시간 기준, 선택적)
    - force_exit: 손실 중에도 강제 매도 여부 (기본 False)
    - min_profit_pct: 최소 익절률 (기본 0%, 이익 시에만 매도)
    - max_loss_pct: 최대 손절률 (기본 -10%)

    날짜/시간 제약 파라미터:
    - use_datetime_constraint: 날짜/시간 제약 사용 여부 (기본 False)
    - datetime_mode: 날짜/시간 모드 ("absolute" | "relative", 기본 "relative")
    - absolute_exit_datetime: 절대 날짜/시간 (datetime 객체, absolute 모드 시)
    - relative_exit_days: 상대 날짜 (매수 시점부터 N일 후, relative 모드 시)
    - relative_exit_hours: 상대 시간 (매수 시점부터 N시간 후, relative 모드 시)
    """

    def __init__(
        self,
        id: int,
        name: str = "Time Based Exit Strategy",
        description: str = "시간 기반 자동 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Dict = None,
    ):
        # 기본 파라미터 설정
        default_params = {
            "holding_periods": 24,  # 24개 캔들 (1시간봉 기준 24시간)
            "holding_hours": None,  # None이면 holding_periods 사용
            "force_exit": False,  # 손실 중에도 강제 매도
            "min_profit_pct": 0,  # 0% 이상일 때만 매도
            "max_loss_pct": -10,  # -10% 이하면 강제 손절
            "min_confidence": 0.6,
            "check_volume": False,
            # 날짜/시간 제약 파라미터
            "use_datetime_constraint": False,  # 날짜/시간 제약 ON/OFF
            "datetime_mode": "relative",  # "absolute" or "relative"
            "absolute_exit_datetime": None,  # datetime 객체 (절대 모드)
            "relative_exit_days": 0,  # 매수 후 N일 (상대 모드)
            "relative_exit_hours": 0,  # 매수 후 N시간 (상대 모드)
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
        holding_periods = self.get_parameter("holding_periods")
        holding_hours = self.get_parameter("holding_hours")

        if holding_periods is not None and holding_periods < 1:
            raise ValueError("보유 기간은 1 이상이어야 합니다")

        if holding_hours is not None and holding_hours < 0.1:
            raise ValueError("보유 시간은 0.1시간 이상이어야 합니다")

        # 날짜/시간 제약 파라미터 검증
        use_datetime_constraint = self.get_parameter("use_datetime_constraint")
        if use_datetime_constraint:
            datetime_mode = self.get_parameter("datetime_mode")
            if datetime_mode not in ["absolute", "relative"]:
                raise ValueError("datetime_mode는 'absolute' 또는 'relative'여야 합니다")

            if datetime_mode == "absolute":
                absolute_exit_datetime = self.get_parameter("absolute_exit_datetime")
                if absolute_exit_datetime is None:
                    raise ValueError("absolute 모드에서는 absolute_exit_datetime이 필요합니다")
                if not isinstance(absolute_exit_datetime, datetime):
                    raise ValueError("absolute_exit_datetime은 datetime 객체여야 합니다")

            elif datetime_mode == "relative":
                relative_exit_days = self.get_parameter("relative_exit_days")
                relative_exit_hours = self.get_parameter("relative_exit_hours")
                if relative_exit_days == 0 and relative_exit_hours == 0:
                    raise ValueError("relative 모드에서는 relative_exit_days 또는 relative_exit_hours 중 최소 하나는 0보다 커야 합니다")
                if relative_exit_days < 0 or relative_exit_hours < 0:
                    raise ValueError("relative_exit_days와 relative_exit_hours는 0 이상이어야 합니다")

        return True

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        시간 기반 전략은 별도 지표 계산이 필요 없음
        현재 가격만 반환
        """
        if not ohlcv_data:
            return {}

        return {
            "current_price": ohlcv_data[-1].close,
            "current_time": ohlcv_data[-1].timestamp,
        }

    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0,
        entry_time: Optional[datetime] = None
    ) -> tuple[bool, Decimal, str]:
        """
        시간 기반 매도 조건 체크

        Args:
            entry_price: 매수 가격
            current_price: 현재 가격
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표
            holding_period: 보유 기간 (캔들 개수)
            entry_time: 매수 시점 (datetime, 날짜/시간 제약 사용 시 필수)

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        holding_periods = self.get_parameter("holding_periods")
        holding_hours = self.get_parameter("holding_hours")
        force_exit = self.get_parameter("force_exit")
        use_datetime_constraint = self.get_parameter("use_datetime_constraint")

        # 현재 시간 추출
        current_time = indicators.get("current_time")
        if current_time is None and ohlcv_data:
            current_time = ohlcv_data[-1].timestamp

        # 1. 날짜/시간 제약 체크 (활성화된 경우)
        datetime_constraint_met = False
        datetime_reason = ""

        if use_datetime_constraint:
            if entry_time is None:
                logger.warning("날짜/시간 제약이 활성화되었지만 entry_time이 제공되지 않았습니다")
            else:
                datetime_mode = self.get_parameter("datetime_mode")

                if datetime_mode == "absolute":
                    # 절대 날짜/시간 모드: 지정된 날짜/시간 도달 시 매도
                    absolute_exit_datetime = self.get_parameter("absolute_exit_datetime")
                    if current_time >= absolute_exit_datetime:
                        datetime_constraint_met = True
                        datetime_reason = f"목표 시각 도달 ({absolute_exit_datetime.strftime('%Y-%m-%d %H:%M:%S')})"
                    else:
                        return False, Decimal("0"), f"목표 시각 미도달 (목표: {absolute_exit_datetime.strftime('%Y-%m-%d %H:%M:%S')})"

                elif datetime_mode == "relative":
                    # 상대 날짜/시간 모드: 매수 시점부터 N일/시간 경과 시 매도
                    relative_exit_days = self.get_parameter("relative_exit_days")
                    relative_exit_hours = self.get_parameter("relative_exit_hours")

                    # 목표 시간 계산
                    target_exit_time = entry_time + timedelta(
                        days=relative_exit_days,
                        hours=relative_exit_hours
                    )

                    if current_time >= target_exit_time:
                        datetime_constraint_met = True
                        total_hours = relative_exit_days * 24 + relative_exit_hours
                        datetime_reason = f"보유 시간 경과 (매수 후 {relative_exit_days}일 {relative_exit_hours}시간)"
                    else:
                        remaining = target_exit_time - current_time
                        remaining_hours = remaining.total_seconds() / 3600
                        return False, Decimal("0"), f"보유 시간 미달 (남은 시간: {remaining_hours:.1f}시간)"

        # 2. 기존 보유 기간 체크 (날짜/시간 제약이 없거나 비활성화된 경우)
        period_constraint_met = False
        period_reason = ""

        if not use_datetime_constraint:
            # holding_hours가 설정되어 있으면 우선 사용
            if holding_hours is not None:
                required_periods = int(holding_hours)  # 시간봉 기준
            else:
                required_periods = holding_periods

            if holding_period < required_periods:
                return False, Decimal("0"), f"보유 기간 미달 ({holding_period}/{required_periods})"

            period_constraint_met = True
            period_reason = f"보유 기간 초과 ({holding_period}개 캔들, {holding_period * self._get_timeframe_hours():.1f}시간)"

        # 3. 손익률 계산
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        # 4. 강제 매도 여부 확인
        if not force_exit:
            # 최소 익절률 체크
            min_profit_pct = Decimal(str(self.get_parameter("min_profit_pct")))
            if profit_loss_pct < min_profit_pct:
                return False, Decimal("0"), f"최소 익절률 미달 ({profit_loss_pct:.2f}% < {min_profit_pct:.2f}%)"

        # 5. 확신도 계산
        # 보유 기간이 길수록 확신도 증가
        if use_datetime_constraint:
            # 날짜/시간 제약 모드: 기본 확신도 높음
            base_confidence = Decimal("0.85")
        else:
            # 기존 로직
            required_periods = holding_hours if holding_hours is not None else holding_periods
            period_ratio = Decimal(str(holding_period)) / Decimal(str(required_periods))
            base_confidence = min(Decimal("0.7") + (period_ratio - Decimal("1")) * Decimal("0.1"), Decimal("0.95"))

        # 수익률에 따라 확신도 조정
        if profit_loss_pct > 0:
            # 수익 중이면 확신도 증가
            base_confidence = base_confidence * Decimal("1.1")
        elif profit_loss_pct < -5:
            # 큰 손실 중이면 확신도 증가 (빨리 손절)
            base_confidence = base_confidence * Decimal("1.2")
        else:
            # 소폭 손실 중이면 확신도 감소
            base_confidence = base_confidence * Decimal("0.9")

        # 확신도 범위 조정
        confidence = min(Decimal("1"), base_confidence)

        # 6. 이유 문자열 생성
        if use_datetime_constraint:
            reason = f"{datetime_reason}, 손익률 {profit_loss_pct:.2f}%"
        else:
            reason = f"{period_reason}, 손익률 {profit_loss_pct:.2f}%"

        logger.info(
            f"시간 기반 매도 조건 충족: {reason}, 확신도={confidence:.2%}"
        )

        return True, confidence, reason

    def _get_timeframe_hours(self) -> float:
        """타임프레임을 시간 단위로 변환"""
        timeframe_map = {
            TimeFrame.MINUTE_1: 1/60,
            TimeFrame.MINUTE_3: 3/60,
            TimeFrame.MINUTE_5: 5/60,
            TimeFrame.MINUTE_15: 15/60,
            TimeFrame.MINUTE_30: 30/60,
            TimeFrame.HOUR_1: 1,
            TimeFrame.HOUR_4: 4,
            TimeFrame.DAY_1: 24,
            TimeFrame.WEEK_1: 168,
        }
        return timeframe_map.get(self.timeframe, 1)

    def get_minimum_data_points(self) -> int:
        """최소 데이터 개수"""
        # 시간 기반 전략은 최소 데이터 필요 없음
        return 1

    def __repr__(self) -> str:
        holding_periods = self.get_parameter("holding_periods")
        holding_hours = self.get_parameter("holding_hours")
        use_datetime_constraint = self.get_parameter("use_datetime_constraint")

        if use_datetime_constraint:
            datetime_mode = self.get_parameter("datetime_mode")
            if datetime_mode == "absolute":
                absolute_exit_datetime = self.get_parameter("absolute_exit_datetime")
                time_info = f"절대시각={absolute_exit_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            else:  # relative
                relative_exit_days = self.get_parameter("relative_exit_days")
                relative_exit_hours = self.get_parameter("relative_exit_hours")
                time_info = f"상대시간={relative_exit_days}일 {relative_exit_hours}시간"
        else:
            if holding_hours:
                time_info = f"{holding_hours}시간"
            else:
                time_info = f"{holding_periods}캔들 ({holding_periods * self._get_timeframe_hours():.1f}시간)"

        return (
            f"<TimeBasedExitStrategy(name={self.name}, "
            f"holding={time_info})>"
        )
