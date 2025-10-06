"""
BTS 단계별 익절 매도 전략

가격 상승에 따라 분할 매도
"""
from typing import Dict, List, Optional
from decimal import Decimal

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class LadderExitStrategy(BaseExitStrategy):
    """
    단계별 익절 매도 전략

    가격 상승 단계에 따라 포지션을 분할 매도
    예: +5% 시 1/3, +10% 시 1/3, +20% 시 나머지
    """

    def __init__(
        self,
        id: int,
        name: str = "Ladder Exit",
        description: str = "단계별 익절 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            # 익절 단계: [수익률, 매도 비율]
            "profit_levels": [
                {"profit_pct": 5.0, "sell_ratio": 0.33},
                {"profit_pct": 10.0, "sell_ratio": 0.33},
                {"profit_pct": 20.0, "sell_ratio": 0.34}
            ],
            "stop_loss_pct": -5.0,
            "min_confidence": 0.85,
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        self.profit_levels = self.parameters["profit_levels"]
        self.stop_loss_pct = Decimal(str(self.parameters["stop_loss_pct"]))

        # 현재 어느 단계까지 실행했는지 추적 (외부에서 관리 필요)
        self.executed_levels = []

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        지표 계산

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Dict: 익절 단계 정보
        """
        return {
            "current_price": ohlcv_data[-1].close,
            "profit_levels": self.profit_levels,
            "stop_loss_pct": self.stop_loss_pct,
            "executed_levels": self.executed_levels
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

        # 1. 손절 체크
        if profit_loss_pct <= self.stop_loss_pct:
            return True, Decimal("0.98"), f"손절 ({profit_loss_pct:.2f}%)"

        # 2. 익절 단계 체크
        for i, level in enumerate(self.profit_levels):
            profit_pct = Decimal(str(level["profit_pct"]))
            sell_ratio = Decimal(str(level["sell_ratio"]))

            # 아직 실행하지 않은 단계이고, 목표 수익 달성
            if i not in self.executed_levels and profit_loss_pct >= profit_pct:
                # 실행 기록
                self.executed_levels.append(i)

                return (
                    True,
                    Decimal("0.9"),
                    f"단계 {i + 1} 익절 ({profit_loss_pct:.2f}% ≥ {profit_pct}%, 매도비율: {sell_ratio:.0%})"
                )

        return False, Decimal("0.5"), "익절 단계 미도달"

    def get_current_sell_ratio(self, profit_loss_pct: Decimal) -> Decimal:
        """
        현재 수익률에 해당하는 매도 비율 조회

        Args:
            profit_loss_pct: 현재 손익률

        Returns:
            Decimal: 매도 비율 (0-1)
        """
        for i, level in enumerate(self.profit_levels):
            profit_pct = Decimal(str(level["profit_pct"]))
            sell_ratio = Decimal(str(level["sell_ratio"]))

            if i not in self.executed_levels and profit_loss_pct >= profit_pct:
                return sell_ratio

        return Decimal("0")

    def reset_execution_state(self):
        """실행 상태 초기화 (새로운 포지션 시작 시)"""
        self.executed_levels = []
        logger.info(f"단계별 익절 상태 초기화: {self.name}")

    def validate_parameters(self) -> bool:
        """
        파라미터 검증

        Returns:
            bool: 검증 성공 여부
        """
        errors = []

        if not self.profit_levels:
            errors.append("profit_levels가 비어있습니다")

        # 익절 단계 검증
        total_ratio = Decimal("0")
        prev_profit = Decimal("0")

        for i, level in enumerate(self.profit_levels):
            if "profit_pct" not in level or "sell_ratio" not in level:
                errors.append(f"단계 {i + 1}: profit_pct 또는 sell_ratio가 없습니다")
                continue

            profit_pct = Decimal(str(level["profit_pct"]))
            sell_ratio = Decimal(str(level["sell_ratio"]))

            # 수익률 증가 확인
            if profit_pct <= prev_profit:
                errors.append(f"단계 {i + 1}: profit_pct는 이전 단계보다 커야 합니다")

            # 매도 비율 범위 확인
            if not (0 < sell_ratio <= 1):
                errors.append(f"단계 {i + 1}: sell_ratio는 0과 1 사이여야 합니다")

            total_ratio += sell_ratio
            prev_profit = profit_pct

        # 총 매도 비율이 1에 가까운지 확인
        if abs(total_ratio - Decimal("1")) > Decimal("0.05"):
            errors.append(f"전체 매도 비율의 합이 1에 가까워야 합니다 (현재: {total_ratio})")

        if self.stop_loss_pct >= 0:
            errors.append("stop_loss_pct는 0보다 작아야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "Ladder Exit 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """필요한 최소 데이터 개수"""
        return 1

    def __repr__(self) -> str:
        levels_str = ", ".join(
            f"{l['profit_pct']}%:{l['sell_ratio']:.0%}"
            for l in self.profit_levels
        )
        return (
            f"<LadderExitStrategy(name={self.name}, "
            f"levels=[{levels_str}])>"
        )


if __name__ == "__main__":
    print("=== 단계별 익절 매도 전략 테스트 ===")

    from datetime import datetime, timedelta

    # 전략 생성
    strategy = LadderExitStrategy(
        id=1,
        parameters={
            "profit_levels": [
                {"profit_pct": 5.0, "sell_ratio": 0.33},
                {"profit_pct": 10.0, "sell_ratio": 0.33},
                {"profit_pct": 20.0, "sell_ratio": 0.34}
            ],
            "stop_loss_pct": -5.0,
        }
    )

    strategy.activate()

    # 테스트 시나리오: 점진적 상승
    entry_price = Decimal("50000000")
    scenarios = [
        ("3% 상승", Decimal("51500000")),
        ("7% 상승", Decimal("53500000")),
        ("12% 상승", Decimal("56000000")),
        ("25% 상승", Decimal("62500000")),
    ]

    for scenario_name, current_price in scenarios:
        test_data = [
            OHLCV(
                timestamp=datetime.now(),
                open=current_price,
                high=current_price,
                low=current_price,
                close=current_price,
                volume=Decimal("100")
            )
        ]

        signal_data = strategy.evaluate_exit(
            symbol="KRW-BTC",
            entry_price=entry_price,
            ohlcv_data=test_data
        )

        profit_pct = strategy.calculate_profit_loss_pct(entry_price, current_price)

        print(f"\n{scenario_name} ({profit_pct:.2f}%)")
        print(f"  시그널: {signal_data.signal.value.upper()}")
        print(f"  확신도: {signal_data.confidence:.2%}")
        print(f"  이유: {signal_data.metadata.get('reason', 'N/A')}")
        print(f"  실행된 단계: {strategy.executed_levels}")
