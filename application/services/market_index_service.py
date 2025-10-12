"""
BTS 마켓 지수 서비스

업비트 종합지수(UBCI) 및 글로벌 암호화폐 지수 제공
"""
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from utils.logger import get_logger

logger = get_logger(__name__)


class MarketIndexService:
    """
    마켓 지수 서비스
    
    - 업비트 종합지수 (UBCI, UBMI, UB10, UB30)
    - 글로벌 암호화폐 지수 (CoinGecko)
    """
    
    UPBIT_TRENDS_URL = "https://www.upbit.com/trends"
    UPBIT_CRIX_URL = "https://crix-api-cdn.upbit.com/v1/crix/candles/days"
    COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
    COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
    # 한국수출입은행 환율 API (무료, 인증키 불필요)
    EXCHANGE_RATE_API_URL = "https://www.koreaexim.go.kr/site/program/financial/exchangeJSON"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'pyupbit'
        })
        self._last_coingecko_call = None
    
    # ===== 업비트 지수 (API 우선, 스크래핑 fallback) =====
    
    def get_upbit_indices(self) -> Dict[str, any]:
        """
        업비트 종합지수 데이터 가져오기

        Upbit API가 공개되지 않아 웹 스크래핑 사용
        """
        try:
            logger.info("업비트 지수 웹 스크래핑으로 데이터 가져오기")
            return self._scrape_upbit_indices()
        except Exception as e:
            logger.error(f"업비트 지수 웹 스크래핑 실패: {e}")
            return self._get_empty_upbit_indices()

    def _fetch_and_parse_upbit_indices(self) -> Dict[str, any]:
        """
        Upbit CRIX API를 통해 지수 데이터를 가져오고 파싱합니다.
        """
        result = {
            'timestamp': datetime.now()
        }
        
        code_mapping = {
            "COMPOSITE": "ubci",
            "MARKET": "ubmi",
            "TOP10": "ub10",
        }

        for code, key in code_mapping.items():
            try:
                params = {
                    "code": f"IDX.UPBIT.{code}",
                    "count": 1
                }
                response = self.session.get(self.UPBIT_CRIX_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data or not isinstance(data, list):
                    raise ValueError(f"{code}에 대한 API 응답이 비어있거나 형식이 잘못되었습니다.")

                latest_candle = data[0]
                trade_price = float(latest_candle.get('tradePrice', 0))
                opening_price = float(latest_candle.get('openingPrice', 0))
                
                if opening_price == 0:
                    change = 0
                    change_rate = 0
                else:
                    change = trade_price - opening_price
                    change_rate = (change / opening_price) * 100

                result[key] = {
                    'value': trade_price,
                    'change': change,
                    'change_rate': change_rate
                }
            except Exception as e:
                logger.error(f"{code} 인덱스 데이터를 가져오는 중 오류 발생: {e}")
                result[key] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

        result['ub30'] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

        if len(result) <= 1:
            raise ValueError("API 응답에서 유효한 지수 데이터를 파싱할 수 없습니다.")

        return result

    def _scrape_upbit_indices(self) -> Dict[str, any]:
        """
        Playwright를 사용하여 동적으로 렌더링된 페이지에서 업비트 지수 데이터를 스크래핑합니다.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(self.UPBIT_TRENDS_URL, timeout=60000)
                # Wait for index values to load (look for css-bbw3a7 class which contains values)
                page.wait_for_selector('.css-bbw3a7', timeout=30000)

                # Extract index data using JavaScript
                indices_data = page.evaluate('''() => {
                    const result = {};

                    // Helper function to extract value and change from text
                    const parseIndexText = (text) => {
                        const valueMatch = text.match(/([\\d,]+\\.\\d+)/);
                        const changeMatch = text.match(/([▲▼+-][\\d,]+\\.\\d+)/);
                        const percentMatch = text.match(/([+-][\\d.]+%)/);

                        return {
                            value: valueMatch ? parseFloat(valueMatch[1].replace(/,/g, '')) : 0,
                            change: changeMatch ? parseFloat(changeMatch[1].replace(/[▲▼,]/g, '')) : 0,
                            change_rate: percentMatch ? parseFloat(percentMatch[1].replace(/%/g, '')) : 0
                        };
                    };

                    // Find all text containing index names
                    const allText = document.body.innerText;
                    const lines = allText.split('\\n');

                    // Look for specific index patterns
                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i];

                        if (line.includes('업비트 종합 지수')) {
                            // Next few lines should have the value
                            const combined = lines.slice(i, i + 5).join(' ');
                            result.ubci = parseIndexText(combined);
                        } else if (line.includes('업비트 알트코인 지수')) {
                            const combined = lines.slice(i, i + 5).join(' ');
                            result.ubmi = parseIndexText(combined);
                        } else if (line === '업비트 10' || line.includes('업비트 10')) {
                            const combined = lines.slice(i, i + 5).join(' ');
                            result.ub10 = parseIndexText(combined);
                        } else if (line === '업비트 30' || line.includes('업비트 30')) {
                            const combined = lines.slice(i, i + 5).join(' ');
                            result.ub30 = parseIndexText(combined);
                        }
                    }

                    return result;
                }''')

                logger.info(f"Playwright로 추출한 데이터: {indices_data}")

                # Build result
                result = {'timestamp': datetime.now()}
                for key in ['ubci', 'ubmi', 'ub10', 'ub30']:
                    if key in indices_data and indices_data[key]['value'] > 0:
                        result[key] = indices_data[key]
                    else:
                        result[key] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

                if any(result[k]['value'] > 0 for k in ['ubci', 'ubmi', 'ub10', 'ub30']):
                    logger.info("업비트 지수 웹 스크래핑 성공")
                    return result
                else:
                    logger.warning("업비트 지수 데이터를 추출할 수 없습니다.")
                    return self._get_empty_upbit_indices()

            except Exception as e:
                logger.error(f"Playwright 스크래핑 실패: {e}")
                return self._get_empty_upbit_indices()
            finally:
                browser.close()
    
    def _extract_indices_from_nextjs(self, data: dict) -> Optional[Dict]:
        """Next.js 데이터에서 지수 정보 추출"""
        try:
            props = data.get('props', {}).get('pageProps', {})
            indices_list = props.get('marketIndex')

            if not indices_list or not isinstance(indices_list, list):
                logger.warning(f"__NEXT_DATA__에서 'marketIndex' 리스트를 찾을 수 없거나 형식이 잘못되었습니다. Found: {type(indices_list)}")
                return None

            result = {
                'timestamp': datetime.now()
            }
            
            code_mapping = {
                "UBCI": "ubci",
                "UBMI": "ubmi",
                "UBSI10": "ub10",
            }

            for index_item in indices_list:
                market_code = index_item.get('market')
                if market_code in code_mapping:
                    key = code_mapping[market_code]
                    change_rate = float(index_item.get('signedChangeRate', 0)) * 100
                    result[key] = {
                        'value': float(index_item.get('tradePrice', 0)),
                        'change': float(index_item.get('signedChangePrice', 0)),
                        'change_rate': change_rate
                    }
            
            if 'ub30' not in result:
                result['ub30'] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}
            if 'ub10' not in result:
                result['ub10'] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

            return result if len(result) > 4 else None
            
        except Exception as e:
            logger.error(f"Next.js 데이터 파싱 실패: {e}")
            return None
    
    def _get_empty_upbit_indices(self) -> Dict:
        """빈 업비트 지수 데이터 반환"""
        empty_index = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}
        return {
            'ubci': empty_index.copy(),
            'ubmi': empty_index.copy(),
            'ub10': empty_index.copy(),
            'ub30': empty_index.copy(),
            'usd_krw': empty_index.copy(),
            'timestamp': datetime.now()
        }

    def get_usd_krw_rate(self) -> Dict[str, float]:
        """
        USD/KRW 환율 가져오기 (2일 전 대비 변동률)
        무료 환율 API 사용 (실제 USD/KRW)

        Note: 무료 API는 일일 업데이트만 지원하므로 2일 전 데이터와 비교

        Returns:
            {'value': 환율, 'change': 변동값, 'change_rate': 변동률(%)}
        """
        try:
            # Currency API - 무료, 일일 업데이트, 실제 환율
            today_url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"

            response = self.session.get(today_url, timeout=10)
            response.raise_for_status()
            today_data = response.json()

            current_rate = float(today_data['usd']['krw'])

            # 2일 전 날짜로 과거 데이터 가져오기 (더 명확한 변동 표시)
            try:
                two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
                historical_url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{two_days_ago}/v1/currencies/usd.json"

                hist_response = self.session.get(historical_url, timeout=10)
                hist_response.raise_for_status()
                historical_data = hist_response.json()

                previous_rate = float(historical_data['usd']['krw'])

                # 2일 전 대비 변동
                change = current_rate - previous_rate
                change_rate = (change / previous_rate) * 100

                logger.info(f"USD/KRW 환율: {current_rate:,.2f} (2일 전 대비: {change_rate:+.2f}%)")

                return {
                    'value': current_rate,
                    'change': change,
                    'change_rate': change_rate
                }

            except Exception as hist_error:
                logger.warning(f"과거 환율 데이터 가져오기 실패: {hist_error}, 변동률 0으로 표시")
                return {
                    'value': current_rate,
                    'change': 0.0,
                    'change_rate': 0.0
                }

        except Exception as e:
            logger.error(f"USD/KRW 환율 가져오기 실패: {e}")
            return {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}
    
    # ===== 글로벌 지수 (CoinGecko API) =====
    
    def get_global_crypto_data(self) -> Dict[str, any]:
        """
        CoinGecko API를 통한 글로벌 암호화폐 시장 데이터
        """
        try:
            response = self.session.get(self.COINGECKO_GLOBAL_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()['data']
            
            volume_to_cap_ratio = (
                data['total_volume']['usd'] / data['total_market_cap']['usd'] * 100
            )
            
            return {
                'total_market_cap_usd': float(data['total_market_cap']['usd']),
                'total_market_cap_krw': float(data['total_market_cap'].get('krw', 0)),
                'market_cap_change_24h': data['market_cap_change_percentage_24h_usd'],
                'total_volume_usd': float(data['total_volume']['usd']),
                'total_volume_krw': float(data['total_volume'].get('krw', 0)),
                'btc_dominance': data['market_cap_percentage']['btc'],
                'eth_dominance': data['market_cap_percentage']['eth'],
                'volume_to_market_cap_ratio': volume_to_cap_ratio,
                'active_cryptocurrencies': data['active_cryptocurrencies'],
                'markets': data.get('markets', 0),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"CoinGecko 글로벌 데이터 가져오기 실패: {e}")
            return self._get_empty_global_data()
    
    def _get_empty_global_data(self) -> Dict[str, any]:
        """빈 글로벌 데이터 반환"""
        return {
            'total_market_cap_usd': 0.0,
            'total_market_cap_krw': 0.0,
            'market_cap_change_24h': 0.0,
            'total_volume_usd': 0.0,
            'total_volume_krw': 0.0,
            'btc_dominance': 0.0,
            'eth_dominance': 0.0,
            'volume_to_market_cap_ratio': 0.0,
            'active_cryptocurrencies': 0,
            'markets': 0,
            'timestamp': datetime.now()
        }
    
    def get_top_coins_with_sparkline(
        self, 
        limit: int = 10, 
        vs_currency: str = 'usd'
    ) -> List[Dict[str, any]]:
        """
        상위 코인 데이터와 7일 sparkline 가져오기
        """
        try:
            import time
            
            if self._last_coingecko_call:
                elapsed = time.time() - self._last_coingecko_call
                if elapsed < 0.02:
                    time.sleep(0.02 - elapsed)
            
            params = {
                'vs_currency': vs_currency,
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': 'true',
                'price_change_percentage': '24h,7d'
            }
            
            response = self.session.get(
                self.COINGECKO_MARKETS_URL, 
                params=params,
                timeout=15
            )
            response.raise_for_status()
            
            self._last_coingecko_call = time.time()
            
            data = response.json()
            
            results = []
            for coin in data:
                results.append({
                    'id': coin.get('id', ''),
                    'symbol': coin.get('symbol', '').upper(),
                    'name': coin.get('name', ''),
                    'current_price': float(coin.get('current_price', 0)),
                    'market_cap': float(coin.get('market_cap', 0)),
                    'market_cap_rank': int(coin.get('market_cap_rank', 0)),
                    'price_change_percentage_24h': float(coin.get('price_change_percentage_24h', 0)),
                    'price_change_percentage_7d': float(coin.get('price_change_percentage_7d_in_currency', 0)),
                    'sparkline_in_7d': coin.get('sparkline_in_7d', {}).get('price', [])
                })
            
            logger.info(f"CoinGecko에서 {len(results)}개 코인 데이터 가져오기 완료")
            return results
            
        except requests.exceptions.Timeout as e:
            logger.error(f"CoinGecko API 타임아웃: {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"CoinGecko API 요청 실패: {e}")
            return []
        except Exception as e:
            logger.error(f"CoinGecko 데이터 처리 실패: {e}")
            return []
    
    # ===== 7일 평균 계산 =====
    
    def calculate_7day_averages(self, sparkline_data: List[Dict]) -> Dict[str, float]:
        """
        7일간 데이터의 평균 계산
        """
        if not sparkline_data:
            return {
                'avg_price_change_7d': 0.0,
                'avg_market_cap': 0.0,
                'positive_coins': 0,
                'negative_coins': 0
            }
        
        total_price_change = sum(coin['price_change_percentage_7d'] for coin in sparkline_data)
        total_market_cap = sum(coin['market_cap'] for coin in sparkline_data)
        positive_coins = sum(1 for coin in sparkline_data if coin['price_change_percentage_7d'] > 0)
        negative_coins = len(sparkline_data) - positive_coins
        
        return {
            'avg_price_change_7d': total_price_change / len(sparkline_data),
            'avg_market_cap': total_market_cap / len(sparkline_data),
            'positive_coins': positive_coins,
            'negative_coins': negative_coins
        }
    
    # ===== 통합 데이터 =====
    
    def get_all_market_indices(self) -> Dict[str, any]:
        """
        모든 마켓 지수 데이터 가져오기
        """
        return {
            'upbit': self.get_upbit_indices(),
            'global': self.get_global_crypto_data()
        }
