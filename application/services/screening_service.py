"""
종목선정 서비스

KRW/BTC 시장에서 상위 종목을 선정하는 서비스
"""
from typing import List, Dict, Optional, Type
from sqlalchemy.orm import Session

from domain.strategies.screening.base_screening import BaseScreeningStrategy, SymbolScore
from domain.strategies.screening.momentum_screening import MomentumScreening
from domain.strategies.screening.volume_screening import VolumeScreening
from domain.strategies.screening.technical_screening import TechnicalScreening
from domain.strategies.screening.hybrid_screening import HybridScreening
from infrastructure.exchanges.base_exchange import BaseExchange
from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class ScreeningService:
    """
    종목선정 서비스

    FastAPI에서도 재사용 가능
    """

    # 사용 가능한 스크리닝 전략
    SCREENING_STRATEGIES: Dict[str, Type[BaseScreeningStrategy]] = {
        "momentum": MomentumScreening,
        "volume": VolumeScreening,
        "technical": TechnicalScreening,
        "hybrid": HybridScreening,
    }

    def __init__(self, db: Session, exchange: BaseExchange):
        """
        서비스 초기화

        Args:
            db: 데이터베이스 세션
            exchange: 거래소 클라이언트
        """
        self.db = db
        self.exchange = exchange
        logger.info("ScreeningService 초기화 완료")

    def screen_symbols(
        self,
        market: str = "KRW",
        strategy_type: str = "momentum",
        strategy_params: Optional[Dict] = None,
        top_n: int = 10
    ) -> List[SymbolScore]:
        """
        종목 스크리닝

        Args:
            market: 시장 (KRW/BTC)
            strategy_type: 전략 유형 (momentum/volume/technical/hybrid)
            strategy_params: 전략 파라미터
            top_n: 선정할 상위 종목 수

        Returns:
            List[SymbolScore]: 상위 N개 종목 점수
        """
        logger.info(
            f"종목 스크리닝 시작: 시장={market}, 전략={strategy_type}, top {top_n}"
        )

        # 1. 시장 전체 심볼 조회
        all_symbols = self.exchange.get_market_symbols(market)
        logger.info(f"{market} 시장 심볼 {len(all_symbols)}개 조회")

        # 2. 각 심볼별 시장 데이터 수집
        market_data_dict = self._collect_market_data(all_symbols)

        # 3. 전략 인스턴스 생성
        if strategy_params is None:
            strategy_params = self._get_default_params(strategy_type)

        strategy = self._create_strategy(strategy_type, strategy_params)

        # 4. 스크리닝 실행
        top_symbols = strategy.screen(all_symbols, market_data_dict, top_n)

        logger.info(
            f"종목 스크리닝 완료: {len(top_symbols)}개 종목 선정"
        )

        return top_symbols

    def _collect_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        심볼별 시장 데이터 수집

        Args:
            symbols: 심볼 목록

        Returns:
            Dict[str, Dict]: 심볼별 시장 데이터
        """
        market_data_dict = {}

        for symbol in symbols:
            try:
                # 현재가 정보
                ticker = self.exchange.get_ticker(symbol)
                if not ticker:
                    continue

                # OHLCV 데이터 (최근 100개)
                ohlcv_data = self.exchange.get_ohlcv(symbol, "60", 100)
                if not ohlcv_data:
                    continue

                # 기술지표 계산 (간단한 RSI, MACD, MA)
                indicators = self._calculate_indicators(ohlcv_data)

                # 24시간 변동률 계산
                price_change_24h = self._calculate_change_24h(ohlcv_data, "price")
                volume_change_24h = self._calculate_change_24h(ohlcv_data, "volume")

                # ticker가 MarketPrice 객체인 경우 처리
                if hasattr(ticker, 'price'):
                    current_price = float(ticker.price)
                    volume_24h = 0  # MarketPrice에는 volume 정보 없음
                else:
                    current_price = ticker.get("trade_price", 0)
                    volume_24h = ticker.get("acc_trade_volume_24h", 0)

                market_data_dict[symbol] = {
                    "price": current_price,
                    "volume_24h": volume_24h,
                    "price_change_24h": price_change_24h,
                    "volume_change_24h": volume_change_24h,
                    "ohlcv": ohlcv_data,
                    "indicators": indicators
                }

            except Exception as e:
                logger.warning(f"{symbol} 데이터 수집 실패: {e}")
                continue

        return market_data_dict

    def _calculate_indicators(self, ohlcv_data: List[OHLCV]) -> Dict:
        """
        기술지표 계산

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Dict: 계산된 지표
        """
        if len(ohlcv_data) < 60:
            return {}

        import pandas as pd

        df = pd.DataFrame([
            {
                "close": float(o.close),
                "volume": float(o.volume)
            }
            for o in ohlcv_data
        ])

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # 이동평균
        ma_20 = df["close"].rolling(window=20).mean()
        ma_60 = df["close"].rolling(window=60).mean()

        # MACD (간단 버전)
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()

        return {
            "rsi": float(rsi.iloc[-1]) if not rsi.empty else 50.0,
            "ma_20": float(ma_20.iloc[-1]) if not ma_20.empty else 0.0,
            "ma_60": float(ma_60.iloc[-1]) if not ma_60.empty else 0.0,
            "macd": {
                "value": float(macd_line.iloc[-1]) if not macd_line.empty else 0.0,
                "signal": float(macd_signal.iloc[-1]) if not macd_signal.empty else 0.0
            }
        }

    def _calculate_change_24h(
        self,
        ohlcv_data: List[OHLCV],
        field: str = "price"
    ) -> float:
        """
        24시간 변동률 계산

        Args:
            ohlcv_data: OHLCV 데이터
            field: 계산할 필드 (price/volume)

        Returns:
            float: 변동률 (%)
        """
        if len(ohlcv_data) < 24:
            return 0.0

        if field == "price":
            current = float(ohlcv_data[-1].close)
            past = float(ohlcv_data[-24].close)
        else:  # volume
            current = float(ohlcv_data[-1].volume)
            past = float(ohlcv_data[-24].volume)

        if past == 0:
            return 0.0

        return ((current - past) / past) * 100

    def _create_strategy(
        self,
        strategy_type: str,
        parameters: Dict
    ) -> BaseScreeningStrategy:
        """
        전략 인스턴스 생성

        Args:
            strategy_type: 전략 유형
            parameters: 전략 파라미터

        Returns:
            BaseScreeningStrategy: 전략 인스턴스
        """
        if strategy_type not in self.SCREENING_STRATEGIES:
            raise ValueError(
                f"알 수 없는 전략 유형: {strategy_type}. "
                f"사용 가능: {list(self.SCREENING_STRATEGIES.keys())}"
            )

        strategy_class = self.SCREENING_STRATEGIES[strategy_type]
        strategy = strategy_class(parameters)

        # 파라미터 검증
        strategy.validate_parameters()

        return strategy

    def _get_default_params(self, strategy_type: str) -> Dict:
        """기본 파라미터 반환"""
        defaults = {
            "momentum": {
                "price_weight": 0.4,
                "volume_weight": 0.3,
                "rsi_weight": 0.3,
                "lookback_days": 7
            },
            "volume": {},
            "technical": {},
            "hybrid": {
                "strategies": [],
                "weights": []
            }
        }
        return defaults.get(strategy_type, {})

    def get_available_strategies(self) -> List[str]:
        """사용 가능한 전략 목록 반환"""
        return list(self.SCREENING_STRATEGIES.keys())
