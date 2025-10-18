"""
BTS 대시보드 페이지

전체 현황 및 주요 지표 표시
"""
import streamlit as st
import sys
from pathlib import Path
from decimal import Decimal

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 전역 스타일 적용 (페이지별로 필수)
from presentation.styles.global_styles import apply_global_styles
apply_global_styles()

from infrastructure.database.connection import get_db_session
from application.services.wallet_service import WalletService
from application.services.trading_service import TradingService
from application.services.strategy_service import StrategyService
from infrastructure.exchanges.upbit_client import UpbitClient
from infrastructure.repositories.user_settings_repository import UserSettingsRepository
from domain.entities.user_settings import UserSettings
from presentation.components.metrics import (
    display_trading_metrics,
    display_performance_summary,
    display_recent_trades_table
)
from presentation.components.charts import (
    render_profit_chart,
    render_candlestick_chart
)
from presentation.components.cards import render_wallet_card
from presentation.components.metric_cards import render_metric_card_group
from utils.logger import get_logger

logger = get_logger(__name__)

def get_services():
    """서비스 인스턴스 가져오기"""
    if 'db' not in st.session_state:
        from infrastructure.database.connection import SessionLocal
        st.session_state.db = SessionLocal()

    if 'wallet_service' not in st.session_state:
        st.session_state.wallet_service = WalletService(st.session_state.db)

    if 'trading_service' not in st.session_state:
        exchange = UpbitClient()
        st.session_state.trading_service = TradingService(st.session_state.db, exchange)

    if 'strategy_service' not in st.session_state:
        exchange = UpbitClient()
        st.session_state.strategy_service = StrategyService(st.session_state.db, exchange)

    return (
        st.session_state.wallet_service,
        st.session_state.trading_service,
        st.session_state.strategy_service
    )

