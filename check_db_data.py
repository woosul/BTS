#!/usr/bin/env python
"""DB 전체 지수 데이터 확인 스크립트"""
import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection import SessionLocal
from infrastructure.database.models import MarketIndexORM


def check_all_indices():
    """모든 index_type별 최신 데이터 확인"""
    db = SessionLocal()
    try:
        print('\n' + '=' * 80)
        print('📊 전체 지수 데이터 현황')
        print('=' * 80)
        
        # index_type별 그룹화
        index_types = db.query(MarketIndexORM.index_type).distinct().all()
        
        # DB는 이제 로컬 시간으로 저장됨
        recent_time = datetime.now() - timedelta(minutes=10)
        
        for (idx_type,) in index_types:
            # 최신 레코드 조회
            latest = db.query(MarketIndexORM).filter(
                MarketIndexORM.index_type == idx_type
            ).order_by(MarketIndexORM.created_at.desc()).first()
            
            # 최근 10분간 레코드 수
            recent_count = db.query(MarketIndexORM).filter(
                MarketIndexORM.index_type == idx_type,
                MarketIndexORM.created_at >= recent_time
            ).count()
            
            if latest:
                time_diff = datetime.now() - latest.created_at
                minutes_ago = int(time_diff.total_seconds() / 60)
                
                status = '✅' if minutes_ago < 10 else '⚠️'
                print(f'\n{status} [{idx_type.upper()}]')
                print(f'   최신 데이터: {latest.created_at.strftime("%Y-%m-%d %H:%M:%S")} ({minutes_ago}분 전)')
                print(f'   최근 10분간: {recent_count}개')
                print(f'   대표 코드: {latest.code}')
                
    finally:
        db.close()


def _print_coin_records(records, coin_symbols):
    """코인 레코드 출력 헬퍼 함수"""
    if not records:
        print('   ❌ 데이터 없음\n')
        return
    
    # 헤더
    header = f'   {"시간":<20}'
    for coin_name in coin_symbols:
        header += f' | {coin_name:^25}'
    print(header)
    print('   ' + '=' * (20 + len(coin_symbols) * 28))
    
    # 심볼 → ID 매핑 (Binance는 심볼, CoinGecko는 ID 사용)
    symbol_to_id = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'SOL': 'solana',
        'BNB': 'binancecoin',
        'XRP': 'ripple',
        'USDT': 'tether',
        'USDC': 'usd-coin',
        'ADA': 'cardano',
        'DOGE': 'dogecoin',
        'TRX': 'tron',
        'AVAX': 'avalanche-2'
    }
    
    # 각 레코드 출력
    for r in records[:5]:  # 최근 5개만
        time_str = r.created_at.strftime('%Y-%m-%d %H:%M:%S')
        
        if not r.extra_data:
            print(f'   {time_str:<20} | ❌ 데이터 없음')
            continue
        
        try:
            coins_data = json.loads(r.extra_data)
            if isinstance(coins_data, str):
                coins_data = json.loads(coins_data)
            
            if not isinstance(coins_data, list):
                print(f'   {time_str:<20} | ❌ 형식 오류')
                continue
            
            # 심볼별 데이터 추출
            coin_display = {}
            for coin in coins_data:
                symbol = coin.get('symbol', '').upper()
                coin_id = coin.get('id', '').lower()
                
                # 심볼 또는 ID로 매칭
                matched_symbol = None
                if symbol in coin_symbols:
                    matched_symbol = symbol
                else:
                    # ID로 역매칭
                    for s, cid in symbol_to_id.items():
                        if cid == coin_id and s in coin_symbols:
                            matched_symbol = s
                            break
                
                if matched_symbol:
                    price = float(coin.get('current_price', 0))
                    change = float(coin.get('price_change_percentage_24h', 0))
                    
                    # 가격 포맷
                    if price < 1:
                        price_str = f'${price:.4f}'
                    elif price < 1000:
                        price_str = f'${price:,.2f}'
                    else:
                        price_str = f'${price:,.0f}'
                    
                    # 변동 화살표
                    arrow = '🔴' if change < 0 else '🟢'
                    coin_display[matched_symbol] = f'{price_str} {arrow}{change:+.1f}%'
            
            # 한 줄 출력
            row = f'   {time_str:<20}'
            for sym in coin_symbols:
                data = coin_display.get(sym, 'N/A')
                row += f' | {data:^25}'
            print(row)
            
        except Exception as e:
            print(f'   {time_str:<20} | ❌ 파싱 오류: {str(e)[:40]}')
    
    print(f'\n   ✅ 총 {len(records)}개 시계열 데이터 (최근 5개 표시)\n')


