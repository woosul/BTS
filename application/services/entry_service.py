"""
BTS Entry Service

매수 전략 관리 및 실행 서비스
"""
from typing import List, Optional, Dict, Type
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
import json

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import StrategyORM
from infrastructure.exchanges.upbit_client import UpbitClient
from domain.strategies.entry.base_entry import BaseEntryStrategy
from domain.strategies.entry.macd_entry import MACDEntryStrategy
from domain.strategies.entry.stochastic_entry import StochasticEntryStrategy
from domain.strategies.entry.multi_indicator_entry import MultiIndicatorEntryStrategy
from domain.strategies.entry.hybrid_entry import HybridEntryStrategy
from core.models import (
    StrategyCreate,
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


class EntryService:
    """
    매수 전략 서비스

    매수 전략 생성, 활성화, 시그널 생성 등 매수 관련 로직
    """

    # 사용 가능한 매수 전략 클래스 매핑
    ENTRY_STRATEGY_CLASSES: Dict[str, Type[BaseEntryStrategy]] = {
        "macd_entry": MACDEntryStrategy,
        "stochastic_entry": StochasticEntryStrategy,
        "multi_indicator_entry": MultiIndicatorEntryStrategy,
        "hybrid_entry": HybridEntryStrategy,
    }

    def __init__(self, db: Session, exchange: Optional[UpbitClient] = None):
        self.db = db
        self.strategy_repo = BaseRepository(StrategyORM, db)
        self.exchange = exchange or UpbitClient()

        # 활성 전략 인스턴스 캐시
        self._active_strategies: Dict[int, BaseEntryStrategy] = {}

    def create_entry_strategy(
        self,
        strategy_type: str,
        name: str,
        description: str = "",
        timeframe: TimeFrame = TimeFrame.HOUR_1,
        parameters: Optional[Dict] = None
    ) -> StrategyResponse:
        """
        매수 전략 생성

        Args:
            strategy_type: 전략 타입 (macd_entry, stochastic_entry 등)
            name: 전략 이름
            description: 전략 설명
            timeframe: 시간프레임
            parameters: 전략 파라미터

        Returns:
            StrategyResponse: 생성된 전략

        Raises:
            StrategyInitializationError: 전략 초기화 실패
        """
        if strategy_type not in self.ENTRY_STRATEGY_CLASSES:
            raise StrategyInitializationError(
                f"지원하지 않는 전략 타입: {strategy_type}",
                {"available": list(self.ENTRY_STRATEGY_CLASSES.keys())}
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

        logger.info(f"매수 전략 생성: {strategy_orm.name} (ID: {strategy_orm.id})")
        return self._to_response(strategy_orm, strategy_type)

    def get_entry_strategy(self, strategy_id: int) -> StrategyResponse:
        """
        매수 전략 조회

        Args:
            strategy_id: 전략 ID

        Returns:
            StrategyResponse: 전략 정보

        Raises:
            StrategyNotFoundError: 전략을 찾을 수 없음
        """
        strategy_orm = self.strategy_repo.get_by_id(strategy_id)
        if not strategy_orm:
            raise StrategyNotFoundError(f"전략을 찾을 수 없습니다: {strategy_id}")

        return self._to_response(strategy_orm)

    def list_entry_strategies(self) -> List[StrategyResponse]:
        """
        모든 매수 전략 목록 조회

        Returns:
            List[StrategyResponse]: 전략 목록
        """
        strategies = self.strategy_repo.get_all()
        return [self._to_response(s) for s in strategies]

    def activate_strategy(self, strategy_id: int, strategy_type: str) -> StrategyResponse:
        """
        매수 전략 활성화

        Args:
            strategy_id: 전략 ID
            strategy_type: 전략 타입

        Returns:
            StrategyResponse: 업데이트된 전략

        Raises:
            StrategyNotFoundError: 전략을 찾을 수 없음
            StrategyInitializationError: 전략 초기화 실패
        """
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

        logger.info(f"전략 활성화: {strategy_orm.name}")
        return self._to_response(strategy_orm, strategy_type)

    def deactivate_strategy(self, strategy_id: int) -> StrategyResponse:
        """
        매수 전략 비활성화

        Args:
            strategy_id: 전략 ID

        Returns:
            StrategyResponse: 업데이트된 전략
        """
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

        logger.info(f"전략 비활성화: {strategy_orm.name}")
        return self._to_response(strategy_orm)

    def generate_entry_signal(
        self,
        strategy_id: int,
        strategy_type: str,
        symbol: str,
        count: int = 200
    ) -> StrategySignalData:
        """
        매수 시그널 생성

        Args:
            strategy_id: 전략 ID
            strategy_type: 전략 타입
            symbol: 거래 심볼 (예: KRW-BTC)
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

        # 시그널 생성
        try:
            signal_data = strategy_instance.analyze(symbol, ohlcv_data)
            logger.info(
                f"매수 시그널 생성 | {symbol} | {signal_data.signal.value.upper()} "
                f"(확신도: {signal_data.confidence:.2%})"
            )
            return signal_data

        except Exception as e:
            logger.error(f"시그널 생성 실패: {e}")
            raise StrategyExecutionError(f"시그널 생성 실패: {str(e)}")

    def batch_generate_signals(
        self,
        strategy_id: int,
        strategy_type: str,
        symbols: List[str],
        count: int = 200
    ) -> Dict[str, StrategySignalData]:
        """
        여러 심볼에 대해 매수 시그널 일괄 생성

        Args:
            strategy_id: 전략 ID
            strategy_type: 전략 타입
            symbols: 거래 심볼 리스트
            count: 가져올 캔들 개수

        Returns:
            Dict[str, StrategySignalData]: 심볼별 시그널 데이터
        """
        results = {}

        for symbol in symbols:
            try:
                signal_data = self.generate_entry_signal(
                    strategy_id,
                    strategy_type,
                    symbol,
                    count
                )
                results[symbol] = signal_data

            except Exception as e:
                logger.error(f"{symbol} 시그널 생성 실패: {e}")
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

    def get_strategy_statistics(self, strategy_id: int) -> Dict:
        """
        전략 통계 조회

        Args:
            strategy_id: 전략 ID

        Returns:
            Dict: 통계 정보
        """
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
    ) -> BaseEntryStrategy:
        """전략 인스턴스 생성"""
        if strategy_type not in self.ENTRY_STRATEGY_CLASSES:
            raise StrategyInitializationError(
                f"지원하지 않는 전략 타입: {strategy_type}"
            )

        strategy_class = self.ENTRY_STRATEGY_CLASSES[strategy_type]

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
            # Upbit API 호출
            candles = self.exchange.get_candles(
                symbol=symbol,
                interval=timeframe.value,
                count=count
            )

            # OHLCV 모델로 변환
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
        사용 가능한 매수 전략 목록

        Returns:
            List[Dict]: 전략 타입 및 설명
        """
        return [
            {
                "type": "macd_entry",
                "name": "MACD Entry",
                "description": "MACD 골든 크로스 매수 전략",
                "parameters": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "min_confidence": 0.65,
                }
            },
            {
                "type": "stochastic_entry",
                "name": "Stochastic Entry",
                "description": "Stochastic 과매도 반등 매수 전략",
                "parameters": {
                    "k_period": 14,
                    "d_period": 3,
                    "smooth": 3,
                    "oversold": 20,
                    "min_confidence": 0.65,
                }
            },
            {
                "type": "multi_indicator_entry",
                "name": "Multi-Indicator Entry",
                "description": "복합 지표 기반 매수 전략",
                "parameters": {
                    "use_rsi": True,
                    "use_macd": True,
                    "use_bollinger": True,
                    "use_volume": True,
                    "combination_mode": "AND",
                    "min_confidence": 0.7,
                }
            },
            {
                "type": "hybrid_entry",
                "name": "Hybrid Entry",
                "description": "복합 전략 가중 평균 매수",
                "parameters": {
                    "strategy_weights": {
                        "macd": 0.35,
                        "stochastic": 0.30,
                        "rsi": 0.20,
                        "volume": 0.15,
                    },
                    "buy_threshold": 0.65,
                    "min_confidence": 0.7,
                }
            },
        ]


if __name__ == "__main__":
    print("=== Entry Service 테스트 ===")
    print("사용 가능한 매수 전략:")

    # DB 세션 없이 테스트 (전략 목록만)
    service = EntryService(db=None, exchange=None)  # type: ignore

    for strategy in service.get_available_strategies():
        print(f"\n- {strategy['name']} ({strategy['type']})")
        print(f"  설명: {strategy['description']}")
        print(f"  파라미터: {strategy['parameters']}")
