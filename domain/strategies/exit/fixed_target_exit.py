"""
BTS 고정 목표가 매도 전략

목표 수익률 달성 시 또는 손절 시 매도
"""
from typing import Dict, List, Optional
from decimal import Decimal

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class FixedTargetExitStrategy(BaseExitStrategy):
    """
    고정 목표가 매도 전략

    - 목표 수익률 달성 시 매도
    - 손절률 도달 시 매도
    """

    def __init__(
        self,
        id: int,
        name: str = "Fixed Target Exit",
        description: str = "고정 목표가 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "target_profit_pct": 10.0,  # 목표 수익률 (%)
            "stop_loss_pct": -5.0,      # 손절률 (%)
            "min_confidence": 0.9,      # 높은 확신도
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        self.target_profit_pct = Decimal(str(self.parameters["target_profit_pct"]))
        self.stop_loss_pct = Decimal(str(self.parameters["stop_loss_pct"]))

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        지표 계산 (고정 목표가 전략은 별도 지표 불필요)

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Dict: 기본 정보
        """
        return {
            "current_price": ohlcv_data[-1].close,
            "target_profit_pct": self.target_profit_pct,
            "stop_loss_pct": self.stop_loss_pct
        }

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
            holding_period: 보유 기간

        Returns:
            tuple: (매도 조건 만족 여부, 확신도, 이유)
        """
        profit_loss_pct = self.calculate_profit_loss_pct(entry_price, current_price)

        # 1. 목표 수익 달성
        if profit_loss_pct >= self.target_profit_pct:
            return True, Decimal("0.95"), f"목표 수익 달성 ({profit_loss_pct:.2f}% ≥ {self.target_profit_pct}%)"

        # 2. 손절
        if profit_loss_pct <= self.stop_loss_pct:
            return True, Decimal("0.98"), f"손절 ({profit_loss_pct:.2f}% ≤ {self.stop_loss_pct}%)"

        return False, Decimal("0.5"), "조건 미충족"

    def validate_parameters(self) -> bool:
        """
        파라미터 검증

        Returns:
            bool: 검증 성공 여부
        """
        errors = []

        if self.target_profit_pct <= 0:
            errors.append("target_profit_pct는 0보다 커야 합니다")

        if self.stop_loss_pct >= 0:
            errors.append("stop_loss_pct는 0보다 작아야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "Fixed Target Exit 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """필요한 최소 데이터 개수"""
        return 1  # 현재가만 필요

    def __repr__(self) -> str:
        return (
            f"<FixedTargetExitStrategy(name={self.name}, "
            f"target={self.target_profit_pct}%, stop={self.stop_loss_pct}%)>"
        )


if __name__ == "__main__":
    print("=== 고정 목표가 매도 전략 테스트 ===")

    from datetime import datetime, timedelta

    # 테스트 데이터 생성
    test_data = []
    base_price = Decimal("50000000")
    entry_price = Decimal("50000000")
    base_time = datetime.now()

    # 시나리오 1: 가격 상승 (목표 수익 달성)
    for i in range(20):
        price = base_price + Decimal(str(i * 300000))  # 점진적 상승
        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=price - Decimal("50000"),
            high=price + Decimal("100000"),
            low=price - Decimal("100000"),
            close=price,
            volume=Decimal("100")
        )
        test_data.append(candle)

    # 전략 생성
    strategy = FixedTargetExitStrategy(
        id=1,
        parameters={
            "target_profit_pct": 10.0,
            "stop_loss_pct": -5.0,
        }
    )

    strategy.activate()

    # 매도 평가
    signal_data = strategy.evaluate_exit(
        symbol="KRW-BTC",
        entry_price=entry_price,
        ohlcv_data=test_data
    )

    print(f"\n시그널: {signal_data.signal.value.upper()}")
    print(f"확신도: {signal_data.confidence:.2%}")
    print(f"현재가: {signal_data.price:,.0f} KRW")
    print(f"진입가: {entry_price:,.0f} KRW")
    print(f"손익률: {signal_data.indicators['profit_loss_pct']:.2f}%")
    print(f"이유: {signal_data.metadata.get('reason', 'N/A')}")
