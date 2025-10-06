"""
BTS Data Summarizer

토큰 최적화를 위한 데이터 요약 모듈
"""
from typing import Dict, List
from decimal import Decimal
from datetime import datetime

from core.models import OHLCV
from utils.logger import get_logger

logger = get_logger(__name__)


class DataSummarizer:
    """
    데이터 요약기

    AI 평가를 위해 차트 데이터를 최소 토큰으로 요약
    """

    def __init__(self, max_candles: int = 20):
        """
        초기화

        Args:
            max_candles: 전송할 최대 캔들 개수
        """
        self.max_candles = max_candles

    def summarize_ohlcv(
        self,
        symbol: str,
        ohlcv_data: List[OHLCV],
        indicators: Dict
    ) -> Dict:
        """
        OHLCV 데이터 요약

        Args:
            symbol: 거래 심볼
            ohlcv_data: OHLCV 데이터
            indicators: 기술 지표

        Returns:
            Dict: 요약된 데이터
        """
        if not ohlcv_data:
            return {
                "symbol": symbol,
                "error": "데이터 없음"
            }

        # 최신 캔들만 선택
        recent_candles = ohlcv_data[-self.max_candles:]

        # 현재가 정보
        latest = recent_candles[-1]
        current_price = latest.close

        # 가격 변화율
        if len(recent_candles) >= 24:
            price_24h_ago = recent_candles[-24].close
            price_change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
        else:
            price_change_24h = Decimal("0")

        # 거래량 평균
        avg_volume = sum(c.volume for c in recent_candles) / len(recent_candles)

        # 최근 캔들 간략 정보
        candle_summary = []
        for i, candle in enumerate(recent_candles[-10:]):  # 최근 10개만
            candle_summary.append({
                "index": i - 9,  # -9, -8, ..., 0 (현재)
                "close": float(candle.close),
                "volume_ratio": float(candle.volume / avg_volume) if avg_volume > 0 else 1.0
            })

        # 요약 데이터
        summary = {
            "symbol": symbol,
            "timeframe": "1h",
            "current_price": float(current_price),
            "price_change_24h": float(price_change_24h),
            "volume_avg": float(avg_volume),
            "recent_candles": candle_summary,
            "indicators": self._summarize_indicators(indicators)
        }

        return summary

    def _summarize_indicators(self, indicators: Dict) -> Dict:
        """
        기술 지표 요약

        Args:
            indicators: 원본 지표

        Returns:
            Dict: 요약된 지표
        """
        summary = {}

        # RSI
        if "rsi" in indicators:
            summary["rsi"] = float(indicators["rsi"])

        # MACD
        if "macd" in indicators:
            summary["macd"] = {
                "value": float(indicators["macd"]),
                "signal": float(indicators.get("macd_signal", 0)),
                "histogram": float(indicators.get("macd_histogram", 0))
            }

        # Bollinger Bands
        if "bb_upper" in indicators:
            current_price = indicators.get("current_price", 0)
            bb_upper = indicators["bb_upper"]
            bb_lower = indicators["bb_lower"]
            bb_middle = indicators["bb_middle"]

            # 볼린저 밴드 내 위치 (0-1, 0.5가 중간)
            if bb_upper != bb_lower:
                bb_position = float((current_price - bb_lower) / (bb_upper - bb_lower))
            else:
                bb_position = 0.5

            summary["bollinger"] = {
                "position": bb_position,  # 0=하단, 0.5=중간, 1=상단
                "width": float((bb_upper - bb_lower) / bb_middle) if bb_middle > 0 else 0
            }

        # Stochastic
        if "k" in indicators:
            summary["stochastic"] = {
                "k": float(indicators["k"]),
                "d": float(indicators.get("d", 0))
            }

        # MA (이동평균)
        if "ma_short" in indicators:
            summary["ma"] = {
                "short": float(indicators["ma_short"]),
                "long": float(indicators.get("ma_long", 0)),
                "cross": "golden" if indicators["ma_short"] > indicators.get("ma_long", 0) else "dead"
            }

        # 거래량 비율
        if "volume_ratio" in indicators:
            summary["volume_ratio"] = float(indicators["volume_ratio"])

        # 손익률 (매도 평가 시)
        if "profit_loss_pct" in indicators:
            summary["profit_loss_pct"] = float(indicators["profit_loss_pct"])

        return summary

    def summarize_strategy_signals(
        self,
        signals: List[Dict]
    ) -> List[Dict]:
        """
        전략 시그널 요약

        Args:
            signals: 전략 시그널 리스트

        Returns:
            List[Dict]: 요약된 시그널
        """
        summary = []

        for signal in signals:
            summary.append({
                "strategy": signal.get("strategy", "Unknown"),
                "signal": signal.get("signal", "hold"),
                "confidence": float(signal.get("confidence", 0.5))
            })

        return summary

    def calculate_summary_stats(
        self,
        ohlcv_data: List[OHLCV]
    ) -> Dict:
        """
        통계 요약

        Args:
            ohlcv_data: OHLCV 데이터

        Returns:
            Dict: 통계 정보
        """
        if not ohlcv_data:
            return {}

        closes = [float(c.close) for c in ohlcv_data]
        volumes = [float(c.volume) for c in ohlcv_data]

        # 기본 통계
        min_price = min(closes)
        max_price = max(closes)
        avg_price = sum(closes) / len(closes)

        # 변동성 (표준편차)
        variance = sum((p - avg_price) ** 2 for p in closes) / len(closes)
        volatility = variance ** 0.5

        return {
            "min_price": min_price,
            "max_price": max_price,
            "avg_price": avg_price,
            "volatility": volatility,
            "avg_volume": sum(volumes) / len(volumes),
            "data_points": len(ohlcv_data)
        }

    def __repr__(self) -> str:
        return f"<DataSummarizer(max_candles={self.max_candles})>"