def main():
    st.title("대시보드")
    
    # 세션 상태 초기화 (KRW 토글)
    if 'show_krw' not in st.session_state:
        st.session_state.show_krw = False
    
    # 마지막 업데이트 타임스탬프 표시 (시간 부분만 업데이트 가능하도록 span으로 분리)
    from datetime import datetime
    st.markdown(
        f'<p style="font-size: 0.875rem; color: rgba(250, 250, 250, 0.6);">'
        f'마지막 업데이트 | <span id="last-update-timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span> | WebSocket 실시간 연동 | '
        f'<a href="/Setting" style="color: rgba(250, 250, 250, 0.6);">설정 →</a>'
        f'</p>',
        unsafe_allow_html=True
    )
    
    st.markdown("---")

    # 업비트 종합지수 + USD 환율 (DB에서 조회)
    try:
        # 스케줄러를 통해 DB에서 조회 (API 호출 없음)
        from application.services.market_index_scheduler import MarketIndexScheduler
        scheduler = MarketIndexScheduler()
        
        upbit_data = scheduler._get_upbit_data_from_db()
        usd_data = scheduler._get_usd_krw_data_from_db()

        # 업비트 지수 카드 그룹 (4개 지수 + USD 환율 = 5개)
        upbit_metrics = []
        indices_config = [
            ('ubci', 'UBCI', 'ubci-card'),
            ('ubmi', 'UBMI', 'ubmi-card'),
            ('ub10', 'UB10', 'ub10-card'),
            ('ub30', 'UB30', 'ub30-card')
        ]

        for key, label, card_id in indices_config:
            index_data = upbit_data.get(key, {})
            value = index_data.get('value', 0)
            change_rate = index_data.get('change_rate', 0)

            logger.info(f"Dashboard 업비트 지수: {key}={value}, change_rate={change_rate}")

            if value > 0:
                upbit_metrics.append({
                    "label": label,
                    "value": f"{value:,.2f}",
                    "delta": change_rate,
                    "card_id": card_id
                })
            else:
                upbit_metrics.append({
                    "label": label,
                    "value": "N/A",
                    "delta": None,
                    "card_id": card_id
                })

        # USD 환율 추가
        if usd_data['value'] > 0:
            upbit_metrics.append({
                "label": "USD/KRW",
                "value": f"₩{usd_data['value']:,.2f}",
                "delta": usd_data['change_rate'],
                "card_id": "usd-krw-card"
            })
        else:
            upbit_metrics.append({
                "label": "USD/KRW",
                "value": "N/A",
                "delta": None,
                "card_id": "usd-krw-card"
            })

        render_metric_card_group(
            title="업비트 종합 지수",
            metrics=upbit_metrics,
            columns=5
        )

        st.markdown("")  # 간격

    except Exception as e:
        logger.error(f"업비트 지수 표시 실패: {e}", exc_info=True)
        st.error(f"업비트 지수를 불러오는데 실패했습니다: {str(e)}")

    # 글로벌 마켓 지수 + 7일 평균 (통합)
    try:
        # 스케줄러 인스턴스를 통해 DB에서 데이터 조회 (API 호출 없음)
        from application.services.market_index_scheduler import MarketIndexScheduler
        scheduler = MarketIndexScheduler()

        global_data = scheduler._get_global_data_from_db()
        coins_data = scheduler._get_coin_data_from_db()

        # 디버깅: 글로벌 데이터 내용 로깅
        logger.info(f"Dashboard 글로벌 데이터 조회: {global_data}")
        logger.info(f"Dashboard 글로벌 데이터 키: {list(global_data.keys()) if global_data else 'None'}")
        if global_data and 'btc_dominance' in global_data:
            logger.info(f"Dashboard BTC 도미넌스 값: {global_data['btc_dominance']}")

        # 글로벌 지수 기본 카드 (3개)
        combined_metrics = [
            {"label": "총 시가총액", "value": "N/A", "delta": None, "card_id": "global-market-cap-card"},
            {"label": "24h 거래량", "value": "N/A", "delta": None, "card_id": "global-volume-card"},
            {"label": "BTC 도미넌스", "value": "N/A", "delta": None, "card_id": "btc-dominance-card"}
        ]

        # 글로벌 데이터가 있으면 업데이트
        if global_data and 'total_market_cap_usd' in global_data:
            market_cap_trillion = global_data['total_market_cap_usd'] / 1_000_000_000_000
            combined_metrics[0]["value"] = f"${market_cap_trillion:.2f}T"
            if 'market_cap_change_24h' in global_data:
                combined_metrics[0]["delta"] = global_data['market_cap_change_24h']

        if global_data and 'total_volume_usd' in global_data:
            volume_billion = global_data['total_volume_usd'] / 1_000_000_000
            combined_metrics[1]["value"] = f"${volume_billion:.1f}B"

        if global_data and 'btc_dominance' in global_data:
            btc_dom_value = f"{global_data['btc_dominance']:.2f}%"
            combined_metrics[2]["value"] = btc_dom_value
            logger.info(f"Dashboard BTC 도미넌스 카드 설정: {btc_dom_value}")

        # 글로벌 데이터에서 평균 변화율과 거래량-시가총액 비율 추가
        if 'market_cap_change_24h' in global_data:
            change_rate = global_data['market_cap_change_24h']
            combined_metrics.append({
                "label": "평균 변화율",
                "value": f"{abs(change_rate):.2f}%",
                "delta": change_rate  # 컬러 코딩을 위한 delta 값
            })
        else:
            combined_metrics.append({"label": "평균 변화율", "value": "N/A", "delta": None})

        if 'volume_to_market_cap_ratio' in global_data:
            ratio = global_data['volume_to_market_cap_ratio']
            combined_metrics.append({
                "label": "거래량-시가총액 비율",
                "value": f"{ratio:.2f}%",
                "delta": None
            })
        else:
            combined_metrics.append({"label": "거래량-시가총액 비율", "value": "N/A", "delta": None})

        render_metric_card_group(
            title="글로벌 시장 지수",
            metrics=combined_metrics,
            columns=5,
            attribution='Powered by <a href="https://www.coingecko.com" target="_blank" style="color: #808080; text-decoration: none;">CoinGecko</a>'
        )

        st.markdown("")  # 간격

        # 개별 코인 추세 (상위 5개: BTC, ETH, SOL, BNB, XRP)
        # API 소스와 무관하게 심볼 기반으로 매칭
        if coins_data and len(coins_data) > 0:
            # USD/KRW 환율 가져오기
            usd_krw_rate = usd_data.get('value', 1400.0) if usd_data else 1400.0
            show_krw = st.session_state.get('show_krw', False)
            
            logger.info(f"Dashboard 개별 코인: show_krw={show_krw}, usd_krw_rate={usd_krw_rate}")
            
            coin_metrics = []
            
            # 표시할 코인 순서 (심볼 우선순위)
            target_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']
            
            # 심볼 → CoinGecko ID 매핑 (Fallback 호환성)
            symbol_to_id = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'SOL': 'solana',
                'BNB': 'binancecoin',
                'XRP': 'ripple',
                'USDT': 'tether',
                'USDC': 'usd-coin'
            }
            
            # 역매핑 (ID → 심볼)
            id_to_symbol = {v: k for k, v in symbol_to_id.items()}
            
            for coin in coins_data:
                if len(coin_metrics) >= 5:
                    break
                
                # 심볼 추출 (대소문자 무관)
                symbol = coin.get('symbol', '').upper()
                coin_id = coin.get('id', '').lower()
                
                # 심볼 또는 ID로 매칭
                matched_symbol = None
                if symbol in target_symbols:
                    matched_symbol = symbol
                elif coin_id in id_to_symbol:
                    matched_symbol = id_to_symbol[coin_id]
                
                if matched_symbol:
                    name = coin.get('name', matched_symbol)
                    price_usd = float(coin.get('current_price', 0))  # float로 명시적 변환
                    change_24h = coin.get('price_change_percentage_24h', 0)
                    
                    # KRW/USD 토글에 따라 가격 포맷
                    if show_krw:
                        # 원화 표시
                        price_krw = price_usd * usd_krw_rate
                        if price_krw < 1000:
                            price_str = f"₩{price_krw:,.2f}"
                        else:
                            price_str = f"₩{price_krw:,.0f}"
                        logger.debug(f"Dashboard {matched_symbol}: KRW mode - ${price_usd:,.2f} → {price_str}")
                    else:
                        # 달러 표시 (천 단위 콤마 + 소숫점 2자리 항상 유지)
                        if price_usd < 1:
                            price_str = f"${price_usd:.4f}"
                        else:
                            price_str = f"${price_usd:,.2f}"  # 모든 경우 소숫점 2자리
                        logger.debug(f"Dashboard {matched_symbol}: USD mode - {price_str}")
                    
                    coin_metrics.append({
                        "label": f"{name} ({matched_symbol})",
                        "value": price_str,
                        "delta": change_24h,
                        "card_id": f"coin-{matched_symbol.lower()}-card"
                    })

            if coin_metrics:
                # 토글 콜백
                def toggle_currency():
                    st.session_state.show_krw = st.session_state.krw_toggle
                
                # 타이틀과 토글 컨테이너를 HTML로 배치 ("Powered by CoinGecko" 방식 참조)
                st.markdown("""
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                    <div style='color: #66686a; font-size: 14px; font-weight: 600;'>개별 코인 추세 (24h 변동)</div>
                    <div></div>
                </div>
                """, unsafe_allow_html=True)
                
                # 토글 스위치 (Streamlit 위젯)
                st.toggle("KRW", value=st.session_state.show_krw, key="krw_toggle", on_change=toggle_currency)
                
                # Hidden div for currency mode (JavaScript가 읽음)
                st.markdown(f'<div id="currency-mode" data-krw="{st.session_state.show_krw}" style="display:none;"></div>', unsafe_allow_html=True)
                
                # 메트릭 카드 렌더링 (title 없이)
                cols = st.columns(5, gap="small")
                for idx, metric in enumerate(coin_metrics):
                    col_idx = idx % 5
                    with cols[col_idx]:
                        from presentation.components.metric_cards import render_metric_card
                        render_metric_card(
                            label=metric.get("label", ""),
                            value=metric.get("value", "N/A"),
                            delta=metric.get("delta", None),
                            card_id=metric.get("card_id", None)
                        )
            else:
                st.info("표시할 코인 데이터가 없습니다.")
        else:
            st.info("코인 데이터를 가져올 수 없습니다.")

        st.markdown("---")

    except Exception as e:
        logger.error(f"글로벌 마켓 지수 표시 실패: {e}")

    # 서비스 초기화
    wallet_service, trading_service, strategy_service = get_services()

    # 사이드바: 활성 전략 및 최근 시그널
    with st.sidebar:
        st.markdown("---")

        # 활성 전략
        try:
            strategies = strategy_service.get_all_strategies()
            active_strategies = [s for s in strategies if s.status.value == "active"]

            st.subheader("활성 전략")
            if active_strategies:
                for strategy in active_strategies:
                    with st.expander(f"{strategy.name}", expanded=False):
                        st.write(f"**설명**: {strategy.description}")
                        st.write(f"**시간프레임**: {strategy.timeframe.value}")
                        st.write(f"**파라미터**:")
                        for key, value in strategy.parameters.items():
                            st.write(f"  - {key}: {value}")
            else:
                st.info("활성화된 전략이 없습니다.")

            # 최근 시그널
            st.subheader("최근 시그널")
            if active_strategies:
                try:
                    strategy = active_strategies[0]
                    signal = strategy_service.generate_signal(
                        strategy.id,
                        "KRW-BTC"
                    )

                    # 시그널 텍스트
                    signal_text = {
                        "buy": "매수",
                        "sell": "매도",
                        "hold": "관망"
                    }
                    text = signal_text.get(signal.signal.value, signal.signal.value)

                    # 태그 스타일로 표시 (inline, 작은 크기)
                    tags_html = f"""<div style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.5rem;">
<span style="background-color: #3C3E44; padding: 0.4rem 0.6rem; border-radius: 4px; display: inline-block; font-size: 0.85rem;">
<span style="color: #9e9e9e;">시그널:</span>
<span style="color: white; font-weight: bold; margin-left: 0.3rem;">{text}</span>
</span>
<span style="background-color: #3C3E44; padding: 0.4rem 0.6rem; border-radius: 4px; display: inline-block; font-size: 0.85rem;">
<span style="color: #9e9e9e;">확신도:</span>
<span style="color: white; font-weight: bold; margin-left: 0.3rem;">{signal.confidence * 100:.1f}%</span>
</span>"""

                    if signal.indicators:
                        for key, value in signal.indicators.items():
                            if isinstance(value, float):
                                val_str = f"{value:.2f}"
                            else:
                                val_str = str(value)
                            tags_html += f"""
<span style="background-color: #3C3E44; padding: 0.4rem 0.6rem; border-radius: 4px; display: inline-block; font-size: 0.85rem;">
<span style="color: #9e9e9e;">{key}:</span>
<span style="color: white; font-weight: bold; margin-left: 0.3rem;">{val_str}</span>
</span>"""

                    tags_html += "</div>"
                    st.markdown(tags_html, unsafe_allow_html=True)

                except Exception as e:
                    logger.error(f"시그널 생성 실패: {e}")
                    st.error(f"시그널 생성 실패: {e}")
            else:
                st.info("활성화된 전략이 없습니다.")

        except Exception as e:
            logger.error(f"전략 조회 실패: {e}")
            st.error(f"전략 조회 실패: {e}")

    # 지갑 선택
    try:
        wallets = wallet_service.get_all_wallets()

        if not wallets:
            st.warning("등록된 지갑이 없습니다. 먼저 지갑을 생성하세요.")
            return

        selected_wallet_id = st.selectbox(
            "지갑 선택",
            options=[w.id for w in wallets],
            format_func=lambda x: next(
                (f"{w.name} ({w.wallet_type.value})" for w in wallets if w.id == x),
                str(x)
            )
        )

        wallet = wallet_service.get_wallet(selected_wallet_id)

    except Exception as e:
        logger.error(f"지갑 조회 실패: {e}")
        st.error(f"지갑 조회 실패: {e}")
        return

    # 지갑 현황 카드
    st.subheader("지갑 현황")
    wallet_type_text = "가상" if wallet.wallet_type.value == "virtual" else "실거래"
    render_wallet_card(
        title=wallet.name,
        balance=wallet.balance_krw,
        total_value=wallet.total_value_krw,
        wallet_type=wallet_type_text
    )

    st.markdown("---")

    # 거래 통계
    try:
        trades = trading_service.get_wallet_trades(wallet.id, limit=100)

        if trades:
            # 통계 계산
            total_trades = len(trades)
            buy_trades = [t for t in trades if t.side.value == "buy"]
            sell_trades = [t for t in trades if t.side.value == "sell"]

            # 수익 계산
            total_buy_amount = sum(t.total_amount + t.fee for t in buy_trades)
            total_sell_amount = sum(t.total_amount - t.fee for t in sell_trades)
            total_profit = total_sell_amount - total_buy_amount

            # 승률 계산
            wins = 0
            if buy_trades:
                avg_buy_price = sum(t.price for t in buy_trades) / len(buy_trades)
                wins = sum(1 for t in sell_trades if t.price > avg_buy_price)

            win_rate = (wins / len(sell_trades) * 100) if sell_trades else 0
            avg_profit = total_profit / total_trades if total_trades > 0 else Decimal("0")

            st.subheader("트레이딩 통계")
            display_trading_metrics(
                total_trades=total_trades,
                win_rate=win_rate,
                avg_profit=avg_profit,
                total_profit=total_profit
            )

        else:
            st.info("거래 내역이 없습니다.")

    except Exception as e:
        logger.error(f"거래 통계 조회 실패: {e}")
        st.error(f"거래 통계 조회 실패: {e}")

    st.markdown("---")

    # 차트
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("가격 차트")
        try:
            # Upbit에서 OHLCV 데이터 조회
            exchange = UpbitClient()
            ohlcv_data = exchange.get_ohlcv("KRW-BTC", "60", 100)

            if ohlcv_data:
                fig = render_candlestick_chart(ohlcv_data, title="BTC/KRW", height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("가격 데이터를 가져올 수 없습니다.")

        except Exception as e:
            logger.error(f"차트 렌더링 실패: {e}")
            st.error(f"차트 렌더링 실패: {e}")

    with col2:
        st.subheader("수익 차트")
        try:
            if trades:
                fig = render_profit_chart(trades, title="손익 추이", height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("거래 내역이 없습니다.")

        except Exception as e:
            logger.error(f"수익 차트 렌더링 실패: {e}")
            st.error(f"수익 차트 렌더링 실패: {e}")

    st.markdown("---")

    # 성과 요약
    if trades:
        display_performance_summary(trades, days=30)

    st.markdown("---")

    # 최근 거래 내역
    st.subheader("최근 거래 내역")
    if trades:
        display_recent_trades_table(trades, limit=10)
    else:
        st.info("거래 내역이 없습니다.")

    # WebSocket 실시간 업데이트 (parent 윈도우에서 실행)
    import streamlit.components.v1 as components
    from config.market_index_config import MarketIndexConfig
    ws_url = MarketIndexConfig.get_websocket_url()

    websocket_client_path = project_root / "presentation" / "static" / "websocket_client.js"
    with open(websocket_client_path, 'r', encoding='utf-8') as f:
        websocket_client_code = f.read()

    # JavaScript 코드에 WebSocket URL 삽입
    websocket_js = f"""
    <script>
        // WebSocket URL 설정
        const WS_URL = '{ws_url}';

        {websocket_client_code}
    </script>
    """

    components.html(websocket_js, height=1)

if __name__ == "__main__":
    main()
