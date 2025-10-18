#!/usr/bin/env python
"""UTC 시간을 로컬 시간으로 변환하는 마이그레이션 스크립트"""
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection import SessionLocal
from infrastructure.database.models import MarketIndexORM
from sqlalchemy import update


def migrate_utc_to_local():
    """모든 테이블의 UTC 시간을 로컬 시간으로 변환"""
    db = SessionLocal()
    
    try:
        print('\n' + '=' * 80)
        print('🔄 UTC → 로컬 시간 변환 시작')
        print('=' * 80 + '\n')
        
        # 한국 시간대 (UTC+9)
        KST_OFFSET = timedelta(hours=9)
        
        # 1. market_indices 테이블
        print('📊 market_indices 테이블 변환 중...')
        records = db.query(MarketIndexORM).all()
        
        total = len(records)
        print(f'   총 {total}개 레코드 발견')
        
        updated_count = 0
        for i, record in enumerate(records, 1):
            # UTC 시간에 9시간 추가
            if record.created_at:
                # naive datetime으로 저장되어 있으므로 UTC로 간주하고 9시간 추가
                record.created_at = record.created_at + KST_OFFSET
            
            if record.updated_at:
                record.updated_at = record.updated_at + KST_OFFSET
            
            updated_count += 1
            
            # 진행 상황 출력 (100개마다)
            if i % 100 == 0 or i == total:
                print(f'   진행: {i}/{total} ({i*100//total}%)')
        
        # 커밋
        db.commit()
        
        print(f'\n✅ 변환 완료: {updated_count}개 레코드')
        
        # 변환 결과 확인
        print('\n' + '=' * 80)
        print('📈 변환 결과 확인')
        print('=' * 80 + '\n')
        
        # 각 index_type별 최신 시간 출력
        index_types = db.query(MarketIndexORM.index_type).distinct().all()
        
        for (idx_type,) in index_types:
            latest = db.query(MarketIndexORM).filter(
                MarketIndexORM.index_type == idx_type
            ).order_by(MarketIndexORM.created_at.desc()).first()
            
            if latest:
                print(f'[{idx_type.upper()}] 최신: {latest.created_at.strftime("%Y-%m-%d %H:%M:%S")} (로컬 시간)')
        
        print('\n' + '=' * 80)
        print('✅ 마이그레이션 완료!')
        print('=' * 80 + '\n')
        
    except Exception as e:
        print(f'\n❌ 오류 발생: {e}')
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    # 확인 메시지
    print('\n⚠️  경고: 이 스크립트는 DB의 모든 시간 데이터를 UTC에서 로컬 시간으로 변환합니다.')
    print('   변환 후에는 되돌릴 수 없습니다.\n')
    
    response = input('계속하시겠습니까? (yes/no): ')
    
    if response.lower() in ['yes', 'y']:
        migrate_utc_to_local()
    else:
        print('\n취소되었습니다.')
