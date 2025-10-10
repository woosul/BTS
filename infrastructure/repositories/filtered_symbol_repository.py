"""
필터링된 종목 Repository
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from infrastructure.repositories.base import BaseRepository
from infrastructure.database.models import FilteredSymbolORM
from domain.entities.filtered_symbol import FilteredSymbol
from utils.logger import logger


class FilteredSymbolRepository(BaseRepository[FilteredSymbolORM]):
    """필터링된 종목 Repository"""
    
    def __init__(self, db: Session):
        super().__init__(FilteredSymbolORM, db)
    
    def save_symbols(self, symbols_data: List[dict], profile_name: Optional[str] = None) -> bool:
        """
        필터링된 종목 목록 저장 (상세 데이터 포함)
        기존 데이터를 모두 삭제하고 새로 저장
        
        Args:
            symbols_data: 종목 상세 데이터 딕셔너리 리스트
                예: [{'symbol': 'KRW-BTC', 'korean_name': '비트코인', 'trading_value': 1000000, ...}, ...]
            profile_name: 필터 프로파일 명 (optional)
            
        Returns:
            성공 여부
        """
        try:
            # 1. 기존 데이터 모두 삭제
            deleted_count = self.db.query(FilteredSymbolORM).delete()
            logger.info(f"기존 필터링 결과 삭제: {deleted_count}개")
            
            # 2. 새로운 데이터 저장
            filtered_at = datetime.now()
            new_symbols = []
            for data in symbols_data:
                # symbol은 필수, 나머지는 optional
                # 'no' 필드는 UI 표시용이므로 저장하지 않음
                new_symbol = FilteredSymbolORM(
                    symbol=data.get('symbol') if isinstance(data, dict) else data,
                    profile_name=profile_name,
                    filtered_at=filtered_at,
                    korean_name=data.get('korean_name') if isinstance(data, dict) else None,
                    trading_value=data.get('trading_value') if isinstance(data, dict) else None,
                    market_cap=data.get('market_cap') if isinstance(data, dict) else None,
                    listing_days=data.get('listing_days') if isinstance(data, dict) else None,
                    current_price=data.get('current_price') if isinstance(data, dict) else None,
                    volatility=data.get('volatility') if isinstance(data, dict) else None,
                    spread=data.get('spread') if isinstance(data, dict) else None,
                    note=data.get('note', '') if isinstance(data, dict) else ''
                )
                new_symbols.append(new_symbol)
            
            self.db.add_all(new_symbols)
            self.db.commit()
            
            profile_info = f" (프로파일: {profile_name})" if profile_name else ""
            logger.info(f"필터링 결과 저장 완료: {len(symbols_data)}개 종목{profile_info}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"필터링 결과 저장 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_latest_symbols(self) -> List[dict]:
        """
        저장된 최신 필터링 결과 조회 (상세 데이터 포함)
        
        Returns:
            종목 상세 데이터 딕셔너리 리스트
        """
        try:
            symbols_orm = self.db.query(FilteredSymbolORM)\
                .order_by(FilteredSymbolORM.filtered_at.desc())\
                .all()
            
            result = []
            for symbol_orm in symbols_orm:
                result.append({
                    'symbol': symbol_orm.symbol,
                    'korean_name': symbol_orm.korean_name,
                    'trading_value': float(symbol_orm.trading_value) if symbol_orm.trading_value else None,
                    'market_cap': float(symbol_orm.market_cap) if symbol_orm.market_cap else None,
                    'listing_days': symbol_orm.listing_days,
                    'current_price': float(symbol_orm.current_price) if symbol_orm.current_price else None,
                    'volatility': float(symbol_orm.volatility) if symbol_orm.volatility else None,
                    'spread': float(symbol_orm.spread) if symbol_orm.spread else None,
                    'note': symbol_orm.note or ''
                })
            
            logger.info(f"저장된 필터링 결과 조회: {len(result)}개 종목")
            return result
            
        except Exception as e:
            logger.error(f"필터링 결과 조회 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_latest_filtered_at(self) -> Optional[datetime]:
        """
        마지막 필터링 시각 조회
        
        Returns:
            마지막 필터링 시각 (없으면 None)
        """
        try:
            result = self.db.query(FilteredSymbolORM.filtered_at)\
                .order_by(FilteredSymbolORM.filtered_at.desc())\
                .first()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"마지막 필터링 시각 조회 실패: {e}")
            return None
    
    def get_profile_name(self) -> Optional[str]:
        """
        저장된 필터링 결과의 프로파일명 조회
        
        Returns:
            프로파일명 (없으면 None)
        """
        try:
            result = self.db.query(FilteredSymbolORM.profile_name)\
                .order_by(FilteredSymbolORM.filtered_at.desc())\
                .first()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"프로파일명 조회 실패: {e}")
            return None
    
    def clear_all(self) -> bool:
        """
        모든 필터링 결과 삭제
        
        Returns:
            성공 여부
        """
        try:
            deleted_count = self.db.query(FilteredSymbolORM).delete()
            self.db.commit()
            
            logger.info(f"필터링 결과 전체 삭제: {deleted_count}개")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"필터링 결과 삭제 실패: {e}")
            return False
    
    def count(self) -> int:
        """
        저장된 종목 수 조회
        
        Returns:
            종목 수
        """
        try:
            return self.db.query(FilteredSymbolORM).count()
        except Exception as e:
            logger.error(f"종목 수 조회 실패: {e}")
            return 0
