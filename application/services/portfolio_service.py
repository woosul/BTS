"""
BTS Portfolio Service

포트폴리오 전략 관리 및 실행 서비스
"""
from typing import List, Optional, Dict, Type
from decimal import Decimal
from sqlalchemy.orm import Session
import json

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import StrategyORM
from infrastructure.exchanges.upbit_client import UpbitClient
from domain.strategies.portfolio.base_portfolio import (
    BasePortfolioStrategy,
    Position,
    AllocationResult
)
from domain.strategies.portfolio.equal_weight import EqualWeightPortfolio
from domain.strategies.portfolio.proportional_weight import ProportionalWeightPortfolio
from domain.strategies.portfolio.kelly_criterion import KellyCriterionPortfolio
from domain.strategies.portfolio.risk_parity import RiskParityPortfolio
from domain.strategies.portfolio.dynamic_allocation import DynamicAllocationPortfolio
from core.models import StrategyResponse, OHLCV
from core.enums import StrategyStatus, TimeFrame
from core.exceptions import (
    StrategyNotFoundError,
    StrategyInitializationError,
    StrategyExecutionError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioService:
    """
    포트폴리오 전략 서비스

    자금 배분 및 리밸런싱 관리
    """

    # 사용 가능한 포트폴리오 전략 클래스 매핑
    PORTFOLIO_STRATEGY_CLASSES: Dict[str, Type[BasePortfolioStrategy]] = {
        "equal_weight": EqualWeightPortfolio,
        "proportional_weight": ProportionalWeightPortfolio,
        "kelly_criterion": KellyCriterionPortfolio,
        "risk_parity": RiskParityPortfolio,
        "dynamic_allocation": DynamicAllocationPortfolio,
    }

    def __init__(self, db: Session, exchange: Optional[UpbitClient] = None):
        self.db = db
        self.strategy_repo = BaseRepository(StrategyORM, db)
        self.exchange = exchange or UpbitClient()

        # 활성 전략 인스턴스 캐시
        self._active_strategies: Dict[int, BasePortfolioStrategy] = {}

    def create_portfolio_strategy(
        self,
        strategy_type: str,
        name: str,
        description: str = "",
        parameters: Optional[Dict] = None
    ) -> StrategyResponse:
        """
        포트폴리오 전략 생성

        Args:
            strategy_type: 전략 타입
            name: 전략 이름
            description: 전략 설명
            parameters: 전략 파라미터

        Returns:
            StrategyResponse: 생성된 전략
        """
        if strategy_type not in self.PORTFOLIO_STRATEGY_CLASSES:
            raise StrategyInitializationError(
                f"지원하지 않는 전략 타입: {strategy_type}",
                {"available": list(self.PORTFOLIO_STRATEGY_CLASSES.keys())}
            )

        # 파라미터를 JSON 문자열로 변환
        parameters_json = json.dumps(parameters or {})

        # DB에 저장
        strategy_orm = self.strategy_repo.create(
            name=name,
            description=description,
            timeframe=TimeFrame.DAY_1,  # 포트폴리오는 일봉 기준
            parameters=parameters_json,
            status=StrategyStatus.INACTIVE
        )

        logger.info(f"포트폴리오 전략 생성: {strategy_orm.name} (ID: {strategy_orm.id})")
        return self._to_response(strategy_orm, strategy_type)

    def calculate_allocation(
        self,
        strategy_id: int,
        strategy_type: str,
        total_balance: Decimal,
        selected_symbols: List[str],
        current_positions: Optional[Dict[str, Dict]] = None,
        fetch_market_data: bool = True
    ) -> AllocationResult:
        """
        자금 배분 계산

        Args:
            strategy_id: 전략 ID
            strategy_type: 전략 타입
            total_balance: 총 자금
            selected_symbols: 선정된 심볼 리스트
            current_positions: 현재 포지션 (dict)
            fetch_market_data: 시장 데이터 자동 조회 여부

        Returns:
            AllocationResult: 배분 결과
        """
        # 전략 인스턴스 가져오기
        if strategy_id not in self._active_strategies:
            strategy_orm = self.strategy_repo.get_by_id(strategy_id)
            if not strategy_orm:
                raise StrategyNotFoundError(f"전략을 찾을 수 없습니다: {strategy_id}")

            strategy_instance = self._create_strategy_instance(
                strategy_type,
                strategy_orm.id,
                strategy_orm.name,
                strategy_orm.description,
                json.loads(strategy_orm.parameters)
            )
            self._active_strategies[strategy_id] = strategy_instance
        else:
            strategy_instance = self._active_strategies[strategy_id]

        # Position 객체로 변환
        positions_dict = None
        if current_positions:
            positions_dict = {
                symbol: Position(
                    symbol=symbol,
                    quantity=Decimal(str(pos["quantity"])),
                    entry_price=Decimal(str(pos["entry_price"])),
                    current_price=Decimal(str(pos["current_price"])),
                    value=Decimal(str(pos["value"]))
                )
                for symbol, pos in current_positions.items()
            }

        # 시장 데이터 조회
        market_data = None
        if fetch_market_data:
            market_data = self._fetch_market_data(selected_symbols)

        # 배분 계산
        try:
            result = strategy_instance.calculate_allocation(
                total_balance=total_balance,
                selected_symbols=selected_symbols,
                current_positions=positions_dict,
                market_data=market_data
            )

            logger.info(
                f"배분 완료 | 전략: {strategy_instance.name} | "
                f"종목 수: {len(result.allocations)}"
            )

            return result

        except Exception as e:
            logger.error(f"배분 계산 실패: {e}")
            raise StrategyExecutionError(f"배분 계산 실패: {str(e)}")

    def check_rebalancing(
        self,
        strategy_id: int,
        strategy_type: str,
        current_positions: Dict[str, Dict],
        target_allocations: Dict[str, Decimal]
    ) -> bool:
        """
        리밸런싱 필요 여부 확인

        Args:
            strategy_id: 전략 ID
            strategy_type: 전략 타입
            current_positions: 현재 포지션
            target_allocations: 목표 배분

        Returns:
            bool: 리밸런싱 필요 여부
        """
        # 전략 인스턴스 가져오기
        if strategy_id not in self._active_strategies:
            strategy_orm = self.strategy_repo.get_by_id(strategy_id)
            if not strategy_orm:
                raise StrategyNotFoundError(f"전략을 찾을 수 없습니다: {strategy_id}")

            strategy_instance = self._create_strategy_instance(
                strategy_type,
                strategy_orm.id,
                strategy_orm.name,
                strategy_orm.description,
                json.loads(strategy_orm.parameters)
            )
            self._active_strategies[strategy_id] = strategy_instance
        else:
            strategy_instance = self._active_strategies[strategy_id]

        # Position 객체로 변환
        positions_dict = {
            symbol: Position(
                symbol=symbol,
                quantity=Decimal(str(pos["quantity"])),
                entry_price=Decimal(str(pos["entry_price"])),
                current_price=Decimal(str(pos["current_price"])),
                value=Decimal(str(pos["value"]))
            )
            for symbol, pos in current_positions.items()
        }

        return strategy_instance.should_rebalance(positions_dict, target_allocations)

    def get_available_strategies(self) -> List[Dict]:
        """사용 가능한 포트폴리오 전략 목록"""
        return [
            {
                "type": "equal_weight",
                "name": "Equal Weight Portfolio",
                "description": "균등 배분 포트폴리오",
                "parameters": {
                    "max_positions": 10,
                    "reserve_ratio": 0.1,
                    "rebalance_threshold": 0.05,
                }
            },
            {
                "type": "proportional_weight",
                "name": "Proportional Weight Portfolio",
                "description": "비율 배분 포트폴리오",
                "parameters": {
                    "weight_mode": "rank",
                    "rank_weights": [0.30, 0.25, 0.20, 0.15, 0.10],
                    "max_positions": 5,
                }
            },
            {
                "type": "kelly_criterion",
                "name": "Kelly Criterion Portfolio",
                "description": "켈리 기준 포트폴리오",
                "parameters": {
                    "kelly_fraction": 0.5,
                    "max_kelly": 0.25,
                    "default_win_rate": 0.55,
                    "default_avg_win": 0.10,
                    "default_avg_loss": 0.05,
                }
            },
            {
                "type": "risk_parity",
                "name": "Risk Parity Portfolio",
                "description": "리스크 패리티 포트폴리오",
                "parameters": {
                    "volatility_period": 30,
                    "max_positions": 10,
                }
            },
            {
                "type": "dynamic_allocation",
                "name": "Dynamic Allocation Portfolio",
                "description": "동적 배분 포트폴리오",
                "parameters": {
                    "base_reserve_ratio": 0.1,
                    "min_reserve_ratio": 0.05,
                    "max_reserve_ratio": 0.5,
                    "volatility_period": 30,
                }
            },
        ]

    # ===== Private Methods =====
    def _create_strategy_instance(
        self,
        strategy_type: str,
        strategy_id: int,
        name: str,
        description: str,
        parameters: Dict
    ) -> BasePortfolioStrategy:
        """전략 인스턴스 생성"""
        if strategy_type not in self.PORTFOLIO_STRATEGY_CLASSES:
            raise StrategyInitializationError(
                f"지원하지 않는 전략 타입: {strategy_type}"
            )

        strategy_class = self.PORTFOLIO_STRATEGY_CLASSES[strategy_type]

        try:
            return strategy_class(
                id=strategy_id,
                name=name,
                description=description,
                parameters=parameters
            )
        except Exception as e:
            raise StrategyInitializationError(
                f"전략 인스턴스 생성 실패: {str(e)}"
            )

    def _fetch_market_data(
        self,
        symbols: List[str],
        count: int = 60
    ) -> Dict[str, List[OHLCV]]:
        """시장 데이터 조회"""
        market_data = {}

        for symbol in symbols:
            try:
                candles = self.exchange.get_candles(
                    symbol=symbol,
                    interval="days",
                    count=count
                )

                ohlcv_data = []
                for candle in candles:
                    ohlcv_data.append(OHLCV(
                        timestamp=candle["candle_date_time_kst"],
                        open=Decimal(str(candle["opening_price"])),
                        high=Decimal(str(candle["high_price"])),
                        low=Decimal(str(candle["low_price"])),
                        close=Decimal(str(candle["trade_price"])),
                        volume=Decimal(str(candle["candle_acc_trade_volume"]))
                    ))

                market_data[symbol] = ohlcv_data

            except Exception as e:
                logger.warning(f"{symbol} 데이터 조회 실패: {e}")

        return market_data

    def _to_response(
        self,
        strategy_orm: StrategyORM,
        strategy_type: str = None
    ) -> StrategyResponse:
        """ORM을 Response 모델로 변환"""
        return StrategyResponse(
            id=strategy_orm.id,
            name=strategy_orm.name,
            description=strategy_orm.description,
            timeframe=strategy_orm.timeframe,
            parameters=json.loads(strategy_orm.parameters),
            status=strategy_orm.status,
            created_at=strategy_orm.created_at,
            updated_at=strategy_orm.updated_at,
            metadata={"strategy_type": strategy_type} if strategy_type else {}
        )


if __name__ == "__main__":
    print("=== Portfolio Service 테스트 ===")
    print("사용 가능한 포트폴리오 전략:")

    service = PortfolioService(db=None, exchange=None)  # type: ignore

    for strategy in service.get_available_strategies():
        print(f"\n- {strategy['name']} ({strategy['type']})")
        print(f"  설명: {strategy['description']}")
        print(f"  파라미터: {strategy['parameters']}")
