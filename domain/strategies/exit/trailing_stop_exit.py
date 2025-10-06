"""
BTS 트레일링 스탑 매도 전략

최고가 대비 일정 비율 하락 시 매도
"""
from typing import Dict, List, Optional
from decimal import Decimal

from domain.strategies.exit.base_exit import BaseExitStrategy
from core.enums import TimeFrame
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class TrailingStopExitStrategy(BaseExitStrategy):
    """
    트레일링 스탑 매도 전략

    진입 후 최고가 대비 일정 비율 하락 시 매도
    - 가격이 상승하면 손절선도 함께 상승
    - 수익을 보호하면서 추가 상승 여력 확보
    """

    def __init__(
        self,
        id: int,
        name: str = "Trailing Stop Exit",
        description: str = "트레일링 스탑 매도 전략",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "trailing_pct": 3.0,        # 최고가 대비 하락률 (%)
            "activation_profit": 2.0,    # 트레일링 활성화 수익률 (%)
            "stop_loss_pct": -5.0,       # 초기 손절률
            "min_confidence": 0.9,
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, timeframe, default_params)

        self.trailing_pct = Decimal(str(self.parameters["trailing_pct"]))
        self.activation_profit = Decimal(str(self.parameters["activation_profit"]))
        self.stop_loss_pct = Decimal(str(self.parameters["stop_loss_pct"]))

        # 최고가 추적 (외부에서 관리 필요)
        self.highest_price = Decimal("0")

    def calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        지표 계산

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Dict: 트레일링 정보
        """
        # 최근 N개 캔들의 최고가 조회
        lookback = min(len(ohlcv_data), 20)
        recent_high = max(candle.high for candle in ohlcv_data[-lookback:])

        return {
            "current_price": ohlcv_data[-1].close,
            "recent_high": recent_high,
            "highest_price": self.highest_price,
            "trailing_pct": self.trailing_pct,
            "activation_profit": self.activation_profit
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

        # 1. 최고가 업데이트
        if current_price > self.highest_price:
            self.highest_price = current_price
            logger.debug(f"최고가 업데이트: {self.highest_price:,.0f}")

        # 2. 초기 손절 (트레일링 활성화 전)
        if profit_loss_pct <= self.stop_loss_pct:
            return True, Decimal("0.98"), f"초기 손절 ({profit_loss_pct:.2f}%)"

        # 3. 트레일링 활성화 조건: 최소 수익률 달성
        if profit_loss_pct < self.activation_profit:
            return False, Decimal("0.5"), f"트레일링 미활성 (수익률 {profit_loss_pct:.2f}% < {self.activation_profit}%)"

        # 4. 트레일링 스탑 체크
        if self.highest_price > 0:
            drawdown_from_high = ((current_price - self.highest_price) / self.highest_price) * 100

            if drawdown_from_high <= -self.trailing_pct:
                return (
                    True,
                    Decimal("0.95"),
                    f"트레일링 스탑 ({drawdown_from_high:.2f}% ≤ -{self.trailing_pct}%)"
                )

        return False, Decimal("0.5"), "조건 미충족"

    def reset_execution_state(self):
        """실행 상태 초기화 (새로운 포지션 시작 시)"""
        self.highest_price = Decimal("0")
        logger.info(f"트레일링 스탑 상태 초기화: {self.name}")

    def set_initial_price(self, entry_price: Decimal):
        """
        초기 가격 설정

        Args:
            entry_price: 진입 가격
        """
        self.highest_price = entry_price
        logger.info(f"트레일링 스탑 초기 가격: {entry_price:,.0f}")

    def get_current_stop_price(self) -> Decimal:
        """
        현재 손절 가격 조회

        Returns:
            Decimal: 현재 트레일링 스탑 가격
        """
        if self.highest_price <= 0:
            return Decimal("0")

        return self.highest_price * (1 - self.trailing_pct / 100)

    def validate_parameters(self) -> bool:
        """
        파라미터 검증

        Returns:
            bool: 검증 성공 여부
        """
        errors = []

        if self.trailing_pct <= 0:
            errors.append("trailing_pct는 0보다 커야 합니다")

        if self.trailing_pct > 50:
            errors.append("trailing_pct는 50% 이하여야 합니다")

        if self.activation_profit < 0:
            errors.append("activation_profit는 0 이상이어야 합니다")

        if self.stop_loss_pct >= 0:
            errors.append("stop_loss_pct는 0보다 작아야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "Trailing Stop Exit 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def get_minimum_data_points(self) -> int:
        """필요한 최소 데이터 개수"""
        return 1

    def __repr__(self) -> str:
        return (
            f"<TrailingStopExitStrategy(name={self.name}, "
            f"trailing={self.trailing_pct}%, activation={self.activation_profit}%)>"
        )


if __name__ == "__main__":
    print("=== 트레일링 스탑 매도 전략 테스트 ===")

    from datetime import datetime, timedelta

    # 전략 생성
    strategy = TrailingStopExitStrategy(
        id=1,
        parameters={
            "trailing_pct": 3.0,
            "activation_profit": 2.0,
            "stop_loss_pct": -5.0,
        }
    )

    strategy.activate()

    # 진입 가격
    entry_price = Decimal("50000000")
    strategy.set_initial_price(entry_price)

    # 테스트 시나리오
    scenarios = [
        ("1% 상승", Decimal("50500000")),   # 활성화 안됨
        ("3% 상승", Decimal("51500000")),   # 활성화
        ("8% 상승", Decimal("54000000")),   # 최고가 갱신
        ("5% 하락 (최고가 대비)", Decimal("51300000")),  # 트레일링 스탑 발동
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
        stop_price = strategy.get_current_stop_price()

        print(f"\n{scenario_name}")
        print(f"  현재가: {current_price:,.0f} (수익률: {profit_pct:.2f}%)")
        print(f"  최고가: {strategy.highest_price:,.0f}")
        print(f"  스탑가: {stop_price:,.0f}")
        print(f"  시그널: {signal_data.signal.value.upper()}")
        print(f"  이유: {signal_data.metadata.get('reason', 'N/A')}")
