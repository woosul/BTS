"""
BTS 기술 지표 계산 모듈

모든 기술적 분석 지표를 중앙화하여 관리
"""
from typing import Union, Tuple
from decimal import Decimal
import pandas as pd
import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


# ==================== 이동평균 (Moving Averages) ====================

def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """
    단순 이동평균 (Simple Moving Average) 계산

    Args:
        prices: 가격 시리즈
        period: 이동평균 기간

    Returns:
        pd.Series: SMA 값
    """
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    지수 이동평균 (Exponential Moving Average) 계산

    Args:
        prices: 가격 시리즈
        period: 이동평균 기간

    Returns:
        pd.Series: EMA 값
    """
    return prices.ewm(span=period, adjust=False).mean()


# ==================== RSI (Relative Strength Index) ====================

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI (Relative Strength Index) 계산

    Args:
        prices: 가격 시리즈
        period: RSI 기간 (기본 14)

    Returns:
        pd.Series: RSI 값 (0-100)
    """
    # 가격 변화 계산
    delta = prices.diff()

    # 상승/하락 분리
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # 평균 계산 (EMA 방식)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()

    # RS 및 RSI 계산
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


# ==================== MACD (Moving Average Convergence Divergence) ====================

def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence) 계산

    Args:
        prices: 가격 시리즈
        fast_period: 단기 EMA 기간 (기본 12)
        slow_period: 장기 EMA 기간 (기본 26)
        signal_period: 시그널 EMA 기간 (기본 9)

    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (MACD 선, 시그널 선, 히스토그램)
    """
    # 단기/장기 EMA 계산
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)

    # MACD 선 = 단기 EMA - 장기 EMA
    macd_line = ema_fast - ema_slow

    # 시그널 선 = MACD 선의 EMA
    signal_line = calculate_ema(macd_line, signal_period)

    # 히스토그램 = MACD 선 - 시그널 선
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


# ==================== Bollinger Bands ====================

def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    볼린저 밴드 (Bollinger Bands) 계산

    Args:
        prices: 가격 시리즈
        period: 이동평균 기간 (기본 20)
        std_dev: 표준편차 배수 (기본 2.0)

    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (상단 밴드, 중심선, 하단 밴드)
    """
    # 중심선 (SMA)
    middle_band = calculate_sma(prices, period)

    # 표준편차
    std = prices.rolling(window=period).std()

    # 상단/하단 밴드
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)

    return upper_band, middle_band, lower_band


# ==================== Stochastic Oscillator ====================

def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
    smooth: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    스토캐스틱 오실레이터 (Stochastic Oscillator) 계산

    Args:
        high: 고가 시리즈
        low: 저가 시리즈
        close: 종가 시리즈
        k_period: %K 기간 (기본 14)
        d_period: %D 기간 (기본 3)
        smooth: 평활 기간 (기본 3)

    Returns:
        Tuple[pd.Series, pd.Series]: (%K, %D)
    """
    # 최저가/최고가
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    # %K 계산 (Fast Stochastic)
    k_fast = 100 * (close - lowest_low) / (highest_high - lowest_low)

    # %K 평활 (Slow Stochastic)
    k_slow = k_fast.rolling(window=smooth).mean()

    # %D 계산 (%K의 이동평균)
    d = k_slow.rolling(window=d_period).mean()

    return k_slow, d


# ==================== ATR (Average True Range) ====================

def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    ATR (Average True Range) 계산

    Args:
        high: 고가 시리즈
        low: 저가 시리즈
        close: 종가 시리즈
        period: ATR 기간 (기본 14)

    Returns:
        pd.Series: ATR 값
    """
    # True Range 계산
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR = True Range의 이동평균
    atr = true_range.ewm(span=period, adjust=False).mean()

    return atr


# ==================== ADX (Average Directional Index) ====================

def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    ADX (Average Directional Index) 계산

    Args:
        high: 고가 시리즈
        low: 저가 시리즈
        close: 종가 시리즈
        period: ADX 기간 (기본 14)

    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (ADX, +DI, -DI)
    """
    # +DM, -DM 계산
    high_diff = high.diff()
    low_diff = -low.diff()

    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

    # ATR 계산
    atr = calculate_atr(high, low, close, period)

    # +DI, -DI 계산
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

    # DX 계산
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)

    # ADX 계산 (DX의 이동평균)
    adx = dx.ewm(span=period, adjust=False).mean()

    return adx, plus_di, minus_di


# ==================== 기타 보조 지표 ====================

def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    OBV (On-Balance Volume) 계산

    Args:
        close: 종가 시리즈
        volume: 거래량 시리즈

    Returns:
        pd.Series: OBV 값
    """
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    return obv


