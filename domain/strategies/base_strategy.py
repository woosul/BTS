"""
BTS 전략 베이스 클래스

모든 트레이딩 전략의 기반이 되는 추상 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from core.enums import StrategySignal, StrategyStatus, TimeFrame
from core.models import OHLCV, StrategySignalData
from core.exceptions import StrategyError, IndicatorCalculationError
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseStrategy(ABC):
    """
    트레이딩 전략 베이스 클래스

    모든 전략은 이 클래스를 상속받아 구현
    """

    def __init__(
        self,
        id: int,
        name: str,
        description: str = "",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.timeframe = timeframe
        self.parameters = parameters or {}
        self.status = StrategyStatus.INACTIVE

        # 전략 통계
        self.total_signals = 0
        self.buy_signals = 0
        self.sell_signals = 0
        self.hold_signals = 0

        logger.info(f"전략 초기화: {self.name}")

    # ===== 추상 메서드 (필수 구현) =====
    @abstractmethod
    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        기술적 지표 계산

        Args:
            ohlcv_data: OHLCV 데이터 리스트

        Returns:
            Dict: 계산된 지표 값

        Raises:
            IndicatorCalculationError: 지표 계산 실패 시
        """
        pass

    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> StrategySignalData:
        """
        트레이딩 시그널 생성

        Args:
            symbol: 거래 심볼
            ohlcv_data: OHLCV 데이터
            indicators: 계산된 지표

        Returns:
            StrategySignalData: 시그널 데이터
        """
        pass

    @abstractmethod
    def validate_parameters(self) -> bool:
        """
        전략 파라미터 검증

        Returns:
            bool: 검증 성공 여부

        Raises:
            StrategyError: 파라미터가 유효하지 않은 경우
        """
        pass

    # ===== 공통 메서드 =====
    def analyze(self, symbol: str, ohlcv_data: List[OHLCV]) -> StrategySignalData:
        """
        시장 분석 및 시그널 생성 (전체 프로세스)

        Args:
            symbol: 거래 심볼
            ohlcv_data: OHLCV 데이터

        Returns:
            StrategySignalData: 시그널 데이터

        Raises:
            StrategyError: 분석 실패 시
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

            # 3. 시그널 생성
            signal_data = self.generate_signal(symbol, ohlcv_data, indicators)

            # 4. 통계 업데이트
            self._update_statistics(signal_data.signal)

            logger.info(
                f"시그널 생성 | 전략: {self.name} | {symbol} | "
                f"{signal_data.signal.value.upper()} (확신도: {signal_data.confidence:.2%})"
            )

            return signal_data

        except Exception as e:
            logger.error(f"전략 분석 실패: {e}")
            raise StrategyError(f"전략 분석 실패: {str(e)}")

    def activate(self) -> None:
        """전략 활성화"""
        self.validate_parameters()
        self.status = StrategyStatus.ACTIVE
        logger.info(f"전략 활성화: {self.name}")

    def deactivate(self) -> None:
        """전략 비활성화"""
        self.status = StrategyStatus.INACTIVE
        logger.info(f"전략 비활성화: {self.name}")

    def pause(self) -> None:
        """전략 일시정지"""
        self.status = StrategyStatus.PAUSED
        logger.info(f"전략 일시정지: {self.name}")

    def is_active(self) -> bool:
        """활성 상태 여부"""
        return self.status == StrategyStatus.ACTIVE

    def is_paused(self) -> bool:
        """일시정지 상태 여부"""
        return self.status == StrategyStatus.PAUSED

    def get_minimum_data_points(self) -> int:
        """
        필요한 최소 데이터 개수

        Returns:
            int: 최소 데이터 개수 (기본 30)
        """
        return self.parameters.get("min_data_points", 30)

    def get_parameter(self, key: str, default=None):
        """
        파라미터 조회

        Args:
            key: 파라미터 키
            default: 기본값

        Returns:
            파라미터 값
        """
        return self.parameters.get(key, default)

    def set_parameter(self, key: str, value) -> None:
        """
        파라미터 설정

        Args:
            key: 파라미터 키
            value: 파라미터 값
        """
        self.parameters[key] = value
        logger.debug(f"파라미터 설정: {key} = {value}")

    def update_parameters(self, parameters: Dict) -> None:
        """
        파라미터 일괄 업데이트

        Args:
            parameters: 새로운 파라미터
        """
        self.parameters.update(parameters)
        self.validate_parameters()
        logger.info(f"파라미터 업데이트 완료: {self.name}")

    # ===== 통계 관리 =====
    def _update_statistics(self, signal: StrategySignal) -> None:
        """
        시그널 통계 업데이트

        Args:
            signal: 생성된 시그널
        """
        self.total_signals += 1

        if signal == StrategySignal.BUY:
            self.buy_signals += 1
        elif signal == StrategySignal.SELL:
            self.sell_signals += 1
        else:
            self.hold_signals += 1

    def get_statistics(self) -> Dict:
        """
        전략 통계 조회

        Returns:
            Dict: 통계 정보
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "total_signals": self.total_signals,
            "buy_signals": self.buy_signals,
            "sell_signals": self.sell_signals,
            "hold_signals": self.hold_signals,
            "buy_ratio": (self.buy_signals / self.total_signals * 100) if self.total_signals > 0 else 0,
            "sell_ratio": (self.sell_signals / self.total_signals * 100) if self.total_signals > 0 else 0,
        }

    def reset_statistics(self) -> None:
        """통계 초기화"""
        self.total_signals = 0
        self.buy_signals = 0
        self.sell_signals = 0
        self.hold_signals = 0
        logger.info(f"통계 초기화: {self.name}")

    # ===== 유틸리티 메서드 =====
    def get_latest_price(self, ohlcv_data: List[OHLCV]) -> Decimal:
        """
        최신 가격 조회

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Decimal: 최신 종가
        """
        if not ohlcv_data:
            return Decimal("0")
        return ohlcv_data[-1].close

    def get_price_change_rate(
        self,
        ohlcv_data: List[OHLCV],
        periods: int = 1
    ) -> Decimal:
        """
        가격 변동률 계산

        Args:
            ohlcv_data: OHLCV 데이터
            periods: 기간

        Returns:
            Decimal: 변동률 (%)
        """
        if len(ohlcv_data) < periods + 1:
            return Decimal("0")

        current_price = ohlcv_data[-1].close
        previous_price = ohlcv_data[-(periods + 1)].close

        if previous_price == 0:
            return Decimal("0")

        return ((current_price - previous_price) / previous_price) * 100

    def calculate_confidence(
        self,
        signal_strength: Decimal,
        trend_strength: Decimal = Decimal("1"),
        volume_strength: Decimal = Decimal("1")
    ) -> Decimal:
        """
        확신도 계산

        Args:
            signal_strength: 시그널 강도 (0-1)
            trend_strength: 추세 강도 (0-1)
            volume_strength: 거래량 강도 (0-1)

        Returns:
            Decimal: 확신도 (0-1)
        """
        # 가중 평균 계산
        weights = {
            "signal": Decimal("0.5"),
            "trend": Decimal("0.3"),
            "volume": Decimal("0.2"),
        }

        confidence = (
            signal_strength * weights["signal"] +
            trend_strength * weights["trend"] +
            volume_strength * weights["volume"]
        )

        # 0-1 범위로 제한
        return max(Decimal("0"), min(Decimal("1"), confidence))

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(id={self.id}, name={self.name}, "
            f"status={self.status.value})>"
        )


if __name__ == "__main__":
    # 베이스 전략은 추상 클래스이므로 직접 테스트 불가
    print("=== 전략 베이스 클래스 ===")
    print("BaseStrategy는 추상 클래스입니다.")
    print("구체적인 전략(RSI, MA Cross 등)을 구현하여 사용하세요.")
