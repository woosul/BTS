"""
BTS 매수 전략 베이스 클래스

모든 매수 전략의 기반이 되는 추상 클래스
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


class BaseEntryStrategy(BaseStrategy, ABC):
    """
    매수 전략 베이스 클래스

    모든 매수(Entry) 전략은 이 클래스를 상속받아 구현
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

        # 매수 전략 전용 파라미터
        self.min_confidence = Decimal(str(parameters.get("min_confidence", 0.6)))
        self.volume_check = parameters.get("volume_check", True)
        self.trend_check = parameters.get("trend_check", True)

        logger.info(f"매수 전략 초기화: {self.name}")

    @abstractmethod
    def check_entry_condition(
        self,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> tuple[bool, Decimal]:
        """
        매수 조건 체크

        Args:
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표

        Returns:
            tuple: (매수 조건 만족 여부, 확신도)
        """
        pass

    def check_volume_condition(self, ohlcv_data: List[OHLCV]) -> bool:
        """
        거래량 조건 체크

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            bool: 거래량 조건 만족 여부
        """
        if not self.volume_check or len(ohlcv_data) < 20:
            return True

        # 최근 거래량이 평균 대비 충분한지 확인
        recent_volume = ohlcv_data[-1].volume
        avg_volume = sum(candle.volume for candle in ohlcv_data[-20:]) / 20

        volume_threshold = Decimal(str(self.parameters.get("volume_threshold", 0.8)))

        return recent_volume >= avg_volume * volume_threshold

    def check_trend_condition(self, ohlcv_data: List[OHLCV]) -> bool:
        """
        추세 조건 체크 (단순 이동평균 기반)

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            bool: 상승 추세 여부
        """
        if not self.trend_check or len(ohlcv_data) < 20:
            return True

        # 20일 이동평균 계산
        ma_20 = sum(candle.close for candle in ohlcv_data[-20:]) / 20
        current_price = ohlcv_data[-1].close

        # 현재가가 이동평균 위에 있으면 상승 추세로 판단
        return current_price >= ma_20

    def generate_signal(
        self,
        symbol: str,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> StrategySignalData:
        """
        매수 시그널 생성

        Args:
            symbol: 거래 심볼
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표

        Returns:
            StrategySignalData: 시그널 데이터
        """
        try:
            # 1. 매수 조건 체크
            entry_condition, base_confidence = self.check_entry_condition(
                ohlcv_data, indicators
            )

            if not entry_condition:
                return StrategySignalData(
                    signal=StrategySignal.HOLD,
                    confidence=Decimal("0.5"),
                    price=ohlcv_data[-1].close,
                    timestamp=ohlcv_data[-1].timestamp,
                    indicators=indicators,
                    metadata={"reason": "매수 조건 미충족"}
                )

            # 2. 거래량 체크
            if not self.check_volume_condition(ohlcv_data):
                return StrategySignalData(
                    signal=StrategySignal.HOLD,
                    confidence=Decimal("0.5"),
                    price=ohlcv_data[-1].close,
                    timestamp=ohlcv_data[-1].timestamp,
                    indicators=indicators,
                    metadata={"reason": "거래량 부족"}
                )

            # 3. 추세 체크
            if not self.check_trend_condition(ohlcv_data):
                # 추세가 좋지 않으면 확신도 감소
                base_confidence *= Decimal("0.8")

            # 4. 최종 확신도 계산
            volume_strength = self._calculate_volume_strength(ohlcv_data)
            final_confidence = self.calculate_confidence(
                base_confidence,
                Decimal("1") if self.check_trend_condition(ohlcv_data) else Decimal("0.7"),
                volume_strength
            )

            # 5. 최소 확신도 체크
            if final_confidence < self.min_confidence:
                return StrategySignalData(
                    signal=StrategySignal.HOLD,
                    confidence=final_confidence,
                    price=ohlcv_data[-1].close,
                    timestamp=ohlcv_data[-1].timestamp,
                    indicators=indicators,
                    metadata={"reason": f"확신도 부족 ({final_confidence:.2%})"}
                )

            # 6. 매수 시그널 반환
            return StrategySignalData(
                signal=StrategySignal.BUY,
                confidence=final_confidence,
                price=ohlcv_data[-1].close,
                timestamp=ohlcv_data[-1].timestamp,
                indicators=indicators,
                metadata={
                    "strategy": self.name,
                    "timeframe": self.timeframe.value,
                    "volume_ok": True,
                    "trend_ok": self.check_trend_condition(ohlcv_data)
                }
            )

        except Exception as e:
            logger.error(f"매수 시그널 생성 실패: {e}")
            raise StrategyError(f"매수 시그널 생성 실패: {str(e)}")

    def _calculate_volume_strength(self, ohlcv_data: List[OHLCV]) -> Decimal:
        """
        거래량 강도 계산

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Decimal: 거래량 강도 (0-1)
        """
        if len(ohlcv_data) < 20:
            return Decimal("0.5")

        recent_volume = float(ohlcv_data[-1].volume)
        avg_volume = sum(float(candle.volume) for candle in ohlcv_data[-20:]) / 20

        if avg_volume == 0:
            return Decimal("0.5")

        ratio = recent_volume / avg_volume

        # 비율을 0-1 범위로 정규화 (2배 이상이면 1.0)
        strength = min(ratio / 2, 1.0)

        return Decimal(str(strength))

    def get_entry_price(self, ohlcv_data: List[OHLCV]) -> Decimal:
        """
        진입 가격 계산

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Decimal: 진입 가격
        """
        # 기본: 현재 종가
        return ohlcv_data[-1].close

    def calculate_position_size(
        self,
        available_balance: Decimal,
        entry_price: Decimal,
        risk_per_trade: Decimal = Decimal("0.02")  # 2%
    ) -> Decimal:
        """
        포지션 크기 계산

        Args:
            available_balance: 사용 가능 잔액
            entry_price: 진입 가격
            risk_per_trade: 거래당 리스크 비율

        Returns:
            Decimal: 매수 수량
        """
        if entry_price <= 0:
            return Decimal("0")

        # 리스크 기반 포지션 크기 계산
        risk_amount = available_balance * risk_per_trade
        position_size = risk_amount / entry_price

        return position_size

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(name={self.name}, "
            f"min_confidence={self.min_confidence})>"
        )
