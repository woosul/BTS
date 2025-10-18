#!/usr/bin/env python3
"""CoinGecko 실시간 가격 직접 확인"""
import requests
from datetime import datetime

API_KEY = "CG-fBNTwyjA4srLMRp7VCdDQmeh"  # 실제 사용 중인 키
URL = "https://api.coingecko.com/api/v3/coins/markets"

params = {
    'vs_currency': 'usd',
    'order': 'market_cap_desc',
    'per_page': 5,
    'page': 1,
    'sparkline': 'false',
    'price_change_percentage': '24h'
}

headers = {
    'x-cg-demo-api-key': API_KEY
}

print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

try:
    response = requests.get(URL, params=params, headers=headers, timeout=15)
    print(f"📡 응답 상태: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n✅ 받은 데이터: {len(data)}개 코인\n")
        print(f"{'코인':<12} {'가격':<18} {'24h 변동':<12}")
        print("=" * 50)
        
        for coin in data[:5]:
            name = coin.get('name', 'N/A')
            symbol = coin.get('symbol', 'N/A').upper()
            price = coin.get('current_price', 0)
            change = coin.get('price_change_percentage_24h', 0)
            
            print(f"{name:<12} ${price:>15,.2f}  {change:>6.2f}%")
            
        # BTC 상세 정보
        btc = data[0]
        print(f"\n🔍 BTC 상세:")
        print(f"  - current_price: {btc.get('current_price')}")
        print(f"  - last_updated: {btc.get('last_updated')}")
        print(f"  - price_change_24h: {btc.get('price_change_24h')}")
        print(f"  - price_change_percentage_24h: {btc.get('price_change_percentage_24h')}")
        
    else:
        print(f"❌ 오류: {response.text}")
        
except Exception as e:
    print(f"❌ 예외 발생: {e}")
