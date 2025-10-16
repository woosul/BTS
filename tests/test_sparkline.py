"""
CoinGecko 7일 추세 데이터 테스트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from application.services.market_index_service import MarketIndexService
from utils.logger import get_logger

logger = get_logger(__name__)

def test_sparkline():
    """7일 sparkline 데이터 테스트"""
    print("=" * 60)
    print("CoinGecko 7일 추세 데이터 테스트")
    print("=" * 60)
    
    service = MarketIndexService()
    
    print("\n상위 5개 코인 7일 추세 데이터 가져오기...")
    try:
        coins = service.get_top_coins_with_sparkline(limit=5)
        
        if coins:
            print(f"\n✓ {len(coins)}개 코인 데이터 가져오기 성공\n")
            
            for coin in coins:
                print(f"코인: {coin['name']} ({coin['symbol']})")
                print(f"  현재 가격: ${coin['current_price']:,.2f}")
                print(f"  시가총액 순위: {coin['market_cap_rank']}")
                print(f"  24시간 변동: {coin['price_change_percentage_24h']:.2f}%")
                print(f"  7일 변동: {coin['price_change_percentage_7d']:.2f}%")
                
                sparkline = coin['sparkline_in_7d']
                if sparkline and len(sparkline) > 0:
                    print(f"  Sparkline 데이터: {len(sparkline)}개 포인트")
                    print(f"  최소값: ${min(sparkline):,.2f}")
                    print(f"  최대값: ${max(sparkline):,.2f}")
                    print(f"  첫 값: ${sparkline[0]:,.2f}, 마지막 값: ${sparkline[-1]:,.2f}")
                else:
                    print(f"  Sparkline 데이터: 없음")
                print()
        else:
            print("\n✗ 데이터를 가져오지 못했습니다.")
            
    except Exception as e:
        print(f"\n✗ 에러 발생: {e}")
        logger.exception("Sparkline 테스트 실패")

if __name__ == "__main__":
    test_sparkline()
