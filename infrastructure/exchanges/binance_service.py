"""
Binance API 서비스

실시간 시장 데이터 조회를 위한 Binance Public API 클라이언트
- API Key 불필요 (Public API)
- Rate Limit: 1200 requests/minute (Weight 기반)
- 업데이트 주기: 실시간 (초 단위)
"""

import requests
from typing import Dict, List, Optional
from datetime import datetime
from config.market_index_config import MarketIndexConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class BinanceService:
    """Binance Public API 서비스"""
    
    BASE_URL = "https://api.binance.com"
    
    def __init__(self, timeout: Optional[int] = None):
        """
        Args:
            timeout: API 요청 타임아웃 (초, None이면 설정값 사용)
        """
        self.timeout = timeout or MarketIndexConfig.TIMEOUT_BINANCE_API
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'BTS/1.0'
        })
        
        # 주요 코인 심볼 매핑 (설정에서 로드)
        self.major_symbols = self._build_symbol_mapping()
        logger.info(f"Binance API 서비스 초기화 완료 (타임아웃: {self.timeout}초, 코인: {len(self.major_symbols)}개)")
    
    def _build_symbol_mapping(self) -> Dict[str, str]:
        """
        설정에서 주요 코인 심볼 매핑 생성
        
        Returns:
            Dict[str, str]: {코인심볼: Binance페어} 매핑
        """
        mapping = {}
        for coin in MarketIndexConfig.BINANCE_TOP_COINS:
            # USDC는 USDT 페어, 나머지는 USDT 페어
            if coin == 'USDC':
                mapping[coin] = 'USDCUSDT'
            else:
                mapping[coin] = f'{coin}USDT'
        return mapping
    
    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Binance API 요청
        
        Args:
            endpoint: API 엔드포인트
            params: 쿼리 파라미터
            
        Returns:
            Dict: API 응답 데이터
            
        Raises:
            Exception: API 요청 실패
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout as exc:
            logger.error(f"Binance API 타임아웃: {url}")
            raise requests.exceptions.Timeout(f"Binance API timeout: {endpoint}") from exc
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance API 요청 실패: {url} - {e}")
            raise requests.exceptions.RequestException(f"Binance API error: {e}") from e
    
    def get_ticker_24hr(self, symbol: str) -> Dict:
        """
        24시간 가격 변동 정보 조회
        
        Args:
            symbol: 거래 심볼 (예: 'BTCUSDT')
            
        Returns:
            Dict: {
                'symbol': 'BTCUSDT',
                'lastPrice': '107065.16',
                'priceChange': '856.08',
                'priceChangePercent': '0.80',
                'highPrice': '108500.00',
                'lowPrice': '105000.00',
                'volume': '34756.12',
                'quoteVolume': '3714125896.45'
            }
        """
        endpoint = "/api/v3/ticker/24hr"
        return self._request(endpoint, params={'symbol': symbol})
    
    def get_price(self, symbol: str) -> Dict:
        """
        현재 가격 조회 (가장 가벼운 API)
        
        Args:
            symbol: 거래 심볼 (예: 'BTCUSDT')
            
        Returns:
            Dict: {
                'symbol': 'BTCUSDT',
                'price': '107065.16'
            }
        """
        endpoint = "/api/v3/ticker/price"
        return self._request(endpoint, params={'symbol': symbol})
    
    def get_top_coins_data(self, limit: int = 10) -> List[Dict]:
        """
        주요 코인의 24시간 가격 정보 조회
        
        Args:
            limit: 조회할 코인 개수
            
        Returns:
            List[Dict]: 코인 정보 리스트 (CoinGecko 형식과 호환)
        """
        coins_data = []
        
        # 주요 코인 심볼 (순서대로)
        symbols_to_fetch = list(self.major_symbols.values())[:limit]
        
        logger.info(f"[Binance] 상위 {limit}개 코인 데이터 조회 시작")
        
        for i, symbol in enumerate(symbols_to_fetch, 1):
            try:
                ticker = self.get_ticker_24hr(symbol)
                
                # 심볼 추출 (Binance 방식: 단순하고 명확)
                coin_symbol = symbol.replace('USDT', '').replace('USDC', '')
                coin_id = coin_symbol.lower()  # id는 소문자 심볼
                
                coin_data = {
                    'id': coin_id,  # 'btc', 'eth', 'sol' 등
                    'symbol': coin_symbol,  # 'BTC', 'ETH', 'SOL' 등
                    'name': self._get_coin_name(coin_symbol),
                    'current_price': float(ticker['lastPrice']),
                    'price_change_24h': float(ticker['priceChange']),
                    'price_change_percentage_24h': float(ticker['priceChangePercent']),
                    'high_24h': float(ticker['highPrice']),
                    'low_24h': float(ticker['lowPrice']),
                    'total_volume': float(ticker['volume']),
                    'market_cap': 0,  # Binance에서 제공하지 않음
                    'last_updated': datetime.now().isoformat(),
                    'source': 'binance'  # 데이터 출처 표시
                }
                
                coins_data.append(coin_data)
                logger.debug(f"[Binance] {i}/{len(symbols_to_fetch)} {coin_symbol}: ${coin_data['current_price']:,.2f}")
                
            except Exception as e:
                logger.error(f"[Binance] {symbol} 조회 실패: {e}")
                continue
        
        logger.info(f"[Binance] {len(coins_data)}개 코인 데이터 조회 완료")
        return coins_data
    
    def get_realtime_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        """
        실시간 가격만 빠르게 조회
        
        Args:
            symbols: 조회할 심볼 리스트 (None이면 주요 코인)
            
        Returns:
            Dict[str, float]: {심볼: 가격} 매핑
        """
        if symbols is None:
            symbols = list(self.major_symbols.values())[:5]
        
        prices = {}
        
        for symbol in symbols:
            try:
                ticker = self.get_price(symbol)
                coin_symbol = symbol.replace('USDT', '').replace('USDC', '')
                prices[coin_symbol] = float(ticker['price'])
                
            except Exception as e:
                logger.error(f"[Binance] {symbol} 가격 조회 실패: {e}")
                continue
        
        return prices
    
    def _get_coin_name(self, symbol: str) -> str:
        """
        심볼에서 코인 이름 추출
        
        Args:
            symbol: 코인 심볼 (예: 'BTC')
            
        Returns:
            str: 코인 이름
        """
        coin_names = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'BNB': 'BNB',
            'XRP': 'XRP',
            'USDT': 'Tether',
            'USDC': 'USD Coin',
            'SOL': 'Solana',
            'ADA': 'Cardano',
            'DOGE': 'Dogecoin',
            'TRX': 'TRON'
        }
        return coin_names.get(symbol, symbol)
    
    def check_health(self) -> bool:
        """
        Binance API 상태 확인
        
        Returns:
            bool: API 정상 여부
        """
        try:
            endpoint = "/api/v3/ping"
            self._request(endpoint)
            logger.info("[Binance] API 상태 정상")
            return True
            
        except Exception as e:
            logger.error(f"[Binance] API 상태 이상: {e}")
            return False


# 싱글톤 인스턴스
_binance_service_instance: Optional[BinanceService] = None


def get_binance_service() -> BinanceService:
    """Binance 서비스 싱글톤 인스턴스 반환"""
    # 모듈 레벨 변수 사용 (global 선언 없이)
    if _binance_service_instance is None:
        # 첫 호출 시에만 인스턴스 생성
        return BinanceService()
    
    return _binance_service_instance
