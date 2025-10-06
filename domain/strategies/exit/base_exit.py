"""
BTS 매도 전략 베이스 클래스

모든 매도 전략의 기반이 되는 추상 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from domain.strategies.base_strategy import BaseStrategy
from core.enums import StrategySignal, TimeFrame
from core.models import OHLCV, StrategySignalData
from core.exceptions import StrategyError
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseExitStrategy(BaseStrategy, ABC):
    """
    매도 전략 베이스 클래스

    모든 매도(Exit) 전략은 이 클래스를 상속받아 구현
    """

    def __init__(
        self,
        id: int,
        name: str,
        description: str = "",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        super().__init__(id, name, description, timeframe, parameters)

        # 매도 전략 전용 파라미터
        self.min_confidence = Decimal(str(parameters.get("min_confidence", 0.7)))
        self.min_profit_pct = Decimal(str(parameters.get("min_profit_pct", 0)))  # 최소 익절률
        self.max_loss_pct = Decimal(str(parameters.get("max_loss_pct", -100)))  # 최대 손실률
        self.check_volume = parameters.get("check_volume", False)

        logger.info(f"매도 전략 초기화: {self.name}")

    @abstractmethod
    def check_exit_condition(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        ohlcv_data: List[OHLCV],
        indicators: Dict,
        holding_period: int = 0
    ) -> tuple[bool, Decimal, str]:
        """
        매도 조건 체크

        Args:
            entry_price: 매수 가격
            current_price: 현재 가격
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표
            holding_period: 보유 기간 (캔들 개수)

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        pass

    def calculate_profit_loss_pct(
        self,
        entry_price: Decimal,
        current_price: Decimal
    ) -> Decimal:
        """
        손익률 계산

        Args:
            entry_price: 매수 가격
            current_price: 현재 가격

        Returns:
            Decimal: 손익률 (%)
        """
        if entry_price <= 0:
            return Decimal("0")

        return ((current_price - entry_price) / entry_price) * 100

    def check_basic_exit_conditions(
        self,
        entry_price: Decimal,
        current_price: Decimal
    ) -> tuple[bool, str]:
        """
        기본 매도 조건 체크 (최소 익절/손절)

        Args:
            entry_price: 매수 가격
            current_price: 현재 가격

        Returns:
            tuple: (조건 충족 여부, 이유)
        """
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        # 최소 익절률 달성
        if self.min_profit_pct > 0 and profit_loss_pct >= self.min_profit_pct:
            return True, f"최소 익절 달성 ({profit_loss_pct:.2f}%)"

        # 최대 손실률 도달
        if profit_loss_pct <= self.max_loss_pct:
            return True, f"손절 ({profit_loss_pct:.2f}%)"

        return False, ""

    def check_volume_condition(self, ohlcv_data: List[OHLCV]) -> bool:
        """
        거래량 조건 체크 (급증 시 매도 고려)

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            bool: 거래량 급증 여부
        """
        if not self.check_volume or len(ohlcv_data) < 20:
            return False

        # 최근 거래량이 평균 대비 2배 이상이면 급증으로 판단
        recent_volume = ohlcv_data[-1].volume
        avg_volume = sum(candle.volume for candle in ohlcv_data[-20:]) / 20

        volume_threshold = Decimal(str(self.parameters.get("volume_threshold", 2.0)))

        return recent_volume >= avg_volume * volume_threshold

    def generate_signal(
        self,
        symbol: str,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> StrategySignalData:
        """
        매도 시그널 생성

        Note: 매도 전략은 entry_price가 필요하므로,
        실제 사용 시 check_exit_condition을 직접 호출하는 것을 권장

        Args:
            symbol: 거래 심볼
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표

        Returns:
            StrategySignalData: 시그널 데이터
        """
        # 기본 구현: entry_price 없이 호출 시 HOLD 반환
        return StrategySignalData(
            signal=StrategySignal.HOLD,
            confidence=Decimal("0.5"),
            price=ohlcv_data[-1].close,
            timestamp=ohlcv_data[-1].timestamp,
            indicators=indicators,
            metadata={"reason": "매도 전략은 entry_price가 필요합니다"}
        )

    def evaluate_exit(
        self,
        symbol: str,
        entry_price: Decimal,
        ohlcv_data: List[OHLCV],
        holding_period: int = 0
    ) -> StrategySignalData:
        """
        매도 평가 (entry_price를 포함한 완전한 평가)

        Args:
            symbol: 거래 심볼
            entry_price: 매수 가격
            ohlcv_data: OHLCV 데이터
            holding_period: 보유 기간 (캔들 개수)

        Returns:
            StrategySignalData: 시그널 데이터
        """
        try:
            # 1. 데이터 검증
            if not ohlcv_data or len(ohlcv_data) < self.get_minimum_data_points():
                raise StrategyError(
                    f"데이터가 부족합니다 (최소 {self.get_minimum_data_points()}개 필요)",
                    {"provided": len(ohlcv_data) if ohlcv_data else 0}
                )

            # 2. 지표 계산
            indicators = self.calculate_indicators(ohlcv_data)

            # 3. 현재 가격
            current_price = ohlcv_data[-1].close

            # 4. 손익률 계산
            profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)
            indicators["profit_loss_pct"] = profit_loss_pct

            # 5. 기본 조건 체크
            basic_exit, basic_reason = self.check_basic_exit_conditions(entry_price, current_price)

            if basic_exit:
                return StrategySignalData(
                    signal=StrategySignal.SELL,
                    confidence=Decimal("0.95"),  # 기본 조건은 높은 확신도
                    price=current_price,
                    timestamp=ohlcv_data[-1].timestamp,
                    indicators=indicators,
                    metadata={
                        "reason": basic_reason,
                        "entry_price": float(entry_price),
                        "profit_loss_pct": float(profit_loss_pct)
                    }
                )

            # 6. 전략별 매도 조건 체크
            exit_condition, confidence, reason = self.check_exit_condition(
                entry_price,
                current_price,
                ohlcv_data,
                indicators,
                holding_period
            )

            if not exit_condition:
                return StrategySignalData(
                    signal=StrategySignal.HOLD,
                    confidence=Decimal("0.5"),
                    price=current_price,
                    timestamp=ohlcv_data[-1].timestamp,
                    indicators=indicators,
                    metadata={
                        "reason": "매도 조건 미충족",
                        "entry_price": float(entry_price),
                        "profit_loss_pct": float(profit_loss_pct)
                    }
                )

            # 7. 최소 확신도 체크
            if confidence < self.min_confidence:
                return StrategySignalData(
                    signal=StrategySignal.HOLD,
                    confidence=confidence,
                    price=current_price,
                    timestamp=ohlcv_data[-1].timestamp,
                    indicators=indicators,
                    metadata={
                        "reason": f"확신도 부족 ({confidence:.2%})",
                        "entry_price": float(entry_price),
                        "profit_loss_pct": float(profit_loss_pct)
                    }
                )

            # 8. 매도 시그널 반환
            return StrategySignalData(
                signal=StrategySignal.SELL,
                confidence=confidence,
                price=current_price,
                timestamp=ohlcv_data[-1].timestamp,
                indicators=indicators,
                metadata={
                    "reason": reason,
                    "strategy": self.name,
                    "entry_price": float(entry_price),
                    "profit_loss_pct": float(profit_loss_pct),
                    "holding_period": holding_period
                }
            )

        except Exception as e:
            logger.error(f"매도 시그널 생성 실패: {e}")
            raise StrategyError(f"매도 시그널 생성 실패: {str(e)}")

    def calculate_take_profit_price(
        self,
        entry_price: Decimal,
        profit_pct: Decimal
    ) -> Decimal:
        """
        익절 가격 계산

        Args:
            entry_price: 매수 가격
            profit_pct: 목표 익절률 (%)

        Returns:
            Decimal: 익절 가격
        """
        return entry_price * (1 + profit_pct / 100)

    def calculate_stop_loss_price(
        self,
        entry_price: Decimal,
        loss_pct: Decimal
    ) -> Decimal:
        """
        손절 가격 계산

        Args:
            entry_price: 매수 가격
            loss_pct: 손절률 (%, 음수)

        Returns:
            Decimal: 손절 가격
        """
        return entry_price * (1 + loss_pct / 100)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(name={self.name}, "
            f"min_confidence={self.min_confidence})>"
        )
