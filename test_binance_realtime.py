#!/usr/bin/env python3
"""
Binance API 실시간 가격 테스트
- API Key 불필요 (Public API)
- Rate Limit: 1200 requests/minute
- 업데이트 주기: 실시간 (초 단위)
"""

import requests
import time
from datetime import datetime

def test_binance_ticker():
    """Binance Ticker API 테스트 (24hr Price Change)"""
    url = "https://api.binance.com/api/v3/ticker/24hr"
    
    print("=" * 80)
    print("🔍 Binance 24hr Ticker API 테스트")
    print("=" * 80)
    
    # 주요 코인 심볼
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'USDCUSDT']
    
    for i in range(3):  # 3회 테스트
        print(f"\n⏰ 테스트 #{i+1} - {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 80)
        
        try:
            # 개별 심볼 조회
            for symbol in symbols:
                response = requests.get(url, params={'symbol': symbol}, timeout=5)
                response.raise_for_status()
                
                ticker = response.json()
                price = float(ticker['lastPrice'])
                change = float(ticker['priceChangePercent'])
                volume = float(ticker['volume'])
                
                # 코인명 추출
                coin_name = symbol.replace('USDT', '').replace('USDC', '')
                
                print(f"{coin_name:8} ${price:>12,.2f}  {change:>+7.2f}%  Vol: {volume:>15,.0f}")
            
        except Exception as e:
            print(f"❌ 에러: {e}")
        
        if i < 2:  # 마지막 반복이 아니면
            print("\n⏳ 5초 대기...")
            time.sleep(5)
    
    print("\n" + "=" * 80)

def test_binance_price():
    """Binance Price API 테스트 (최신 가격만)"""
    url = "https://api.binance.com/api/v3/ticker/price"
    
    print("\n" + "=" * 80)
    print("🔍 Binance Price API 테스트 (가장 가벼운 API)")
    print("=" * 80)
    
    symbols = ['BTCUSDT', 'ETHUSDT']
    
    for i in range(5):  # 5회 빠른 테스트
        print(f"\n⏰ 테스트 #{i+1} - {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        try:
            for symbol in symbols:
                response = requests.get(url, params={'symbol': symbol}, timeout=5)
                response.raise_for_status()
                
                ticker = response.json()
                price = float(ticker['price'])
                coin_name = symbol.replace('USDT', '')
                print(f"  {coin_name}: ${price:,.2f}")
            
        except Exception as e:
            print(f"❌ 에러: {e}")
        
        if i < 4:
            time.sleep(1)  # 1초 간격
    
    print("\n" + "=" * 80)

def compare_apis():
    """CoinGecko vs Binance 비교"""
    print("\n" + "=" * 80)
    print("📊 API 비교 분석")
    print("=" * 80)
    
    print("\n🟡 CoinGecko (현재 사용 중)")
    print("  - Rate Limit: Demo Plan ~30 calls/minute")
    print("  - 업데이트 주기: 1-2분 (캐시됨)")
    print("  - 장점: 5000+ 코인, 시총/거래량 등 풍부한 데이터")
    print("  - 단점: 느린 업데이트, Rate Limit 낮음")
    print("  - 가격: Demo는 무료, Pro는 $129/month")
    
    print("\n🟢 Binance Public API (추천)")
    print("  - Rate Limit: 1200 requests/minute (Weight 기반)")
    print("  - 업데이트 주기: 실시간 (초 단위)")
    print("  - 장점: 빠름, 무료, 안정적, API Key 불필요")
    print("  - 단점: Binance 상장 코인만 (350+)")
    print("  - 가격: 무료")
    
    print("\n💡 권장 사항:")
    print("  1. 대시보드 실시간 가격: Binance API 사용")
    print("  2. 코인 검색/필터링: CoinGecko 또는 Binance 리스트")
    print("  3. 하이브리드: 주요 코인은 Binance, 나머지는 CoinGecko")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_binance_ticker()
    test_binance_price()
    compare_apis()
