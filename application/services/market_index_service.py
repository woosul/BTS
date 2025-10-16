"""
BTS 마켓 지수 서비스

업비트 종합지수(UBCI) 및 글로벌 암호화폐 지수 제공
"""
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from config.market_index_config import MarketIndexConfig
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
    # FxRatesAPI (실시간 환율 API - 무료 플랜: 1000 requests/month)
    FXRATES_API_BASE_URL = "https://api.fxratesapi.com/latest"
    # Fallback: Currency API (일일 업데이트만 지원)
    CURRENCY_API_BASE_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'pyupbit'
        })
        self._last_coingecko_call = None
        self._last_fxrates_call = None

        # .env에서 FxRatesAPI 키 가져오기
        import os
        from dotenv import load_dotenv
        load_dotenv()
        self.fxrates_api_key = os.getenv('CURRENCY_API_KEY', '')
    
    # ===== 업비트 지수 (API 우선, 스크래핑 fallback) =====
    
    def get_upbit_indices(self) -> Dict[str, any]:
        """
        업비트 지수 데이터 수집 (다중 fallback)
        1. 간단한 requests 방식 (가장 빠름)
        2. CSS 셀렉터 방식 (빠름)
        3. 텍스트 기반 파싱 (안정적)
        4. 정규식 기반 파싱 (최후)
        """
        logger.info("업비트 지수 데이터 가져오기 시작 (다중 fallback)")

        # Fallback 0: 간단한 requests 방식 (가장 빠름)
        try:
            result = self._scrape_with_requests()
            if self._is_valid_result(result):
                logger.info("✓ Fallback 0 성공: 간단한 requests 방식")
                return result
        except Exception as e:
            logger.warning(f"✗ Fallback 0 실패 (requests): {e}")

        # Fallback 1: CSS 셀렉터 방식
        try:
            result = self._scrape_with_css_selector()
            if self._is_valid_result(result):
                logger.info("✓ Fallback 1 성공: CSS 셀렉터 방식")
                return result
        except Exception as e:
            logger.warning(f"✗ Fallback 1 실패 (CSS): {e}")
        except Exception as e:
            logger.warning(f"✗ Fallback 1 실패 (CSS 셀렉터): {e}")

        # Fallback 2: 텍스트 기반 파싱
        try:
            result = self._scrape_with_text_parsing()
            if self._is_valid_result(result):
                logger.info("✓ Fallback 2 성공: 텍스트 기반 파싱")
                return result
        except Exception as e:
            logger.warning(f"✗ Fallback 2 실패 (텍스트 파싱): {e}")

        # Fallback 3: 정규식 기반 파싱
        try:
            result = self._scrape_with_regex()
            if self._is_valid_result(result):
                logger.info("✓ Fallback 3 성공: 정규식 기반 파싱")
                return result
        except Exception as e:
            logger.warning(f"✗ Fallback 3 실패 (정규식): {e}")

        logger.error("모든 fallback 방법 실패 - 빈 데이터 반환")
        return self._get_empty_upbit_indices()

    def _is_valid_result(self, result: Dict[str, any]) -> bool:
        """결과가 유효한 데이터인지 확인"""
        if not result or not isinstance(result, dict):
            return False
        # 적어도 하나의 지수가 0보다 큰지 확인
        return any(
            result.get(key, {}).get('value', 0) > 0
            for key in ['ubci', 'ubmi', 'ub10', 'ub30']
        )

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
                response = self.session.get(self.UPBIT_CRIX_URL, params=params, timeout=MarketIndexConfig.TIMEOUT_UPBIT_API)
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

    def _scrape_with_requests(self) -> Dict[str, any]:
        """
        Fallback 0: 간단한 requests 방식으로 업비트 CRIX API 호출
        가장 빠르고 안정적인 방법이지만, API 구조 변경에 취약할 수 있음
        """
        try:
            # 업비트 CRIX API를 통한 지수 데이터 조회
            response = self.session.get(self.UPBIT_CRIX_URL, timeout=MarketIndexConfig.TIMEOUT_UPBIT_API)
            response.raise_for_status()
            
            data = response.json()
            result = {'timestamp': datetime.now()}
            
            # CRIX 응답에서 지수 정보 추출
            if isinstance(data, list) and len(data) > 0:
                # 첫 번째 항목에서 지수 정보 추출 (실제 API 응답 구조에 맞게 조정 필요)
                for item in data:
                    if 'code' in item and 'trade_price' in item:
                        code = item['code'].lower()
                        price = float(item.get('trade_price', 0))
                        change = float(item.get('change_price', 0))
                        change_rate = float(item.get('change_rate', 0)) * 100
                        
                        if code in ['ubci', 'ubmi', 'ub10', 'ub30']:
                            result[code] = {
                                'value': price,
                                'change': change,
                                'change_rate': change_rate
                            }
            
            # 기본값 설정 (데이터가 없는 경우)
            for key in ['ubci', 'ubmi', 'ub10', 'ub30']:
                if key not in result:
                    result[key] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}
            
            return result
            
        except Exception as e:
            logger.warning(f"Requests 방식 스크래핑 실패: {e}")
            raise

    def _scrape_with_css_selector(self) -> Dict[str, any]:
        """
        Fallback 1: CSS 셀렉터 방식으로 스크래핑
        - 빠르지만 CSS 클래스 변경에 취약
        - 짧은 타임아웃(10초)
        - USD/KRW 환율도 함께 추출
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(self.UPBIT_TRENDS_URL, timeout=MarketIndexConfig.TIMEOUT_UPBIT_SCRAPING * 1000)
                # 여러 가능한 CSS 셀렉터 시도
                selectors = ['.css-bbw3a7', '[data-testid="index-value"]', 'div[class*="css-"]']

                for selector in selectors:
                    try:
                        page.wait_for_selector(selector, timeout=MarketIndexConfig.TIMEOUT_UPBIT_WAIT_SELECTOR * 1000)
                        break
                    except:
                        continue

                # Extract index data + USD/KRW using JavaScript
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

                    // USD/KRW 전용 파싱 함수 (연속된 3줄에서 추출)
                    const parseUsdKrw = (lines, startIdx) => {
                        // 형식: "미국 (USD/KRW)" 다음 2줄 건너뛰고 3개 연속 값
                        // 예: 1,417.20 / 5.30 / 0.37%
                        try {
                            const value = parseFloat(lines[startIdx + 2].replace(/,/g, ''));
                            const change = parseFloat(lines[startIdx + 3].replace(/,/g, ''));
                            const changeRateStr = lines[startIdx + 4];
                            const changeRate = parseFloat(changeRateStr.replace(/%/g, ''));

                            return {
                                value: value || 0,
                                change: change || 0,
                                change_rate: changeRate || 0
                            };
                        } catch (e) {
                            return { value: 0, change: 0, change_rate: 0 };
                        }
                    };

                    // Find all text containing index names
                    const allText = document.body.innerText;
                    const lines = allText.split('\\n');

                    // Look for specific index patterns
                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i];

                        if (line.includes('업비트 종합 지수')) {
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
                        } else if (line.includes('미국 (USD/KRW)')) {
                            // USD/KRW 환율 추출 (전용 파서 사용)
                            result.usd_krw = parseUsdKrw(lines, i);
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

                # USD/KRW 환율 추가
                if 'usd_krw' in indices_data and indices_data['usd_krw']['value'] > 0:
                    result['usd_krw'] = indices_data['usd_krw']
                    logger.info(f"USD/KRW 환율 추출 성공: {result['usd_krw']}")
                else:
                    result['usd_krw'] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

                if any(result[k]['value'] > 0 for k in ['ubci', 'ubmi', 'ub10', 'ub30']):
                    logger.info("업비트 지수 + USD/KRW 웹 스크래핑 성공")
                    return result
                else:
                    logger.warning("업비트 지수 데이터를 추출할 수 없습니다.")
                    return self._get_empty_upbit_indices()

            except Exception as e:
                logger.error(f"Playwright 스크래핑 실패: {e}")
                return self._get_empty_upbit_indices()
            finally:
                browser.close()
    
    def _scrape_with_text_parsing(self) -> Dict[str, any]:
        """
        Fallback 2: 텍스트 기반 파싱 방식
        - CSS 클래스 변경에 강함
        - 페이지 전체 텍스트에서 지수명으로 찾기
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                # 업비트 데이터랩 페이지로 변경
                page.goto("https://datalab.upbit.com/", timeout=MarketIndexConfig.TIMEOUT_UPBIT_SCRAPING * 1000)
                page.wait_for_load_state('domcontentloaded', timeout=MarketIndexConfig.TIMEOUT_UPBIT_WAIT_LOAD * 1000)

                # 전체 텍스트 추출
                text = page.evaluate('() => document.body.innerText')
                lines = text.split('\n')

                result = {'timestamp': datetime.now()}
                indices = {'ubci': None, 'ubmi': None, 'ub10': None, 'ub30': None}

                # 텍스트에서 지수 찾기
                for i, line in enumerate(lines):
                    if '업비트 종합 지수' in line:
                        # 다음 2-3줄에서 숫자 찾기
                        for j in range(i+1, min(i+4, len(lines))):
                            import re
                            value_match = re.search(r'([\d,]+\.\d+)', lines[j])
                            if value_match:
                                indices['ubci'] = float(value_match.group(1).replace(',', ''))
                                # 변동률 찾기
                                rate_match = re.search(r'([+-]?\d+\.\d+)%', lines[j+1] if j+1 < len(lines) else '')
                                if rate_match:
                                    change_rate = float(rate_match.group(1))
                                    indices['ubci'] = {
                                        'value': indices['ubci'],
                                        'change': 0.0,
                                        'change_rate': change_rate
                                    }
                                break

                    elif '업비트 알트코인 지수' in line:
                        for j in range(i+1, min(i+4, len(lines))):
                            import re
                            value_match = re.search(r'([\d,]+\.\d+)', lines[j])
                            if value_match:
                                indices['ubmi'] = float(value_match.group(1).replace(',', ''))
                                rate_match = re.search(r'([+-]?\d+\.\d+)%', lines[j+1] if j+1 < len(lines) else '')
                                if rate_match:
                                    change_rate = float(rate_match.group(1))
                                    indices['ubmi'] = {
                                        'value': indices['ubmi'],
                                        'change': 0.0,
                                        'change_rate': change_rate
                                    }
                                break

                    elif '업비트 10' in line and '업비트 100' not in line:
                        for j in range(i+1, min(i+4, len(lines))):
                            import re
                            value_match = re.search(r'([\d,]+\.\d+)', lines[j])
                            if value_match:
                                indices['ub10'] = float(value_match.group(1).replace(',', ''))
                                rate_match = re.search(r'([+-]?\d+\.\d+)%', lines[j+1] if j+1 < len(lines) else '')
                                if rate_match:
                                    change_rate = float(rate_match.group(1))
                                    indices['ub10'] = {
                                        'value': indices['ub10'],
                                        'change': 0.0,
                                        'change_rate': change_rate
                                    }
                                break

                    elif '업비트 30' in line:
                        for j in range(i+1, min(i+4, len(lines))):
                            import re
                            value_match = re.search(r'([\d,]+\.\d+)', lines[j])
                            if value_match:
                                indices['ub30'] = float(value_match.group(1).replace(',', ''))
                                rate_match = re.search(r'([+-]?\d+\.\d+)%', lines[j+1] if j+1 < len(lines) else '')
                                if rate_match:
                                    change_rate = float(rate_match.group(1))
                                    indices['ub30'] = {
                                        'value': indices['ub30'],
                                        'change': 0.0,
                                        'change_rate': change_rate
                                    }
                                break

                # 결과 구성
                for key in ['ubci', 'ubmi', 'ub10', 'ub30']:
                    if isinstance(indices[key], dict):
                        result[key] = indices[key]
                    elif indices[key]:
                        result[key] = {
                            'value': indices[key],
                            'change': 0.0,
                            'change_rate': 0.0
                        }
                    else:
                        result[key] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

                return result

            except Exception as e:
                logger.error(f"텍스트 파싱 실패: {e}")
                raise
            finally:
                browser.close()

    def _scrape_with_regex(self) -> Dict[str, any]:
        """
        Fallback 3: 정규식 기반 파싱
        - 최후의 수단
        - 페이지 HTML에서 직접 정규식으로 추출
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto("https://datalab.upbit.com/", timeout=MarketIndexConfig.TIMEOUT_UPBIT_SCRAPING * 1000)
                page.wait_for_load_state('domcontentloaded', timeout=MarketIndexConfig.TIMEOUT_UPBIT_WAIT_LOAD * 1000)

                # HTML 전체 가져오기
                html = page.content()

                import re
                result = {'timestamp': datetime.now()}

                # 정규식으로 모든 숫자 패턴 찾기
                # 예: "18,012.67" 형태의 숫자
                pattern = r'([\d,]+\.\d{2})'
                matches = re.findall(pattern, html)

                # 상위 4개 큰 숫자를 지수로 가정 (간단한 휴리스틱)
                if matches:
                    numbers = [float(m.replace(',', '')) for m in matches]
                    # 1000 이상의 숫자만 필터 (지수는 보통 큰 숫자)
                    valid_numbers = sorted([n for n in numbers if n > 1000], reverse=True)[:4]

                    keys = ['ubci', 'ubmi', 'ub10', 'ub30']
                    for i, key in enumerate(keys):
                        if i < len(valid_numbers):
                            result[key] = {
                                'value': valid_numbers[i],
                                'change': 0.0,
                                'change_rate': 0.0
                            }
                        else:
                            result[key] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}
                else:
                    for key in ['ubci', 'ubmi', 'ub10', 'ub30']:
                        result[key] = {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

                return result

            except Exception as e:
                logger.error(f"정규식 파싱 실패: {e}")
                raise
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
        USD/KRW 환율 가져오기

        우선순위:
        1. Upbit 웹스크래핑 (업비트 지수와 함께 수집, 가장 빠름)
        2. FxRatesAPI (실시간, API 키 필요, 1000 requests/month 무료)
        3. Currency API (일일 업데이트만 지원, 최종 fallback)

        Returns:
            {'value': 환율, 'change': 변동값, 'change_rate': 변동률(%)}
        """
        # 우선순위 1: Upbit 스크래핑에서 이미 가져온 경우 (캐싱된 데이터 사용 안함, 항상 새로 조회)
        # 이 메서드는 독립적으로 호출되므로 항상 최신 데이터를 가져옵니다.

        # Fallback 1: FxRatesAPI 사용 (실시간 업데이트)
        try:
            if self.fxrates_api_key:
                result = self._get_usd_krw_from_fxrates()
                if result and result.get('value', 0) > 0:
                    logger.info(f"USD/KRW 환율 (FxRatesAPI): {result['value']:,.2f} (변동률: {result['change_rate']:+.2f}%)")
                    return result
                else:
                    logger.warning("FxRatesAPI 응답 데이터가 유효하지 않음, fallback으로 전환")
        except Exception as e:
            logger.warning(f"FxRatesAPI 호출 실패: {e}, fallback으로 전환")

        # Fallback 2: Currency API (일일 업데이트, 2일 전 대비)
        try:
            result = self._get_usd_krw_from_currency_api()
            logger.info(f"USD/KRW 환율 (Currency API fallback): {result['value']:,.2f} (2일 전 대비: {result['change_rate']:+.2f}%)")
            return result
        except Exception as e:
            logger.error(f"모든 USD/KRW API 호출 실패: {e}")
            return {'value': 0.0, 'change': 0.0, 'change_rate': 0.0}

    def _get_usd_krw_from_fxrates(self) -> Dict[str, float]:
        """
        FxRatesAPI를 사용한 USD/KRW 환율 조회 (실시간)

        Rate Limit: 무료 플랜 1000 requests/month
        업데이트 권장 주기: 1시간 (월 720회) 또는 30분 (월 1440회, 유료 필요)
        """
        # Rate limiting 체크 (1시간에 1회로 제한)
        if self._last_fxrates_call:
            elapsed = time.time() - self._last_fxrates_call
            min_interval = 3600  # 1시간 = 3600초
            if elapsed < min_interval:
                remaining = min_interval - elapsed
                logger.debug(f"FxRatesAPI rate limit: {remaining/60:.1f}분 남음")
                raise Exception(f"Rate limit: {remaining/60:.1f}분 후 재시도")

        # 현재 환율 조회
        params = {
            'api_key': self.fxrates_api_key,
            'base': 'USD',
            'currencies': 'KRW'
        }

        response = self.session.get(
            self.FXRATES_API_BASE_URL,
            params=params,
            timeout=MarketIndexConfig.TIMEOUT_CURRENCY_API
        )
        response.raise_for_status()

        self._last_fxrates_call = time.time()

        data = response.json()

        # 응답 형식: {"success": true, "base": "USD", "date": "2025-01-01", "rates": {"KRW": 1234.56}}
        if not data.get('success', False):
            raise Exception(f"FxRatesAPI 오류: {data.get('error', {})}")

        current_rate = float(data['rates']['KRW'])

        # 전일 환율 조회 (변동률 계산용)
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            hist_params = {
                'api_key': self.fxrates_api_key,
                'base': 'USD',
                'currencies': 'KRW',
                'date': yesterday
            }

            hist_response = self.session.get(
                self.FXRATES_API_BASE_URL,
                params=hist_params,
                timeout=MarketIndexConfig.TIMEOUT_CURRENCY_API
            )
            hist_response.raise_for_status()
            hist_data = hist_response.json()

            if hist_data.get('success', False):
                previous_rate = float(hist_data['rates']['KRW'])
                change = current_rate - previous_rate
                change_rate = (change / previous_rate) * 100

                return {
                    'value': current_rate,
                    'change': change,
                    'change_rate': change_rate
                }
        except Exception as hist_error:
            logger.warning(f"FxRatesAPI 전일 환율 조회 실패: {hist_error}")

        # 전일 환율 조회 실패 시 변동률 0
        return {
            'value': current_rate,
            'change': 0.0,
            'change_rate': 0.0
        }

    def _get_usd_krw_from_currency_api(self) -> Dict[str, float]:
        """
        Currency API를 사용한 USD/KRW 환율 조회 (fallback, 일일 업데이트)
        """
        response = self.session.get(self.CURRENCY_API_BASE_URL, timeout=MarketIndexConfig.TIMEOUT_CURRENCY_API)
        response.raise_for_status()
        today_data = response.json()

        current_rate = float(today_data['usd']['krw'])

        # 2일 전 날짜로 과거 데이터 가져오기
        try:
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            historical_url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{two_days_ago}/v1/currencies/usd.json"

            hist_response = self.session.get(historical_url, timeout=MarketIndexConfig.TIMEOUT_CURRENCY_API)
            hist_response.raise_for_status()
            historical_data = hist_response.json()

            previous_rate = float(historical_data['usd']['krw'])

            change = current_rate - previous_rate
            change_rate = (change / previous_rate) * 100

            return {
                'value': current_rate,
                'change': change,
                'change_rate': change_rate
            }

        except Exception as hist_error:
            logger.warning(f"Currency API 과거 환율 조회 실패: {hist_error}")
            return {
                'value': current_rate,
                'change': 0.0,
                'change_rate': 0.0
            }
    
    # ===== 글로벌 지수 (CoinGecko API) =====
    
    def get_global_crypto_data(self) -> Dict[str, any]:
        """
        CoinGecko API를 통한 글로벌 암호화폐 시장 데이터
        Rate limiting: 최소 2초 간격
        """
        try:
            # Rate limiting 체크
            if self._last_coingecko_call:
                elapsed = time.time() - self._last_coingecko_call
                min_interval = MarketIndexConfig.INTERNAL_MIN_INTERVAL_COINGECKO / 1000  # 밀리초 → 초 변환 (2.4초)
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    logger.info(f"CoinGecko API rate limit: {wait_time:.1f}초 대기")
                    time.sleep(wait_time)
            
            response = self.session.get(self.COINGECKO_GLOBAL_URL, timeout=MarketIndexConfig.TIMEOUT_COINGECKO_API)
            response.raise_for_status()
            
            self._last_coingecko_call = time.time()
            
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
        Rate limiting: 최소 60초 간격
        """
        try:
            # Rate limiting 체크 (CoinGecko API 공유)
            if self._last_coingecko_call:
                elapsed = time.time() - self._last_coingecko_call
                min_interval = MarketIndexConfig.INTERNAL_MIN_INTERVAL_COINGECKO / 1000  # 밀리초 → 초 변환 (2.4초)
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    logger.info(f"CoinGecko Markets API rate limit: {wait_time:.1f}초 대기")
                    time.sleep(wait_time)
            
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
                timeout=MarketIndexConfig.TIMEOUT_COINGECKO_MARKETS
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
