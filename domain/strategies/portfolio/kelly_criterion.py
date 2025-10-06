"""
BTS 켈리 기준 포트폴리오 전략

승률과 손익비 기반 최적 포지션 크기 계산
"""
from typing import Dict, List, Optional
from decimal import Decimal

from domain.strategies.portfolio.base_portfolio import (
    BasePortfolioStrategy,
    Position,
    AllocationResult
)
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class KellyCriterionPortfolio(BasePortfolioStrategy):
    """
    켈리 기준 포트폴리오

    Kelly Criterion = (승률 × 평균수익 - (1 - 승률) × 평균손실) / 평균수익

    최적 베팅 비율을 수학적으로 계산
    """

    def __init__(
        self,
        id: int,
        name: str = "Kelly Criterion Portfolio",
        description: str = "켈리 기준 포트폴리오",
        parameters: Optional[Dict] = None,
    ):
        default_params = {
            "min_allocation": 10000,
            "max_positions": 10,
            "reserve_ratio": 0.2,  # 켈리는 공격적이므로 예비금 더 확보
            "rebalance_threshold": 0.15,
            # 켈리 계산용
            "default_win_rate": 0.55,  # 기본 승률 55%
            "default_avg_win": 0.10,   # 기본 평균 수익 10%
            "default_avg_loss": 0.05,  # 기본 평균 손실 5%
            "kelly_fraction": 0.5,     # 켈리 비율 조정 (풀 켈리는 위험)
            "max_kelly": 0.25,         # 최대 켈리 비율 제한
        }
        if parameters:
            default_params.update(parameters)

        super().__init__(id, name, description, default_params)

        self.rebalance_threshold = Decimal(str(self.parameters["rebalance_threshold"]))
        self.default_win_rate = Decimal(str(self.parameters["default_win_rate"]))
        self.default_avg_win = Decimal(str(self.parameters["default_avg_win"]))
        self.default_avg_loss = Decimal(str(self.parameters["default_avg_loss"]))
        self.kelly_fraction = Decimal(str(self.parameters["kelly_fraction"]))
        self.max_kelly = Decimal(str(self.parameters["max_kelly"]))

        # 종목별 통계 (외부에서 업데이트 필요)
        self.symbol_stats: Dict[str, Dict] = {}

    def calculate_allocation(
        self,
        total_balance: Decimal,
        selected_symbols: List[str],
        current_positions: Optional[Dict[str, Position]] = None,
        market_data: Optional[Dict[str, List[OHLCV]]] = None
    ) -> AllocationResult:
        """
        켈리 기준 배분 계산

        Args:
            total_balance: 총 사용 가능 자금
            selected_symbols: 선정된 심볼 리스트
            current_positions: 현재 보유 포지션
            market_data: 시장 데이터

        Returns:
            AllocationResult: 배분 결과
        """
        if not selected_symbols:
            logger.warning("선정된 심볼이 없습니다")
            return AllocationResult(
                allocations={},
                weights={},
                metadata={"reason": "선정된 심볼 없음"}
            )

        # 예비 자금 제외
        reserve = total_balance * self.reserve_ratio
        available = total_balance - reserve

        # 각 종목의 켈리 비율 계산
        kelly_ratios = {}
        for symbol in selected_symbols:
            kelly = self._calculate_kelly(symbol)
            kelly_ratios[symbol] = kelly

        # 켈리 합계
        total_kelly = sum(kelly_ratios.values())

        if total_kelly <= 0:
            logger.warning("유효한 켈리 비율이 없습니다. 균등 배분으로 대체")
            # 균등 배분으로 대체
            kelly_ratios = {
                symbol: Decimal("1") / len(selected_symbols)
                for symbol in selected_symbols
            }
            total_kelly = Decimal("1")

        # 켈리 비율 정규화 및 배분
        allocations = {}
        for symbol, kelly in kelly_ratios.items():
            if kelly > 0:
                weight = kelly / total_kelly
                allocations[symbol] = available * weight

        # 제약 조건 적용
        allocations = self.apply_constraints(total_balance, allocations)

        # 비중 계산
        weights = self.calculate_weights(allocations)

        logger.info(
            f"켈리 기준 배분 완료 | 종목 수: {len(allocations)} | "
            f"켈리 분수: {self.kelly_fraction}"
        )

        return AllocationResult(
            allocations=allocations,
            weights=weights,
            metadata={
                "strategy": "kelly_criterion",
                "num_positions": len(allocations),
                "total_allocated": float(sum(allocations.values())),
                "reserve": float(reserve),
                "kelly_fraction": float(self.kelly_fraction),
                "kelly_ratios": {k: float(v) for k, v in kelly_ratios.items()}
            }
        )

    def _calculate_kelly(self, symbol: str) -> Decimal:
        """
        개별 종목의 켈리 비율 계산

        Kelly % = (W × R - L) / R
        W = 승률
        R = 평균 수익
        L = 1 - W (패율) × 평균 손실

        Args:
            symbol: 거래 심볼

        Returns:
            Decimal: 켈리 비율 (0-1)
        """
        # 종목 통계 조회 (없으면 기본값 사용)
        if symbol in self.symbol_stats:
            stats = self.symbol_stats[symbol]
            win_rate = Decimal(str(stats.get("win_rate", self.default_win_rate)))
            avg_win = Decimal(str(stats.get("avg_win", self.default_avg_win)))
            avg_loss = Decimal(str(stats.get("avg_loss", self.default_avg_loss)))
        else:
            win_rate = self.default_win_rate
            avg_win = self.default_avg_win
            avg_loss = self.default_avg_loss

        # 켈리 공식
        # kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        if avg_win <= 0:
            logger.warning(f"{symbol}: 평균 수익이 0 이하입니다")
            return Decimal("0")

        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        # 음수 켈리는 0으로
        if kelly < 0:
            logger.warning(f"{symbol}: 켈리 비율이 음수입니다 (기댓값 음수)")
            return Decimal("0")

        # 켈리 분수 적용 (풀 켈리는 너무 공격적)
        kelly = kelly * self.kelly_fraction

        # 최대 켈리 제한
        kelly = min(kelly, self.max_kelly)

        return kelly

    def update_symbol_stats(
        self,
        symbol: str,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ):
        """
        종목별 통계 업데이트

        Args:
            symbol: 거래 심볼
            win_rate: 승률 (0-1)
            avg_win: 평균 수익률 (예: 0.10 = 10%)
            avg_loss: 평균 손실률 (예: 0.05 = 5%)
        """
        self.symbol_stats[symbol] = {
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "updated_at": datetime.now()
        }

        logger.info(
            f"{symbol} 통계 업데이트 | 승률: {win_rate:.2%} | "
            f"평균수익: {avg_win:.2%} | 평균손실: {avg_loss:.2%}"
        )

    def should_rebalance(
        self,
        current_positions: Dict[str, Position],
        target_allocations: Dict[str, Decimal]
    ) -> bool:
        """리밸런싱 필요 여부 판단"""
        if not current_positions or not target_allocations:
            return False

        # 현재 비중 계산
        total_value = self.calculate_position_value(current_positions)
        current_weights = {
            symbol: pos.value / total_value
            for symbol, pos in current_positions.items()
        }

        # 목표 비중 계산
        target_weights = self.calculate_weights(target_allocations)

        # 차이 계산
        divergence = self.calculate_divergence(current_weights, target_weights)

        needs_rebalance = divergence > self.rebalance_threshold

        if needs_rebalance:
            logger.info(
                f"리밸런싱 필요 | 비중 차이: {divergence:.2%} > "
                f"임계값: {self.rebalance_threshold:.2%}"
            )

        return needs_rebalance

    def validate_parameters(self) -> bool:
        """파라미터 검증"""
        errors = []

        try:
            super().validate_parameters()
        except Exception as e:
            errors.append(str(e))

        if not (0 < self.default_win_rate < 1):
            errors.append("default_win_rate는 0과 1 사이여야 합니다")

        if self.default_avg_win <= 0:
            errors.append("default_avg_win은 0보다 커야 합니다")

        if self.default_avg_loss <= 0:
            errors.append("default_avg_loss는 0보다 커야 합니다")

        if not (0 < self.kelly_fraction <= 1):
            errors.append("kelly_fraction은 0과 1 사이여야 합니다")

        if not (0 < self.max_kelly <= 1):
            errors.append("max_kelly는 0과 1 사이여야 합니다")

        if errors:
            from core.exceptions import StrategyError
            raise StrategyError(
                "켈리 기준 포트폴리오 파라미터 검증 실패",
                {"errors": errors}
            )

        return True

    def __repr__(self) -> str:
        return (
            f"<KellyCriterionPortfolio(name={self.name}, "
            f"kelly_fraction={self.kelly_fraction}, max_kelly={self.max_kelly})>"
        )