if __name__ == "__main__":
    print("=== Data Summarizer 테스트 ===")

    from datetime import timedelta

    # 테스트 데이터 생성
    test_data = []
    base_price = Decimal("50000000")
    base_time = datetime.now()

    for i in range(30):
        price = base_price + Decimal(str(i * 100000))
        candle = OHLCV(
            timestamp=base_time + timedelta(hours=i),
            open=price - Decimal("50000"),
            high=price + Decimal("100000"),
            low=price - Decimal("100000"),
            close=price,
            volume=Decimal("100") * (1 + Decimal(str(i % 3)) * Decimal("0.5"))
        )
        test_data.append(candle)

    # 테스트 지표
    test_indicators = {
        "rsi": Decimal("65.5"),
        "macd": Decimal("150000"),
        "macd_signal": Decimal("120000"),
        "macd_histogram": Decimal("30000"),
        "bb_upper": Decimal("52000000"),
        "bb_middle": Decimal("50000000"),
        "bb_lower": Decimal("48000000"),
        "current_price": Decimal("51000000"),
        "volume_ratio": Decimal("1.8")
    }

    # 요약기 생성
    summarizer = DataSummarizer(max_candles=20)

    # OHLCV 요약
    summary = summarizer.summarize_ohlcv(
        symbol="KRW-BTC",
        ohlcv_data=test_data,
        indicators=test_indicators
    )

    print("\n[요약 결과]")
    print(f"심볼: {summary['symbol']}")
    print(f"현재가: {summary['current_price']:,.0f} KRW")
    print(f"24시간 변화: {summary['price_change_24h']:.2f}%")

    print(f"\n지표:")
    for key, value in summary['indicators'].items():
        print(f"  {key}: {value}")

    print(f"\n최근 캔들 수: {len(summary['recent_candles'])}")

    # 통계 요약
    stats = summarizer.calculate_summary_stats(test_data)
    print(f"\n통계:")
    print(f"  평균가: {stats['avg_price']:,.0f} KRW")
    print(f"  변동성: {stats['volatility']:,.0f}")
    print(f"  데이터 포인트: {stats['data_points']}")

    # JSON 크기 추정
    import json
    json_str = json.dumps(summary, ensure_ascii=False)
    print(f"\nJSON 크기: {len(json_str)} 문자")
    print(f"토큰 추정: ~{len(json_str) // 4} 토큰")