def check_coingecko_markets():
    """Top Coins 데이터 상세 확인 - Binance/CoinGecko 소스별 시계열"""
    db = SessionLocal()
    try:
        print('\n' + '=' * 80)
        print('🪙 상위 코인 데이터 상세 (API 소스별)')
        print('=' * 80 + '\n')
        
        # 1. Binance 데이터
        print('� [Binance 실시간 데이터]')
        binance_records = db.query(MarketIndexORM).filter(
            MarketIndexORM.index_type == 'coin',
            MarketIndexORM.code == 'top_coins',
            MarketIndexORM.api_source == 'binance'
        ).order_by(MarketIndexORM.created_at.desc()).limit(10).all()
        _print_coin_records(binance_records, ['BTC', 'ETH', 'SOL', 'BNB', 'XRP'])
        
        # 2. CoinGecko 데이터
        print('🔸 [CoinGecko Fallback 데이터]')
        coingecko_records = db.query(MarketIndexORM).filter(
            MarketIndexORM.index_type == 'coin',
            MarketIndexORM.code == 'top_coins',
            MarketIndexORM.api_source == 'coingecko'
        ).order_by(MarketIndexORM.created_at.desc()).limit(10).all()
        _print_coin_records(coingecko_records, ['BTC', 'ETH', 'USDT', 'BNB', 'XRP'])
        
        # 3. 레거시 데이터 (하위 호환성 확인용)
        print('🔸 [레거시 데이터 (구버전 coingecko_top_coins)]')
        legacy_records = db.query(MarketIndexORM).filter(
            MarketIndexORM.index_type == 'coin',
            MarketIndexORM.code == 'coingecko_top_coins'
        ).order_by(MarketIndexORM.created_at.desc()).limit(10).all()
        _print_coin_records(legacy_records, ['BTC', 'ETH', 'USDT', 'BNB', 'XRP'])
        
    finally:
        db.close()


def check_global_data():
    """CoinGecko Global 데이터 확인"""
    db = SessionLocal()
    try:
        print('\n' + '=' * 80)
        print('📈 CoinGecko Global 데이터 상세')
        print('=' * 80 + '\n')
        
        records = db.query(MarketIndexORM).filter(
            MarketIndexORM.index_type == 'global'
        ).order_by(MarketIndexORM.created_at.desc()).limit(5).all()
        
        if not records:
            print('❌ 데이터가 없습니다.\n')
            return
        
        for r in records:
            time_str = r.created_at.strftime('%Y-%m-%d %H:%M:%S')
            print(f'{time_str} - {r.name}: ${r.value:,.0f} ({r.change_rate:+.2f}%)')
        
    finally:
        db.close()


def check_upbit_data():
    """업비트 지수 데이터 확인"""
    db = SessionLocal()
    try:
        print('\n' + '=' * 80)
        print('📊 업비트 지수 데이터 상세')
        print('=' * 80 + '\n')
        
        records = db.query(MarketIndexORM).filter(
            MarketIndexORM.index_type == 'upbit'
        ).order_by(MarketIndexORM.created_at.desc()).limit(5).all()
        
        if not records:
            print('❌ 데이터가 없습니다.\n')
            return
        
        for r in records:
            time_str = r.created_at.strftime('%Y-%m-%d %H:%M:%S')
            print(f'{time_str} - {r.code}: {r.value:,.2f} ({r.change_rate:+.2f}%)')
        
    finally:
        db.close()


def main():
    """전체 확인 실행"""
    try:
        check_all_indices()
        check_coingecko_markets()
        check_global_data()
        check_upbit_data()
        
        print('\n' + '=' * 80)
        print('💡 모든 시간은 시스템 로컬 시간입니다 (KST)')
        print('=' * 80 + '\n')
        
    except Exception as e:
        print('\n❌ 오류 발생: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
