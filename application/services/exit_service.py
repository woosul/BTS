"""
BTS Exit Service

매도 전략 관리 및 실행 서비스
"""
from typing import List, Optional, Dict, Type
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
import json

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import StrategyORM
from infrastructure.exchanges.upbit_client import UpbitClient
from domain.strategies.exit.base_exit import BaseExitStrategy
from domain.strategies.exit.fixed_target_exit import FixedTargetExitStrategy
from domain.strategies.exit.ladder_exit import LadderExitStrategy
from domain.strategies.exit.trailing_stop_exit import TrailingStopExitStrategy
from domain.strategies.exit.atr_stop_exit import ATRStopExitStrategy
from domain.strategies.exit.multi_condition_exit import MultiConditionExitStrategy
from domain.strategies.exit.hybrid_exit import HybridExitStrategy
from core.models import (
    StrategyResponse,
    StrategySignalData,
    OHLCV
)
from core.enums import StrategyStatus, TimeFrame, StrategySignal
from core.exceptions import (
    StrategyNotFoundError,
    StrategyInitializationError,
    StrategyExecutionError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ExitService:
    """
    매도 전략 서비스

    매도 전략 생성, 활성화, 시그널 생성 등 매도 관련 로직
    """

    # 사용 가능한 매도 전략 클래스 매핑
    EXIT_STRATEGY_CLASSES: Dict[str, Type[BaseExitStrategy]] = {
        "fixed_target_exit": FixedTargetExitStrategy,
        "ladder_exit": LadderExitStrategy,
        "trailing_stop_exit": TrailingStopExitStrategy,
        "atr_stop_exit": ATRStopExitStrategy,
        "multi_condition_exit": MultiConditionExitStrategy,
        "hybrid_exit": HybridExitStrategy,
    }

    def __init__(self, db: Session, exchange: Optional[UpbitClient] = None):
        self.db = db
        self.strategy_repo = BaseRepository(StrategyORM, db)
        self.exchange = exchange or UpbitClient()

        # 활성 전략 인스턴스 캐시
        self._active_strategies: Dict[int, BaseExitStrategy] = {}

    def create_exit_strategy(
        self,
        strategy_type: str,
        name: str,
        description: str = "",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None
    ) -> StrategyResponse:
        """
        매도 전략 생성

        Args:
            strategy_type: 전략 타입
            name: 전략 이름
            description: 전략 설명
            timeframe: 시간프레임
            parameters: 전략 파라미터

        Returns:
            StrategyResponse: 생성된 전략

        Raises:
            StrategyInitializationError: 전략 초기화 실패
        """
        if strategy_type not in self.EXIT_STRATEGY_CLASSES:
            raise StrategyInitializationError(
                f"지원하지 않는 전략 타입: {strategy_type}",
                {"available": list(self.EXIT_STRATEGY_CLASSES.keys())}
            )

        # 파라미터를 JSON 문자열로 변환
        parameters_json = json.dumps(parameters or {})

        # DB에 저장
        strategy_orm = self.strategy_repo.create(
            name=name,
            description=description,
            timeframe=timeframe,
            parameters=parameters_json,
            status=StrategyStatus.INACTIVE
        )

        logger.info(f"매도 전략 생성: {strategy_orm.name} (ID: {strategy_orm.id})")
        return self._to_response(strategy_orm, strategy_type)

    def get_exit_strategy(self, strategy_id: int) -> StrategyResponse:
        """매도 전략 조회"""
        strategy_orm = self.strategy_repo.get_by_id(strategy_id)
        if not strategy_orm:
            raise StrategyNotFoundError(f"전략을 찾을 수 없습니다: {strategy_id}")

        return self._to_response(strategy_orm)

    def list_exit_strategies(self) -> List[StrategyResponse]:
        """모든 매도 전략 목록 조회"""
        strategies = self.strategy_repo.get_all()
        return [self._to_response(s) for s in strategies]

    def activate_strategy(self, strategy_id: int, strategy_type: str) -> StrategyResponse:
        """매도 전략 활성화"""
        strategy_orm = self.strategy_repo.get_by_id(strategy_id)
        if not strategy_orm:
            raise StrategyNotFoundError(f"전략을 찾을 수 없습니다: {strategy_id}")

        # 전략 인스턴스 생성 및 활성화
        strategy_instance = self._create_strategy_instance(
            strategy_type,
            strategy_orm.id,
            strategy_orm.name,
            strategy_orm.description,
            strategy_orm.timeframe,
            json.loads(strategy_orm.parameters)
        )

        strategy_instance.activate()

        # 캐시에 저장
        self._active_strategies[strategy_id] = strategy_instance

        # DB 상태 업데이트
        self.strategy_repo.update(
            strategy_id,
            status=StrategyStatus.ACTIVE
        )

        logger.info(f"매도 전략 활성화: {strategy_orm.name}")
        return self._to_response(strategy_orm, strategy_type)

    def deactivate_strategy(self, strategy_id: int) -> StrategyResponse:
        """매도 전략 비활성화"""
        strategy_orm = self.strategy_repo.get_by_id(strategy_id)
        if not strategy_orm:
            raise StrategyNotFoundError(f"전략을 찾을 수 없습니다: {strategy_id}")

        # 캐시에서 제거
        if strategy_id in self._active_strategies:
            self._active_strategies[strategy_id].deactivate()
            del self._active_strategies[strategy_id]

        # DB 상태 업데이트
        self.strategy_repo.update(
            strategy_id,
            status=StrategyStatus.INACTIVE
        )

        logger.info(f"매도 전략 비활성화: {strategy_orm.name}")
        return self._to_response(strategy_orm)

    def evaluate_exit(
        self,
        strategy_id: int,
        strategy_type: str,
        symbol: str,
        entry_price: Decimal,
        holding_period: int = 0,
        count: int = 200
    ) -> StrategySignalData:
        """
        매도 평가

        Args:
            strategy_id: 전략 ID
            strategy_type: 전략 타입
            symbol: 거래 심볼
            entry_price: 매수 가격
            holding_period: 보유 기간 (캔들 개수)
            count: 가져올 캔들 개수

        Returns:
            StrategySignalData: 시그널 데이터

        Raises:
            StrategyExecutionError: 시그널 생성 실패
        """
        # 전략 인스턴스 가져오기 또는 생성
        if strategy_id not in self._active_strategies:
            strategy_orm = self.strategy_repo.get_by_id(strategy_id)
            if not strategy_orm:
                raise StrategyNotFoundError(f"전략을 찾을 수 없습니다: {strategy_id}")

            strategy_instance = self._create_strategy_instance(
                strategy_type,
                strategy_orm.id,
                strategy_orm.name,
                strategy_orm.description,
                strategy_orm.timeframe,
                json.loads(strategy_orm.parameters)
            )
            self._active_strategies[strategy_id] = strategy_instance
        else:
            strategy_instance = self._active_strategies[strategy_id]

        # OHLCV 데이터 가져오기
        ohlcv_data = self._fetch_ohlcv_data(
            symbol,
            strategy_instance.timeframe,
            count
        )

        # 매도 평가
        try:
            signal_data = strategy_instance.evaluate_exit(
                symbol=symbol,
                entry_price=entry_price,
                ohlcv_data=ohlcv_data,
                holding_period=holding_period
            )

            logger.info(
                f"매도 평가 | {symbol} | 진입가: {entry_price:,.0f} | "
                f"{signal_data.signal.value.upper()} (확신도: {signal_data.confidence:.2%})"
            )

            return signal_data

        except Exception as e:
            logger.error(f"매도 평가 실패: {e}")
            raise StrategyExecutionError(f"매도 평가 실패: {str(e)}")

    def batch_evaluate_exits(
        self,
        strategy_id: int,
        strategy_type: str,
        positions: List[Dict],  # [{"symbol": "KRW-BTC", "entry_price": 50000000, "holding_period": 10}]
        count: int = 200
    ) -> Dict[str, StrategySignalData]:
        """
        여러 포지션에 대해 매도 평가 일괄 수행

        Args:
            strategy_id: 전략 ID
            strategy_type: 전략 타입
            positions: 포지션 리스트
            count: 가져올 캔들 개수

        Returns:
            Dict[str, StrategySignalData]: 심볼별 시그널 데이터
        """
        results = {}

        for position in positions:
            symbol = position["symbol"]
            entry_price = Decimal(str(position["entry_price"]))
            holding_period = position.get("holding_period", 0)

            try:
                signal_data = self.evaluate_exit(
                    strategy_id,
                    strategy_type,
                    symbol,
                    entry_price,
                    holding_period,
                    count
                )
                results[symbol] = signal_data

            except Exception as e:
                logger.error(f"{symbol} 매도 평가 실패: {e}")
                # 실패한 심볼은 HOLD로 처리
                results[symbol] = StrategySignalData(
                    signal=StrategySignal.HOLD,
                    confidence=Decimal("0"),
                    price=Decimal("0"),
                    timestamp=datetime.now(),
                    indicators={},
                    metadata={"error": str(e)}
                )

        return results

    def reset_strategy_state(self, strategy_id: int):
        """
        전략 상태 초기화 (새 포지션 시작 시)

        Args:
            strategy_id: 전략 ID
        """
        if strategy_id in self._active_strategies:
            strategy = self._active_strategies[strategy_id]
            if hasattr(strategy, 'reset_execution_state'):
                strategy.reset_execution_state()
                logger.info(f"전략 상태 초기화: {strategy.name}")

    def get_strategy_statistics(self, strategy_id: int) -> Dict:
        """전략 통계 조회"""
        if strategy_id in self._active_strategies:
            return self._active_strategies[strategy_id].get_statistics()
        else:
            return {"error": "전략이 활성화되지 않았습니다"}

    # ===== Private Methods =====
    def _create_strategy_instance(
        self,
        strategy_type: str,
        strategy_id: int,
        name: str,
        description: str,
        timeframe: TimeFrame,
        parameters: Dict
    ) -> BaseExitStrategy:
        """전략 인스턴스 생성"""
        if strategy_type not in self.EXIT_STRATEGY_CLASSES:
            raise StrategyInitializationError(
                f"지원하지 않는 전략 타입: {strategy_type}"
            )

        strategy_class = self.EXIT_STRATEGY_CLASSES[strategy_type]

        try:
            return strategy_class(
                id=strategy_id,
                name=name,
                description=description,
                timeframe=timeframe,
                parameters=parameters
            )
        except Exception as e:
            raise StrategyInitializationError(
                f"전략 인스턴스 생성 실패: {str(e)}"
            )

    def _fetch_ohlcv_data(
        self,
        symbol: str,
        timeframe: TimeFrame,
        count: int
    ) -> List[OHLCV]:
        """거래소에서 OHLCV 데이터 가져오기"""
        try:
            candles = self.exchange.get_candles(
                symbol=symbol,
                interval=timeframe.value,
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

            return ohlcv_data

        except Exception as e:
            logger.error(f"OHLCV 데이터 조회 실패: {e}")
            raise StrategyExecutionError(f"시장 데이터 조회 실패: {str(e)}")

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

    def get_available_strategies(self) -> List[Dict]:
        """
        사용 가능한 매도 전략 목록

        Returns:
            List[Dict]: 전략 타입 및 설명
        """
        return [
            {
                "type": "fixed_target_exit",
                "name": "Fixed Target Exit",
                "description": "고정 목표가 매도 전략",
                "parameters": {
                    "target_profit_pct": 10.0,
                    "stop_loss_pct": -5.0,
                }
            },
            {
                "type": "ladder_exit",
                "name": "Ladder Exit",
                "description": "단계별 익절 매도 전략",
                "parameters": {
                    "profit_levels": [
                        {"profit_pct": 5.0, "sell_ratio": 0.33},
                        {"profit_pct": 10.0, "sell_ratio": 0.33},
                        {"profit_pct": 20.0, "sell_ratio": 0.34}
                    ],
                    "stop_loss_pct": -5.0,
                }
            },
            {
                "type": "trailing_stop_exit",
                "name": "Trailing Stop Exit",
                "description": "트레일링 스탑 매도 전략",
                "parameters": {
                    "trailing_pct": 3.0,
                    "activation_profit": 2.0,
                    "stop_loss_pct": -5.0,
                }
            },
            {
                "type": "atr_stop_exit",
                "name": "ATR Stop Exit",
                "description": "ATR 기반 동적 손절 전략",
                "parameters": {
                    "atr_period": 14,
                    "atr_multiplier": 2.0,
                    "target_profit_pct": 15.0,
                    "min_stop_loss_pct": -3.0,
                    "max_stop_loss_pct": -10.0,
                }
            },
            {
                "type": "multi_condition_exit",
                "name": "Multi-Condition Exit",
                "description": "복합 조건 매도 전략",
                "parameters": {
                    "use_profit_target": True,
                    "target_profit_pct": 10.0,
                    "use_stop_loss": True,
                    "stop_loss_pct": -5.0,
                    "use_rsi": True,
                    "use_time_based": True,
                    "max_holding_periods": 48,
                    "use_ma_cross": True,
                }
            },
            {
                "type": "hybrid_exit",
                "name": "Hybrid Exit",
                "description": "복합 전략 가중 평균 매도",
                "parameters": {
                    "strategy_weights": {
                        "fixed_target": 0.40,
                        "trailing_stop": 0.35,
                        "rsi": 0.15,
                        "time_based": 0.10,
                    },
                    "sell_threshold": 0.75,
                }
            },
        ]


if __name__ == "__main__":
    print("=== Exit Service 테스트 ===")
    print("사용 가능한 매도 전략:")

    # DB 세션 없이 테스트 (전략 목록만)
    service = ExitService(db=None, exchange=None)  # type: ignore

    for strategy in service.get_available_strategies():
        print(f"\n- {strategy['name']} ({strategy['type']})")
        print(f"  설명: {strategy['description']}")
        print(f"  파라미터: {strategy['parameters']}")
