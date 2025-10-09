"""
필터링 서비스

스크리닝 전 종목 필터링 로직
"""
import time
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from domain.entities.filter_profile import (
    FilterProfile,
    FilterStats,
    FilterProfileCreate,
    FilterProfileUpdate
)
from infrastructure.repositories.filter_profile_repository import FilterProfileRepository
from infrastructure.repositories.filtered_symbol_repository import FilteredSymbolRepository
from infrastructure.exchanges.base_exchange import BaseExchange
from utils.logger import get_logger

logger = get_logger(__name__)


class FilteringService:
    """필터링 서비스"""
    
    def __init__(self, db: Session, exchange: BaseExchange):
        self.db = db
        self.exchange = exchange
        self.repo = FilterProfileRepository(db)
        self.filtered_symbol_repo = FilteredSymbolRepository(db)
        # 필터링 과정에서 수집된 데이터 캐시
        self._symbol_data_cache: Dict[str, Dict[str, Any]] = {}
        logger.info("FilteringService 초기화 완료")
    
    def apply_filters(
        self,
        symbols: List[str],
        profile: FilterProfile,
        return_stats: bool = True
    ) -> Tuple[List[str], List[FilterStats]]:
        """
        필터 프로파일을 적용하여 종목 필터링
        
        Args:
            symbols: 필터링할 종목 리스트
            profile: 적용할 필터 프로파일
            return_stats: 통계 정보 반환 여부
        
        Returns:
            (필터링된 종목 리스트, 필터 통계 리스트)
        """
        logger.info(f"필터링 시작: 프로파일={profile.name}, 초기 종목 수={len(symbols)}")
        
        filtered_symbols = symbols.copy()
        stats_list = []
        conditions = profile.conditions
        
        # 0단계: 상장폐지 및 거래정지 필터
        if conditions.enabled and (conditions.exclude_delisting or conditions.exclude_suspended):
            filtered_symbols, stats = self._filter_delisting_suspended(
                filtered_symbols,
                conditions.exclude_delisting,
                conditions.exclude_suspended
            )
            if return_stats:
                stats_list.append(stats)
        
        # 1단계: 거래대금 필터
        if conditions.enabled and conditions.min_trading_value:
            filtered_symbols, stats = self._filter_trading_value(
                filtered_symbols,
                conditions.min_trading_value
            )
            if return_stats:
                stats_list.append(stats)
        
        # 2단계: 시가총액 필터
        if conditions.enabled and (conditions.min_market_cap or conditions.max_market_cap):
            filtered_symbols, stats = self._filter_market_cap(
                filtered_symbols,
                conditions.min_market_cap,
                conditions.max_market_cap
            )
            if return_stats:
                stats_list.append(stats)
        
        # 3단계: 상장기간 필터
        if conditions.enabled and conditions.min_listing_days:
            filtered_symbols, stats = self._filter_listing_period(
                filtered_symbols,
                conditions.min_listing_days
            )
            if return_stats:
                stats_list.append(stats)
        
        # 4단계: 가격범위 필터
        if conditions.enabled and (conditions.min_price or conditions.max_price):
            filtered_symbols, stats = self._filter_price_range(
                filtered_symbols,
                conditions.min_price,
                conditions.max_price
            )
            if return_stats:
                stats_list.append(stats)
        
        # 5단계: 변동성 필터
        if conditions.enabled and (conditions.min_volatility or conditions.max_volatility):
            filtered_symbols, stats = self._filter_volatility(
                filtered_symbols,
                conditions.min_volatility,
                conditions.max_volatility
            )
            if return_stats:
                stats_list.append(stats)
        
        # 6단계: 스프레드 필터
        if conditions.enabled and conditions.max_spread:
            filtered_symbols, stats = self._filter_spread(
                filtered_symbols,
                conditions.max_spread
            )
            if return_stats:
                stats_list.append(stats)
        
        logger.info(f"필터링 완료: 최종 종목 수={len(filtered_symbols)} ({len(symbols)} → {len(filtered_symbols)})")
        
        return filtered_symbols, stats_list
    
    def get_symbol_details(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        종목들의 상세 데이터 조회 (캐시 데이터 사용)
        
        Args:
            symbols: 조회할 종목 리스트
            
        Returns:
            종목별 상세 데이터 딕셔너리 리스트
        """
        details = []
        
        logger.info(f"캐시된 데이터로 상세 정보 생성: {len(symbols)}개 종목")
        
        try:
            # 캐시된 데이터 사용
            for i, symbol in enumerate(symbols, 1):
                cached_data = self._symbol_data_cache.get(symbol, {})
                
                detail = {
                    'no': i,
                    'symbol': symbol,
                    'korean_name': cached_data.get('korean_name', '-'),
                    'trading_value': cached_data.get('trading_value'),
                    'market_cap': cached_data.get('market_cap'),  # None (API 제한)
                    'listing_days': cached_data.get('listing_days'),  # None (API 제한)
                    'current_price': cached_data.get('current_price'),
                    'volatility': cached_data.get('volatility'),
                    'spread': cached_data.get('spread'),
                    'note': ''
                }
                
                details.append(detail)
            
            logger.info(f"상세 데이터 생성 완료: {len(details)}개 종목")
            
            # 캐시 통계 로깅
            with_volatility = sum(1 for d in details if d['volatility'] is not None)
            with_spread = sum(1 for d in details if d['spread'] is not None)
            logger.info(f"캐시 데이터: 변동성={with_volatility}/{len(details)}, 스프레드={with_spread}/{len(details)}")
                
        except Exception as e:
            logger.error(f"종목 상세 데이터 조회 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        return details
    
    def _filter_delisting_suspended(
        self,
        symbols: List[str],
        exclude_delisting: bool,
        exclude_suspended: bool
    ) -> Tuple[List[str], FilterStats]:
        """0단계: 상장폐지 및 거래정지 필터"""
        start_time = time.time()
        before_count = len(symbols)
        
        filtered = []
        for symbol in symbols:
            try:
                # Upbit는 실제로 거래 가능한 종목만 반환하므로
                # 이 필터는 대부분의 경우 모든 종목을 통과시킴
                # 다만 market_warning 체크는 추가 가능
                filtered.append(symbol)
            except Exception as e:
                logger.debug(f"{symbol} 상장/거래 상태 확인 실패: {e}")
                continue
        
        execution_time = (time.time() - start_time) * 1000
        after_count = len(filtered)
        filtered_count = before_count - after_count
        filtered_pct = (filtered_count / before_count * 100) if before_count > 0 else 0
        
        stats = FilterStats(
            stage_name="0. 상장폐지/거래정지",
            symbols_before=before_count,
            symbols_after=after_count,
            filtered_count=filtered_count,
            filtered_percentage=filtered_pct,
            execution_time_ms=execution_time
        )
        
        logger.info(f"필터 적용 | {stats.stage_name} | {before_count} → {after_count} (-{filtered_count}개)")
        return filtered, stats
    
    def _filter_trading_value(
        self,
        symbols: List[str],
        min_value: float
    ) -> Tuple[List[str], FilterStats]:
        """1단계: 거래대금 필터"""
        start_time = time.time()
        before_count = len(symbols)
        
        logger.info(f"거래대금 필터 시작: 최소값={min_value:,.0f}원 ({min_value/1e8:.1f}억원)")
        
        filtered = []
        sample_count = 0
        
        try:
            # 배치로 모든 종목의 ticker 조회 (Rate Limit 방지)
            tickers = self.exchange.get_tickers_batch(symbols)
            
            for symbol in symbols:
                try:
                    ticker = tickers.get(symbol)
                    
                    if ticker:
                        trading_value = ticker.get('acc_trade_price_24h', 0)
                        current_price = ticker.get('trade_price', 0)
                        
                        # 데이터 캐시에 저장
                        if symbol not in self._symbol_data_cache:
                            self._symbol_data_cache[symbol] = {}
                        self._symbol_data_cache[symbol]['trading_value'] = trading_value
                        self._symbol_data_cache[symbol]['current_price'] = current_price
                        self._symbol_data_cache[symbol]['korean_name'] = ticker.get('korean_name', '-')
                        
                        # 처음 3개 종목은 샘플로 로그 출력
                        if sample_count < 3:
                            logger.info(f"[샘플] {symbol}: 거래대금={trading_value:,.0f}원 ({trading_value/1e8:.1f}억원), 기준={min_value/1e8:.1f}억원, 통과={trading_value >= min_value}")
                            sample_count += 1
                        
                        if trading_value >= min_value:
                            filtered.append(symbol)
                    else:
                        logger.debug(f"{symbol} ticker 데이터 없음")
                        
                except Exception as e:
                    logger.error(f"{symbol} 거래대금 처리 실패: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"배치 ticker 조회 실패: {e}")
            # 배치 조회 실패 시 개별 조회로 폴백하지 않고 빈 결과 반환
            filtered = []
        
        execution_time = (time.time() - start_time) * 1000
        after_count = len(filtered)
        filtered_count = before_count - after_count
        filtered_pct = (filtered_count / before_count * 100) if before_count > 0 else 0
        
        stats = FilterStats(
            stage_name=f"1. 거래대금 (>={min_value/1e8:.1f}억원)",
            symbols_before=before_count,
            symbols_after=after_count,
            filtered_count=filtered_count,
            filtered_percentage=filtered_pct,
            execution_time_ms=execution_time
        )
        
        logger.info(f"필터 적용 | {stats.stage_name} | {before_count} → {after_count} (-{filtered_count}개)")
        return filtered, stats
    
    def _filter_market_cap(
        self,
        symbols: List[str],
        min_cap: Optional[float],
        max_cap: Optional[float]
    ) -> Tuple[List[str], FilterStats]:
        """2단계: 시가총액 필터"""
        start_time = time.time()
        before_count = len(symbols)
        
        logger.info(f"시가총액 필터 시작: 최소={min_cap/1e8 if min_cap else 0:.1f}억원, 최대={max_cap/1e8 if max_cap else 0:.1f}억원")
        
        filtered = []
        sample_count = 0
        
        try:
            # 배치로 모든 종목의 ticker 조회
            tickers = self.exchange.get_tickers_batch(symbols)
            
            for symbol in symbols:
                try:
                    ticker = tickers.get(symbol)
                    
                    if ticker:
                        trading_value = ticker.get('acc_trade_price_24h', 0)
                        
                        # 24시간 거래대금을 시가총액의 대용치로 사용
                        market_cap_proxy = trading_value * 100
                        
                        # 데이터 캐시에 저장
                        if symbol not in self._symbol_data_cache:
                            self._symbol_data_cache[symbol] = {}
                        self._symbol_data_cache[symbol]['market_cap'] = market_cap_proxy
                        
                        # 처음 3개 종목은 샘플로 로그 출력
                        if sample_count < 3:
                            logger.info(f"[샘플] {symbol}: 추정시가총액={market_cap_proxy/1e8:.1f}억원, 기준=최소{min_cap/1e8 if min_cap else 0:.1f}억~최대{max_cap/1e8 if max_cap else '무제한'}억")
                            sample_count += 1
                        
                        if min_cap and market_cap_proxy < min_cap:
                            continue
                        if max_cap and market_cap_proxy > max_cap:
                            continue
                        
                        filtered.append(symbol)
                except Exception as e:
                    logger.error(f"{symbol} 시가총액 처리 실패: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"배치 ticker 조회 실패: {e}")
            filtered = []
        
        execution_time = (time.time() - start_time) * 1000
        after_count = len(filtered)
        filtered_count = before_count - after_count
        filtered_pct = (filtered_count / before_count * 100) if before_count > 0 else 0
        
        min_str = f">={min_cap/1e8:.0f}억" if min_cap else ""
        max_str = f"<={max_cap/1e8:.0f}억" if max_cap else ""
        range_str = f"{min_str} {max_str}".strip()
        
        stats = FilterStats(
            stage_name=f"2. 시가총액 ({range_str})" if range_str else "2. 시가총액",
            symbols_before=before_count,
            symbols_after=after_count,
            filtered_count=filtered_count,
            filtered_percentage=filtered_pct,
            execution_time_ms=execution_time
        )
        
        logger.info(f"필터 적용 | {stats.stage_name} | {before_count} → {after_count} (-{filtered_count}개)")
        return filtered, stats
    
    def _filter_listing_period(
        self,
        symbols: List[str],
        min_days: int
    ) -> Tuple[List[str], FilterStats]:
        """3단계: 상장기간 필터"""
        start_time = time.time()
        before_count = len(symbols)
        
        from datetime import datetime
        
        logger.info(f"상장기간 필터 시작: 최소={min_days}일 (종목 수: {len(symbols)}개)")
        
        filtered = []
        sample_count = 0
        
        # Rate Limit: Quotation candle API는 초당 10개 요청 제한
        # 안전하게 5개씩 배치로 묶어서 처리 (안전 마진 확보)
        # 주의: 이 필터는 시간이 오래 걸리므로 자주 사용하지 말 것
        batch_size = 5
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i+batch_size]
            
            # 배치 시작 (모든 배치에서 1.5초 대기)
            if i > 0:
                logger.info(f"Rate Limit 방지: 1.5초 대기 (진행: {i}/{len(symbols)}개)")
                time.sleep(1.5)
            
            for symbol in batch_symbols:
                try:
                    # OHLCV 데이터로 상장 기간 확인
                    # 일봉 데이터를 요청 (Upbit는 최대 200개까지 반환)
                    ohlcv_list = self.exchange.get_ohlcv(symbol, interval='day', limit=200)
                    
                    if ohlcv_list and len(ohlcv_list) > 0:
                        # 가장 오래된 데이터 (리스트의 첫 번째 OHLCV 객체)
                        first_candle = ohlcv_list[0]
                        first_date = first_candle.timestamp
                        
                        # timezone 처리: aware datetime을 naive로 변환
                        if first_date.tzinfo is not None:
                            first_date = first_date.replace(tzinfo=None)
                        
                        # 실제 상장일 = 첫 번째 데이터의 날짜
                        # 상장 기간 = 현재 - 상장일
                        days_since_listing = (datetime.now() - first_date).days
                        
                        # 데이터 캐시에 저장
                        if symbol not in self._symbol_data_cache:
                            self._symbol_data_cache[symbol] = {}
                        self._symbol_data_cache[symbol]['listing_days'] = days_since_listing
                        
                        # 처음 3개 종목은 샘플로 로그 출력
                        if sample_count < 3:
                            logger.info(f"[샘플] {symbol}: 상장기간={days_since_listing}일 (첫 데이터: {first_date.strftime('%Y-%m-%d')}), 기준={min_days}일, 통과={days_since_listing >= min_days}")
                            sample_count += 1
                        
                        # 상장 기간이 기준 이상이면 통과
                        if days_since_listing >= min_days:
                            filtered.append(symbol)
                    else:
                        # 데이터가 없으면 제외 (신규 상장 또는 거래 중단)
                        logger.warning(f"{symbol} OHLCV 데이터 없음 - 제외")
                        continue
                        
                except Exception as e:
                    # OHLCV 조회 실패 (신규 상장, 거래 중단, API 오류 등)
                    logger.warning(f"{symbol} 상장기간 확인 실패 - 제외 (사유: {str(e)[:100]})")
                    continue
        
        execution_time = (time.time() - start_time) * 1000
        after_count = len(filtered)
        filtered_count = before_count - after_count
        filtered_pct = (filtered_count / before_count * 100) if before_count > 0 else 0
        
        stats = FilterStats(
            stage_name=f"3. 상장기간 (>={min_days}일)",
            symbols_before=before_count,
            symbols_after=after_count,
            filtered_count=filtered_count,
            filtered_percentage=filtered_pct,
            execution_time_ms=execution_time
        )
        
        logger.info(f"필터 적용 | {stats.stage_name} | {before_count} → {after_count} (-{filtered_count}개)")
        return filtered, stats
    
    def _filter_price_range(
        self,
        symbols: List[str],
        min_price: Optional[float],
        max_price: Optional[float]
    ) -> Tuple[List[str], FilterStats]:
        """4단계: 가격범위 필터"""
        start_time = time.time()
        before_count = len(symbols)
        
        logger.info(f"가격범위 필터 시작: 최소={min_price:,.0f}원, 최대={max_price:,.0f}원" if min_price or max_price else "가격범위 필터 시작")
        
        filtered = []
        sample_count = 0
        
        try:
            # 배치로 모든 종목의 ticker 조회
            tickers = self.exchange.get_tickers_batch(symbols)
            
            for symbol in symbols:
                try:
                    ticker = tickers.get(symbol)
                    
                    if ticker:
                        price = ticker.get('trade_price', 0)
                        
                        # 처음 3개 종목은 샘플로 로그 출력
                        if sample_count < 3:
                            min_str = f"{min_price:,.0f}" if min_price else "0"
                            max_str = f"{max_price:,.0f}" if max_price else "무제한"
                            logger.info(f"[샘플] {symbol}: 가격={price:,.0f}원, 기준=최소{min_str}~최대{max_str}원")
                            sample_count += 1
                        
                        if min_price and price < min_price:
                            continue
                        if max_price and price > max_price:
                            continue
                        
                        filtered.append(symbol)
                except Exception as e:
                    logger.error(f"{symbol} 가격 처리 실패: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"배치 ticker 조회 실패: {e}")
            filtered = []
        
        execution_time = (time.time() - start_time) * 1000
        after_count = len(filtered)
        filtered_count = before_count - after_count
        filtered_pct = (filtered_count / before_count * 100) if before_count > 0 else 0
        
        min_str = f"{min_price:,.0f}원" if min_price else ""
        max_str = f"{max_price:,.0f}원" if max_price else ""
        range_str = f"{min_str} ~ {max_str}".strip() if min_str and max_str else (min_str or max_str)
        
        stats = FilterStats(
            stage_name=f"4. 가격범위 ({range_str})" if range_str else "4. 가격범위",
            symbols_before=before_count,
            symbols_after=after_count,
            filtered_count=filtered_count,
            filtered_percentage=filtered_pct,
            execution_time_ms=execution_time
        )
        
        logger.info(f"필터 적용 | {stats.stage_name} | {before_count} → {after_count} (-{filtered_count}개)")
        return filtered, stats
    
    def _filter_volatility(
        self,
        symbols: List[str],
        min_vol: Optional[float],
        max_vol: Optional[float]
    ) -> Tuple[List[str], FilterStats]:
        """5단계: 변동성 필터 (7일 기준)"""
        start_time = time.time()
        before_count = len(symbols)
        
        logger.info(f"변동성 필터 시작: 최소={min_vol}%, 최대={max_vol}% (종목 수: {len(symbols)}개)")
        
        filtered = []
        sample_count = 0
        
        # Rate Limit: Quotation candle API는 초당 10개 요청 제한
        # 안전하게 5개씩 배치로 묶어서 처리
        batch_size = 5
        
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i+batch_size]
            
            # 배치 시작 전 대기 (첫 배치 제외)
            if i > 0:
                logger.info(f"Rate Limit 방지: 1.5초 대기 (진행: {i}/{len(symbols)}개)")
                time.sleep(1.5)
            
            for symbol in batch_symbols:
                try:
                    # 7일간 OHLCV 데이터로 변동성 계산
                    ohlcv_list = self.exchange.get_ohlcv(symbol, interval='day', limit=7)
                    if ohlcv_list and len(ohlcv_list) >= 7:
                        # 일일 변동률 계산
                        daily_changes_sum = 0
                        for candle in ohlcv_list:
                            daily_change = (float(candle.high) - float(candle.low)) / float(candle.low) * 100
                            daily_changes_sum += daily_change
                        
                        avg_volatility = daily_changes_sum / len(ohlcv_list)
                        
                        # 데이터 캐시에 저장
                        if symbol not in self._symbol_data_cache:
                            self._symbol_data_cache[symbol] = {}
                        self._symbol_data_cache[symbol]['volatility'] = avg_volatility
                        
                        # 처음 3개 종목은 샘플로 로그 출력
                        if sample_count < 3:
                            logger.info(f"[샘플] {symbol}: 변동성={avg_volatility:.2f}%, 기준=최소{min_vol}~최대{max_vol}%")
                            sample_count += 1
                        
                        if min_vol and avg_volatility < min_vol:
                            continue
                        if max_vol and avg_volatility > max_vol:
                            continue
                        
                        filtered.append(symbol)
                except Exception as e:
                    logger.error(f"{symbol} 변동성 계산 실패: {e}")
                    continue
        
        execution_time = (time.time() - start_time) * 1000
        after_count = len(filtered)
        filtered_count = before_count - after_count
        filtered_pct = (filtered_count / before_count * 100) if before_count > 0 else 0
        
        min_str = f"{min_vol}%" if min_vol else ""
        max_str = f"{max_vol}%" if max_vol else ""
        range_str = f"{min_str} ~ {max_str}".strip() if min_str and max_str else (min_str or max_str)
        
        stats = FilterStats(
            stage_name=f"5. 변동성 ({range_str})" if range_str else "5. 변동성",
            symbols_before=before_count,
            symbols_after=after_count,
            filtered_count=filtered_count,
            filtered_percentage=filtered_pct,
            execution_time_ms=execution_time
        )
        
        logger.info(f"필터 적용 | {stats.stage_name} | {before_count} → {after_count} (-{filtered_count}개)")
        return filtered, stats
    
    def _filter_spread(
        self,
        symbols: List[str],
        max_spread_pct: float
    ) -> Tuple[List[str], FilterStats]:
        """6단계: 스프레드 필터"""
        start_time = time.time()
        before_count = len(symbols)
        
        logger.info(f"스프레드 필터 시작: 최대={max_spread_pct}%")
        
        filtered = []
        sample_count = 0
        for symbol in symbols:
            try:
                orderbook = self.exchange.get_orderbook(symbol)
                
                if orderbook:
                    if isinstance(orderbook, dict) and 'orderbook_units' in orderbook:
                        units = orderbook['orderbook_units']
                    else:
                        units = getattr(orderbook, 'orderbook_units', [])
                    
                    if units and len(units) > 0:
                        # 1호가 매수/매도가
                        if isinstance(units[0], dict):
                            best_bid = units[0].get('bid_price', 0)
                            best_ask = units[0].get('ask_price', 0)
                        else:
                            best_bid = getattr(units[0], 'bid_price', 0)
                            best_ask = getattr(units[0], 'ask_price', 0)
                        
                        if best_bid > 0:
                            spread_pct = (best_ask - best_bid) / best_bid * 100
                            
                            # 데이터 캐시에 저장
                            if symbol not in self._symbol_data_cache:
                                self._symbol_data_cache[symbol] = {}
                            self._symbol_data_cache[symbol]['spread'] = spread_pct
                            
                            # 처음 3개 종목은 샘플로 로그 출력
                            if sample_count < 3:
                                logger.info(f"[샘플] {symbol}: 스프레드={spread_pct:.3f}%, 기준=<={max_spread_pct}%")
                                sample_count += 1
                            
                            if spread_pct <= max_spread_pct:
                                filtered.append(symbol)
            except Exception as e:
                logger.error(f"{symbol} 스프레드 조회 실패: {e}")
                continue
        
        execution_time = (time.time() - start_time) * 1000
        after_count = len(filtered)
        filtered_count = before_count - after_count
        filtered_pct = (filtered_count / before_count * 100) if before_count > 0 else 0
        
        stats = FilterStats(
            stage_name=f"6. 스프레드 (<={max_spread_pct}%)",
            symbols_before=before_count,
            symbols_after=after_count,
            filtered_count=filtered_count,
            filtered_percentage=filtered_pct,
            execution_time_ms=execution_time
        )
        
        logger.info(f"필터 적용 | {stats.stage_name} | {before_count} → {after_count} (-{filtered_count}개)")
        return filtered, stats
    
    # Repository 메서드 래핑
    def create_profile(self, profile_data: 'FilterProfileCreate') -> FilterProfile:
        """필터 프로파일 생성"""
        return self.repo.create(profile_data)
    
    def get_profile(self, profile_id: int) -> Optional[FilterProfile]:
        """필터 프로파일 조회"""
        return self.repo.get_by_id(profile_id)
    
    def get_profile_by_name(self, name: str) -> Optional[FilterProfile]:
        """이름으로 프로파일 조회"""
        return self.repo.get_by_name(name)
    
    def get_all_profiles(self, market: Optional[str] = None) -> List[FilterProfile]:
        """모든 프로파일 조회"""
        if market:
            return self.repo.get_by_market(market)
        return self.repo.get_all()
    
    def get_active_profiles(self, market: Optional[str] = None) -> List[FilterProfile]:
        """활성화된 프로파일 조회"""
        return self.repo.get_active_profiles(market)
    
    def update_profile(self, profile_id: int, update_data: 'FilterProfileUpdate') -> Optional[FilterProfile]:
        """필터 프로파일 수정"""
        return self.repo.update(profile_id, update_data)
    
    def delete_profile(self, profile_id: int) -> bool:
        """필터 프로파일 삭제"""
        return self.repo.delete(profile_id)
    
    def activate_profile(self, profile_id: int) -> bool:
        """프로파일 활성화"""
        return self.repo.activate(profile_id)
    
    def deactivate_profile(self, profile_id: int) -> bool:
        """프로파일 비활성화"""
        return self.repo.deactivate(profile_id)
    
    # ===== 필터링 결과 저장/조회 =====
    
    def save_filtered_symbols(self, symbols: List[str], profile_name: Optional[str] = None) -> bool:
        """
        필터링 결과를 DB에 저장
        기존 데이터는 모두 삭제됨
        
        Args:
            symbols: 필터링된 종목 코드 리스트
            profile_name: 필터 프로파일명 (optional)
            
        Returns:
            성공 여부
        """
        try:
            return self.filtered_symbol_repo.save_symbols(symbols, profile_name)
        except Exception as e:
            logger.error(f"필터링 결과 저장 실패: {e}")
            return False
    
    def get_saved_symbols(self) -> List[str]:
        """
        저장된 필터링 결과 조회
        
        Returns:
            종목 코드 리스트
        """
        try:
            return self.filtered_symbol_repo.get_latest_symbols()
        except Exception as e:
            logger.error(f"저장된 필터링 결과 조회 실패: {e}")
            return []
    
    def get_saved_symbols_count(self) -> int:
        """
        저장된 종목 수 조회
        
        Returns:
            종목 수
        """
        try:
            return self.filtered_symbol_repo.count()
        except Exception as e:
            logger.error(f"저장된 종목 수 조회 실패: {e}")
            return 0
    
    def get_last_filtered_time(self) -> Optional[str]:
        """
        마지막 필터링 시각 조회
        
        Returns:
            마지막 필터링 시각 (포맷: YYYY-MM-DD HH:MM:SS)
        """
        try:
            filtered_at = self.filtered_symbol_repo.get_latest_filtered_at()
            if filtered_at:
                return filtered_at.strftime('%Y-%m-%d %H:%M:%S')
            return None
        except Exception as e:
            logger.error(f"마지막 필터링 시각 조회 실패: {e}")
            return None
    
    def get_saved_profile_name(self) -> Optional[str]:
        """
        저장된 필터링 결과의 프로파일명 조회
        
        Returns:
            프로파일명
        """
        try:
            return self.filtered_symbol_repo.get_profile_name()
        except Exception as e:
            logger.error(f"저장된 프로파일명 조회 실패: {e}")
            return None