if __name__ == "__main__":
    print("=== 켈리 기준 포트폴리오 테스트 ===")

    from datetime import datetime

    # 포트폴리오 생성
    portfolio = KellyCriterionPortfolio(
        id=1,
        parameters={
            "kelly_fraction": 0.5,  # 하프 켈리
            "max_kelly": 0.25,
            "max_positions": 5,
            "reserve_ratio": 0.2,
        }
    )

    portfolio.validate_parameters()

    # 종목별 통계 업데이트
    portfolio.update_symbol_stats(
        "KRW-BTC",
        win_rate=0.60,  # 60% 승률
        avg_win=0.15,   # 평균 15% 수익
        avg_loss=0.08   # 평균 8% 손실
    )

    portfolio.update_symbol_stats(
        "KRW-ETH",
        win_rate=0.55,
        avg_win=0.12,
        avg_loss=0.07
    )

    portfolio.update_symbol_stats(
        "KRW-XRP",
        win_rate=0.50,
        avg_win=0.10,
        avg_loss=0.06
    )

    # 배분 계산
    total_balance = Decimal("10000000")  # 1천만원
    selected_symbols = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]

    result = portfolio.calculate_allocation(
        total_balance=total_balance,
        selected_symbols=selected_symbols
    )

    print(f"\n총 자금: {total_balance:,.0f} KRW")
    print(f"\n배분 결과:")

    for symbol in selected_symbols:
        amount = result.get_allocation(symbol)
        weight = result.get_weight(symbol)
        kelly_ratio = result.metadata["kelly_ratios"].get(symbol, 0)

        stats = portfolio.symbol_stats.get(symbol, {})
        print(f"\n{symbol}:")
        print(f"  통계: 승률 {stats.get('win_rate', 0):.2%}, "
              f"평균수익 {stats.get('avg_win', 0):.2%}, "
              f"평균손실 {stats.get('avg_loss', 0):.2%}")
        print(f"  켈리 비율: {kelly_ratio:.4f}")
        print(f"  배분: {amount:,.0f} KRW ({weight:.2%})")
