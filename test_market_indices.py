"""
마켓 지수 서비스 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from application.services.market_index_service import MarketIndexService

def test_market_indices():
    service = MarketIndexService()
    
    print("=" * 60)
    print("글로벌 암호화폐 시장 데이터 (CoinGecko)")
    print("=" * 60)
    
    global_data = service.get_global_crypto_data()
    print(f"총 시가총액 (USD): ${global_data['total_market_cap_usd']:,.0f}")
    print(f"총 시가총액 (KRW): ₩{global_data['total_market_cap_krw']:,.0f}")
    print(f"24h 거래량 (USD): ${global_data['total_volume_usd']:,.0f}")
    print(f"BTC 도미넌스: {global_data['btc_dominance']:.2f}%")
    print(f"ETH 도미넌스: {global_data['eth_dominance']:.2f}%")
    print(f"24h 시가총액 변화: {global_data['market_cap_change_24h']:.2f}%")
    print(f"활성 암호화폐: {global_data['active_cryptocurrencies']:,}개")
    print(f"거래소: {global_data['markets']:,}개")
    
    print("\n" + "=" * 60)
    print("업비트 지수 (UBCI, UBMI, UB10, UB30)")
    print("=" * 60)
    
    upbit_data = service.get_upbit_indices()
    
    for key in ['ubci', 'ubmi', 'ub10', 'ub30']:
        index_data = upbit_data.get(key, {})
        value = index_data.get('value', 0)
        change = index_data.get('change', 0)
        change_rate = index_data.get('change_rate', 0)
        
        name_map = {
            'ubci': 'UBCI (업비트 종합지수)',
            'ubmi': 'UBMI (업비트 알트코인 지수)',
            'ub10': 'UB10 (업비트 10)',
            'ub30': 'UB30 (업비트 30)'
        }
        
        if value > 0:
            sign = '+' if change >= 0 else ''
            print(f"{name_map[key]}: {value:,.2f} ({sign}{change:,.2f}, {sign}{change_rate:.2f}%)")
        else:
            print(f"{name_map[key]}: 데이터 없음")
    
    print("=" * 60)

if __name__ == "__main__":
    test_market_indices()