def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    VWAP (Volume Weighted Average Price) 계산

    Args:
        high: 고가 시리즈
        low: 저가 시리즈
        close: 종가 시리즈
        volume: 거래량 시리즈

    Returns:
        pd.Series: VWAP 값
    """
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap


def calculate_momentum(prices: pd.Series, period: int = 10) -> pd.Series:
    """
    모멘텀 (Momentum) 계산

    Args:
        prices: 가격 시리즈
        period: 모멘텀 기간 (기본 10)

    Returns:
        pd.Series: 모멘텀 값
    """
    return prices.diff(period)


def calculate_roc(prices: pd.Series, period: int = 10) -> pd.Series:
    """
    ROC (Rate of Change) 계산

    Args:
        prices: 가격 시리즈
        period: ROC 기간 (기본 10)

    Returns:
        pd.Series: ROC 값 (%)
    """
    return ((prices - prices.shift(period)) / prices.shift(period)) * 100


# ==================== 유틸리티 함수 ====================

def validate_series(series: pd.Series, name: str, min_length: int = 2) -> None:
    """
    시리즈 데이터 유효성 검증

    Args:
        series: 검증할 시리즈
        name: 시리즈 이름
        min_length: 최소 길이

    Raises:
        ValueError: 유효하지 않은 경우
    """
    if series is None or len(series) < min_length:
        raise ValueError(f"{name} 데이터가 부족합니다 (최소 {min_length}개 필요)")

    if series.isna().all():
        raise ValueError(f"{name} 데이터에 유효한 값이 없습니다")


def safe_divide(numerator: pd.Series, denominator: pd.Series, fill_value: float = 0) -> pd.Series:
    """
    안전한 나눗셈 (0으로 나누기 방지)

    Args:
        numerator: 분자
        denominator: 분모
        fill_value: 0으로 나눌 때 대체 값

    Returns:
        pd.Series: 나눗셈 결과
    """
    result = numerator / denominator
    result = result.replace([np.inf, -np.inf], fill_value)
    return result.fillna(fill_value)


if __name__ == "__main__":
    """
    기술 지표 계산 테스트
    """
    print("=== 기술 지표 계산 테스트 ===\n")

    # 샘플 데이터 생성
    np.random.seed(42)
    n = 100
    dates = pd.date_range(start='2024-01-01', periods=n, freq='H')

    # 가격 데이터 생성 (랜덤 워크)
    close_prices = pd.Series(
        50000000 + np.cumsum(np.random.randn(n) * 100000),
        index=dates
    )
    high_prices = close_prices * 1.01
    low_prices = close_prices * 0.99
    volume = pd.Series(np.random.rand(n) * 1000 + 500, index=dates)

    print(f"샘플 데이터: {len(close_prices)}개 캔들\n")

    # 1. RSI 테스트
    rsi = calculate_rsi(close_prices, period=14)
    print(f"1. RSI (14): {rsi.iloc[-1]:.2f}")

    # 2. MACD 테스트
    macd, signal, hist = calculate_macd(close_prices)
    print(f"2. MACD: {macd.iloc[-1]:.2f}, Signal: {signal.iloc[-1]:.2f}, Hist: {hist.iloc[-1]:.2f}")

    # 3. Bollinger Bands 테스트
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close_prices, period=20, std_dev=2.0)
    print(f"3. Bollinger Bands: Upper={bb_upper.iloc[-1]:,.0f}, Middle={bb_middle.iloc[-1]:,.0f}, Lower={bb_lower.iloc[-1]:,.0f}")

    # 4. Stochastic 테스트
    k, d = calculate_stochastic(high_prices, low_prices, close_prices)
    print(f"4. Stochastic: %K={k.iloc[-1]:.2f}, %D={d.iloc[-1]:.2f}")

    # 5. ATR 테스트
    atr = calculate_atr(high_prices, low_prices, close_prices, period=14)
    print(f"5. ATR (14): {atr.iloc[-1]:,.0f}")

    # 6. Moving Averages 테스트
    sma_20 = calculate_sma(close_prices, 20)
    ema_20 = calculate_ema(close_prices, 20)
    print(f"6. SMA(20): {sma_20.iloc[-1]:,.0f}, EMA(20): {ema_20.iloc[-1]:,.0f}")

    print("\n✅ 모든 기술 지표 계산 성공")
