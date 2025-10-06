"""
BTS 전략 서비스

트레이딩 전략 관리 및 실행
Streamlit과 FastAPI에서 공통 사용
"""
from typing import List, Optional, Dict, Type
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
import json

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import StrategyORM
from infrastructure.exchanges.upbit_client import UpbitClient
from domain.strategies.base_strategy import BaseStrategy
from domain.strategies.rsi_strategy import RSIStrategy
from core.models import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategySignalData,
    OHLCV
)
from core.enums import StrategyStatus, TimeFrame
from core.exceptions import (
    StrategyNotFoundError,
    StrategyInitializationError,
    StrategyExecutionError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class StrategyService:
    """
    전략 서비스

    전략 생성, 활성화, 시그널 생성 등 전략 관련 로직
    """

    # 사용 가능한 전략 클래스 매핑
    STRATEGY_CLASSES: Dict[str, Type[BaseStrategy]] = {
        "rsi": RSIStrategy,
        # 추후 추가: "ma_cross": MACrossStrategy, ...
    }

    def __init__(self, db: Session, exchange: Optional[UpbitClient] = None):
        self.db = db
        self.strategy_repo = BaseRepository(StrategyORM, db)
        self.exchange = exchange or UpbitClient()

        # 활성 전략 인스턴스 캐시
        self._active_strategies: Dict[int, BaseStrategy] = {}

    # ===== 전략 관리 =====
    def create_strategy(self, strategy_data: StrategyCreate) -> StrategyResponse:
        """
        전략 생성

        Args:
            strategy_data: 전략 생성 데이터

        Returns:
            StrategyResponse: 생성된 전략

        Raises:
            StrategyInitializationError: 전략 초기화 실패
        """
        # 파라미터를 JSON 문자열로 변환
        parameters_json = json.dumps(strategy_data.parameters)

        # DB에 저장
        strategy_orm = self.strategy_repo.create(
            name=strategy_data.name,
            description=strategy_data.description,
            timeframe=strategy_data.timeframe,
            parameters=parameters_json,
            status=StrategyStatus.INACTIVE
        )

        logger.info(f"전략 생성: {strategy_orm.name} (ID: {strategy_orm.id})")
        return self._to_response(strategy_orm)

    def get_strategy(self, strategy_id: int) -> StrategyResponse:
        """
        전략 조회

        Args:
            strategy_id: 전략 ID

        Returns:
            StrategyResponse: 전략 정보

        Raises:
            StrategyNotFoundError: 전략을 찾을 수 없음
        """
        strategy_orm = self.strategy_repo.get_by_id(strategy_id)
        if not strategy_orm:
            raise StrategyNotFoundError(
                "전략을 찾을 수 없습니다",
                {"strategy_id": strategy_id}
            )

        return self._to_response(strategy_orm)

    def get_all_strategies(self) -> List[StrategyResponse]:
        """전략 목록 조회"""
        strategies = self.strategy_repo.get_all()
        return [self._to_response(s) for s in strategies]

    def update_strategy(
        self,
        strategy_id: int,
        strategy_data: StrategyUpdate
    ) -> StrategyResponse:
        """
        전략 업데이트

        Args:
            strategy_id: 전략 ID
            strategy_data: 업데이트 데이터

        Returns:
            StrategyResponse: 업데이트된 전략
        """
        strategy_orm = self.strategy_repo.get_by_id_or_raise(strategy_id)

        # 업데이트 데이터 준비
        update_dict = strategy_data.model_dump(exclude_unset=True)

        # 파라미터는 JSON 변환
        if "parameters" in update_dict:
            update_dict["parameters"] = json.dumps(update_dict["parameters"])

        # 업데이트
        if update_dict:
            strategy_orm = self.strategy_repo.update(strategy_id, **update_dict)

            # 캐시된 인스턴스 제거 (재생성 필요)
            if strategy_id in self._active_strategies:
                del self._active_strategies[strategy_id]

        logger.info(f"전략 업데이트: {strategy_orm.name}")
        return self._to_response(strategy_orm)

    def delete_strategy(self, strategy_id: int) -> bool:
        """
        전략 삭제

        Args:
            strategy_id: 전략 ID

        Returns:
            bool: 삭제 성공 여부
        """
        # 캐시에서 제거
        if strategy_id in self._active_strategies:
            del self._active_strategies[strategy_id]

        success = self.strategy_repo.delete(strategy_id)
        if success:
            logger.info(f"전략 삭제: ID {strategy_id}")
        return success

    # ===== 전략 활성화/비활성화 =====
    def activate_strategy(self, strategy_id: int) -> StrategyResponse:
        """
        전략 활성화

        Args:
            strategy_id: 전략 ID

        Returns:
            StrategyResponse: 활성화된 전략
        """
        strategy_orm = self.strategy_repo.get_by_id_or_raise(strategy_id)

        # 전략 인스턴스 생성
        strategy_instance = self._get_strategy_instance(strategy_orm)
        strategy_instance.activate()

        # DB 업데이트
        self.strategy_repo.update(strategy_id, status=StrategyStatus.ACTIVE)

        # 캐시에 저장
        self._active_strategies[strategy_id] = strategy_instance

        logger.info(f"전략 활성화: {strategy_orm.name}")
        return self._to_response(strategy_orm)

    def deactivate_strategy(self, strategy_id: int) -> StrategyResponse:
        """
        전략 비활성화

        Args:
            strategy_id: 전략 ID

        Returns:
            StrategyResponse: 비활성화된 전략
        """
        strategy_orm = self.strategy_repo.get_by_id_or_raise(strategy_id)

        # 전략 인스턴스 비활성화
        if strategy_id in self._active_strategies:
            self._active_strategies[strategy_id].deactivate()
            del self._active_strategies[strategy_id]

        # DB 업데이트
        self.strategy_repo.update(strategy_id, status=StrategyStatus.INACTIVE)

        logger.info(f"전략 비활성화: {strategy_orm.name}")
        return self._to_response(strategy_orm)

    # ===== 시그널 생성 =====
    def generate_signal(
        self,
        strategy_id: int,
        symbol: str,
        ohlcv_data: Optional[List[OHLCV]] = None
    ) -> StrategySignalData:
        """
        트레이딩 시그널 생성

        Args:
            strategy_id: 전략 ID
            symbol: 거래 심볼
            ohlcv_data: OHLCV 데이터 (없으면 거래소에서 조회)

        Returns:
            StrategySignalData: 시그널 데이터

        Raises:
            StrategyExecutionError: 시그널 생성 실패
        """
        strategy_orm = self.strategy_repo.get_by_id_or_raise(strategy_id)

        # 전략 인스턴스 가져오기
        strategy = self._get_strategy_instance(strategy_orm)

        # OHLCV 데이터 준비
        if ohlcv_data is None:
            ohlcv_data = self._fetch_ohlcv_data(
                symbol,
                strategy_orm.timeframe
            )

        # 시그널 생성
        try:
            signal_data = strategy.analyze(symbol, ohlcv_data)
            logger.info(
                f"시그널 생성 완료: {strategy_orm.name} | {symbol} | "
                f"{signal_data.signal.value.upper()}"
            )
            return signal_data

        except Exception as e:
            logger.error(f"시그널 생성 실패: {e}")
            raise StrategyExecutionError(
                f"시그널 생성 실패: {str(e)}",
                {"strategy_id": strategy_id, "symbol": symbol, "error": str(e)}
            )

    def generate_signals_for_all_active(
        self,
        symbols: List[str]
    ) -> Dict[int, List[StrategySignalData]]:
        """
        모든 활성 전략의 시그널 생성

        Args:
            symbols: 거래 심볼 목록

        Returns:
            Dict[int, List[StrategySignalData]]: {전략ID: [시그널들]}
        """
        # 활성 전략 조회
        active_strategies = self.strategy_repo.filter_by(status=StrategyStatus.ACTIVE)

        results = {}
        for strategy_orm in active_strategies:
            signals = []
            for symbol in symbols:
                try:
                    signal = self.generate_signal(strategy_orm.id, symbol)
                    signals.append(signal)
                except Exception as e:
                    logger.error(f"시그널 생성 실패 ({symbol}): {e}")

            results[strategy_orm.id] = signals

        return results

    # ===== 백테스팅 =====
    def backtest_strategy(
        self,
        strategy_id: int,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_balance: Decimal = Decimal("10000000")
    ) -> Dict:
        """
        전략 백테스팅

        Args:
            strategy_id: 전략 ID
            symbol: 거래 심볼
            start_date: 시작일
            end_date: 종료일
            initial_balance: 초기 자본

        Returns:
            Dict: 백테스팅 결과
        """
        # TODO: 백테스팅 로직 구현
        logger.info(f"백테스팅 시작: 전략 {strategy_id}, {symbol}")

        return {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "initial_balance": initial_balance,
            "message": "백테스팅 기능은 추후 구현 예정입니다"
        }

    # ===== 내부 메서드 =====
    def _get_strategy_instance(self, strategy_orm: StrategyORM) -> BaseStrategy:
        """
        전략 인스턴스 생성 또는 캐시에서 가져오기

        Args:
            strategy_orm: 전략 ORM

        Returns:
            BaseStrategy: 전략 인스턴스

        Raises:
            StrategyInitializationError: 초기화 실패
        """
        # 캐시 확인
        if strategy_orm.id in self._active_strategies:
            return self._active_strategies[strategy_orm.id]

        # 전략 클래스 찾기
        strategy_type = self._infer_strategy_type(strategy_orm.name)
        strategy_class = self.STRATEGY_CLASSES.get(strategy_type)

        if not strategy_class:
            raise StrategyInitializationError(
                f"지원하지 않는 전략 유형: {strategy_type}",
                {"name": strategy_orm.name}
            )

        # 파라미터 파싱
        parameters = json.loads(strategy_orm.parameters) if strategy_orm.parameters else {}

        # 인스턴스 생성
        try:
            strategy = strategy_class(
                id=strategy_orm.id,
                name=strategy_orm.name,
                description=strategy_orm.description or "",
                timeframe=strategy_orm.timeframe,
                parameters=parameters
            )
            return strategy

        except Exception as e:
            logger.error(f"전략 인스턴스 생성 실패: {e}")
            raise StrategyInitializationError(
                f"전략 초기화 실패: {str(e)}",
                {"strategy_id": strategy_orm.id, "error": str(e)}
            )

    def _infer_strategy_type(self, name: str) -> str:
        """
        전략 이름으로 유형 추론

        Args:
            name: 전략 이름

        Returns:
            str: 전략 유형 (rsi, ma_cross 등)
        """
        name_lower = name.lower()

        if "rsi" in name_lower:
            return "rsi"
        elif "ma" in name_lower or "moving average" in name_lower:
            return "ma_cross"
        elif "bollinger" in name_lower:
            return "bollinger"
        else:
            # 기본값
            return "rsi"

    def _fetch_ohlcv_data(
        self,
        symbol: str,
        timeframe: TimeFrame,
        limit: int = 200
    ) -> List[OHLCV]:
        """
        거래소에서 OHLCV 데이터 조회

        Args:
            symbol: 거래 심볼
            timeframe: 시간 프레임
            limit: 조회 개수

        Returns:
            List[OHLCV]: OHLCV 데이터
        """
        # TimeFrame enum을 Upbit interval로 변환
        interval_map = {
            TimeFrame.MINUTE_1: "1",
            TimeFrame.MINUTE_3: "3",
            TimeFrame.MINUTE_5: "5",
            TimeFrame.MINUTE_15: "15",
            TimeFrame.MINUTE_30: "30",
            TimeFrame.HOUR_1: "60",
            TimeFrame.HOUR_4: "240",
            TimeFrame.DAY_1: "day",
            TimeFrame.WEEK_1: "week",
        }

        interval = interval_map.get(timeframe, "60")
        return self.exchange.get_ohlcv(symbol, interval, limit)

    def _to_response(self, strategy_orm: StrategyORM) -> StrategyResponse:
        """ORM → Response 변환"""
        parameters = json.loads(strategy_orm.parameters) if strategy_orm.parameters else {}

        return StrategyResponse(
            id=strategy_orm.id,
            name=strategy_orm.name,
            description=strategy_orm.description or "",
            timeframe=strategy_orm.timeframe,
            status=strategy_orm.status,
            parameters=parameters,
            created_at=strategy_orm.created_at,
            updated_at=strategy_orm.updated_at
        )


if __name__ == "__main__":
    from infrastructure.database.connection import get_db_session

    print("=== 전략 서비스 테스트 ===")

    with get_db_session() as db:
        service = StrategyService(db)

        # 전략 생성
        strategy_data = StrategyCreate(
            name="테스트 RSI 전략",
            description="RSI 기반 자동매매",
            timeframe=TimeFrame.HOUR_1,
            parameters={
                "rsi_period": 14,
                "oversold": 30,
                "overbought": 70
            }
        )

        try:
            strategy = service.create_strategy(strategy_data)
            print(f"\n1. 전략 생성: {strategy.name} (ID: {strategy.id})")

            # 전략 활성화
            strategy = service.activate_strategy(strategy.id)
            print(f"\n2. 전략 활성화: {strategy.status.value}")

            # 시그널 생성
            signal = service.generate_signal(strategy.id, "KRW-BTC")
            print(f"\n3. 시그널 생성: {signal.signal.value.upper()} (확신도: {signal.confidence:.2%})")

        except Exception as e:
            print(f"\n오류: {e}")
