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

from infrastructure.database.connection import get_db_session
from application.services.wallet_service import WalletService
from application.services.trading_service import TradingService
from application.services.strategy_service import StrategyService
from application.services.cached_market_index_service import CachedMarketIndexService
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

# st.navigation을 사용할 때는 각 페이지에서 st.set_page_config와 st.logo를 호출하면 안 됨
# 메인 streamlit_app.py에서만 설정해야 함

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
    # 전역 스타일 적용
    from presentation.styles.global_styles import apply_global_styles
    apply_global_styles()

    st.title("대시보드")

    # 갱신 간격 설정
    from datetime import datetime
    settings_repo = UserSettingsRepository()

    # 현재 설정값 가져오기
    current_setting = settings_repo.get_by_key(UserSettings.DASHBOARD_REFRESH_INTERVAL)
    current_interval = int(current_setting.setting_value) if current_setting else 0

    # 간격 옵션
    interval_options = {
        "OFF": 0,
        "10초": 10,
        "30초": 30,
        "1분": 60,
        "3분": 180,
        "5분": 300,
        "10분": 600
    }

    current_label = next((k for k, v in interval_options.items() if v == current_interval), "OFF")
    current_index = list(interval_options.keys()).index(current_label)

    # 간단한 인라인 레이아웃
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f'<span style="color: rgba(250, 250, 250, 0.6); font-size: 0.875rem;">마지막 업데이트 | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 암호화폐 시장 지수 설정 주기별 갱신</span>', unsafe_allow_html=True)
    with col2:
        selected_label = st.selectbox(
            "갱신 간격",
            options=list(interval_options.keys()),
            index=current_index,
            key="dashboard_refresh_interval",
            label_visibility="collapsed"
        )

    # 설정 변경 시 저장
    selected_interval = interval_options[selected_label]
    if selected_interval != current_interval:
        settings_repo.upsert(
            key=UserSettings.DASHBOARD_REFRESH_INTERVAL,
            value=str(selected_interval),
            description="대시보드 페이지 자동 갱신 간격 (초)"
        )
        st.success(f"갱신 간격이 {selected_label}으로 변경되었습니다.")
        st.rerun()

    st.markdown("---")

    # 업비트 종합지수 + USD 환율 (DB 캐시 사용)
    try:
        market_index_service = CachedMarketIndexService()

        # DB 캐시에서 즉시 조회 (만료되면 백그라운드 업데이트)
        upbit_data = market_index_service.get_upbit_indices_cached()
        usd_data = market_index_service.get_usd_krw_cached()

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
        # 글로벌 데이터는 DB 캐시에서 조회
        global_data = market_index_service.get_global_crypto_data_cached()

        # 상위 코인 데이터도 DB 캐시에서 조회 (Streamlit 캐시 사용 안 함)
        coins_data = market_index_service.get_top_coins_with_sparkline_cached(limit=10)

        # 글로벌 + 7일 평균 통합 카드 (5개 구성)
        market_cap_trillion = global_data['total_market_cap_usd'] / 1_000_000_000_000
        volume_billion = global_data['total_volume_usd'] / 1_000_000_000

        combined_metrics = [
            {
                "label": "총 시가총액",
                "value": f"${market_cap_trillion:.2f}T",
                "delta": global_data['market_cap_change_24h'],  # 24h 변동률 있음
                "card_id": "global-market-cap-card"
            },
            {
                "label": "24h 거래량",
                "value": f"${volume_billion:.1f}B",
                "delta": None,  # 변동률 데이터 없음
                "card_id": "global-volume-card"
            },
            {
                "label": "BTC 도미넌스",
                "value": f"{global_data['btc_dominance']:.2f}%",
                "delta": None,  # 변동률 데이터 없음
                "card_id": "btc-dominance-card"
            }
        ]

        # 7일 평균 데이터 추가
        if coins_data and len(coins_data) > 0:
            averages = market_index_service.calculate_7day_averages(coins_data)
            avg_mcap_billion = averages['avg_market_cap'] / 1_000_000_000
            avg_change = averages['avg_price_change_7d']

            combined_metrics.extend([
                {
                    "label": "평균 변화율",
                    "value": f"{abs(avg_change):.2f}%",
                    "delta": avg_change  # +/- 값을 delta로 전달하여 색상 변경
                },
                {
                    "label": "평균 시가총액",
                    "value": f"${avg_mcap_billion:.2f}B",
                    "delta": None
                }
            ])
        else:
            # 데이터 없을 때 빈 카드
            combined_metrics.extend([
                {"label": "평균 변화율", "value": "N/A", "delta": None},
                {"label": "평균 시가총액", "value": "N/A", "delta": None}
            ])

        render_metric_card_group(
            title="글로벌 시장 지수",
            metrics=combined_metrics,
            columns=5
        )

        st.markdown("")  # 간격

        # 개별 코인 추세 (5개)
        try:
            if coins_data:
                # 개별 코인 카드 그룹 (상위 5개만)
                coin_metrics = []
                for coin in coins_data[:5]:
                    price = coin['current_price']
                    price_str = f"${price:,.2f}" if price < 1000 else f"${price:,.0f}"
                    coin_metrics.append({
                        "label": coin['symbol'].upper(),
                        "value": price_str,
                        "delta": coin['price_change_percentage_7d']
                    })

                render_metric_card_group(
                    title="개별 코인 추세",
                    metrics=coin_metrics,
                    columns=5
                )
            else:
                st.info("7일 추세 데이터를 가져올 수 없습니다.")

        except Exception as sparkline_error:
            logger.warning(f"7일 추세 데이터 표시 실패: {sparkline_error}")
            st.info("7일 추세 데이터를 불러오는 중 문제가 발생했습니다.")

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

    # parent.window에서 WebSocket 실행 (iframe 샌드박스 우회)
    websocket_js = f"""
    <script>
    (function() {{
        // parent 윈도우에 WebSocket 함수 정의 (중복 방지)
        if (window.parent.btsDashboardWebSocket) {{
            console.log('[WebSocket] 이미 초기화됨');
            return;
        }}

        console.log('[WebSocket] parent 윈도우에서 초기화 시작');

        window.parent.btsDashboardWebSocket = {{
            ws: null,
            reconnectInterval: null,

            connect: function() {{
                const self = window.parent.btsDashboardWebSocket;

                if (self.ws && (self.ws.readyState === WebSocket.CONNECTING || self.ws.readyState === WebSocket.OPEN)) {{
                    console.log('[WebSocket] 이미 연결 중');
                    return;
                }}

                console.log('[WebSocket] 연결 시도: {ws_url}');
                self.ws = new WebSocket('{ws_url}');

                self.ws.onopen = function(event) {{
                    console.log('[WebSocket] ✓ 연결 성공');
                    if (self.reconnectInterval) {{
                        clearInterval(self.reconnectInterval);
                        self.reconnectInterval = null;
                    }}

                    // ping 테스트 전송
                    if (self.ws.readyState === WebSocket.OPEN) {{
                        self.ws.send('ping');
                        console.log('[WebSocket] ping 전송');
                    }}
                }};

                self.ws.onmessage = function(event) {{
                    console.log('[WebSocket] 메시지 수신:', event.data.substring(0, 100));

                    if (event.data === 'pong') {{
                        console.log('[WebSocket] pong 수신 - 통신 정상');
                        return;
                    }}

                    try {{
                        const message = JSON.parse(event.data);
                        console.log('[WebSocket] JSON 파싱 성공, type:', message.type);

                        if (message.type === 'indices_updated') {{
                            console.log('[WebSocket] 지수 데이터 수신 완료');
                            console.log('[WebSocket] upbit:', message.data.upbit ? 'OK' : 'NO');
                            console.log('[WebSocket] usd_krw:', message.data.usd_krw ? 'OK' : 'NO');
                            console.log('[WebSocket] global:', message.data.global ? 'OK' : 'NO');

                            window.parent.btsDashboardWebSocket.updateDashboard(message.data, message.timestamp);
                        }}
                    }} catch (e) {{
                        console.error('[WebSocket] JSON 파싱 실패:', e);
                    }}
                }};

                self.ws.onerror = function(error) {{
                    console.error('[WebSocket] 오류:', error);
                }};

                self.ws.onclose = function(event) {{
                    console.log('[WebSocket] 연결 종료 (code=' + event.code + ')');
                    self.ws = null;
                    if (!self.reconnectInterval) {{
                        console.log('[WebSocket] 5초 후 재연결');
                        self.reconnectInterval = setInterval(function() {{
                            window.parent.btsDashboardWebSocket.connect();
                        }}, 5000);
                    }}
                }};
            }},

            updateDashboard: function(data, timestamp) {{
                console.log('[WebSocket] 대시보드 업데이트 시작');
                const doc = window.parent.document;
                let updateCount = 0;

                // 업비트 지수
                if (data.upbit) {{
                    ['ubci', 'ubmi', 'ub10', 'ub30'].forEach(function(key) {{
                        if (data.upbit[key]) {{
                            const card = doc.getElementById(key + '-card');
                            if (card) {{
                                const valueSpan = card.querySelector('.metric-value');
                                const deltaSpan = card.querySelector('.metric-delta');

                                if (valueSpan) {{
                                    const value = data.upbit[key].value || 0;
                                    valueSpan.textContent = value > 0 ? value.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) : 'N/A';

                                    if (deltaSpan) {{
                                        const changeRate = data.upbit[key].change_rate || 0;
                                        if (changeRate > 0) {{
                                            deltaSpan.innerHTML = '<span style="font-size: 8px;">▲</span> ' + Math.abs(changeRate).toFixed(2) + '%';
                                            deltaSpan.style.color = '#ef5350';
                                            valueSpan.style.color = '#ef5350';
                                        }} else if (changeRate < 0) {{
                                            deltaSpan.innerHTML = '<span style="font-size: 8px;">▼</span> ' + Math.abs(changeRate).toFixed(2) + '%';
                                            deltaSpan.style.color = '#42a5f5';
                                            valueSpan.style.color = '#42a5f5';
                                        }} else {{
                                            deltaSpan.innerHTML = '<span style="font-size: 8px;">-</span> 0.00%';
                                            deltaSpan.style.color = '#9e9e9e';
                                            valueSpan.style.color = 'white';
                                        }}
                                    }}
                                    updateCount++;
                                }}
                            }}
                        }}
                    }});
                }}

                // USD/KRW
                if (data.usd_krw) {{
                    const card = doc.getElementById('usd-krw-card');
                    if (card) {{
                        const valueSpan = card.querySelector('.metric-value');
                        if (valueSpan) {{
                            const value = data.usd_krw.value || 0;
                            valueSpan.textContent = value > 0 ? '₩' + value.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) : 'N/A';
                            updateCount++;
                        }}
                    }}
                }}

                // 글로벌 데이터
                if (data.global) {{
                    const marketCapCard = doc.getElementById('global-market-cap-card');
                    if (marketCapCard && data.global.total_market_cap_usd) {{
                        const valueSpan = marketCapCard.querySelector('.metric-value');
                        if (valueSpan) {{
                            const marketCapTrillion = data.global.total_market_cap_usd / 1_000_000_000_000;
                            valueSpan.textContent = '$' + marketCapTrillion.toFixed(2) + 'T';
                            updateCount++;
                        }}
                    }}

                    const volumeCard = doc.getElementById('global-volume-card');
                    if (volumeCard && data.global.total_volume_usd) {{
                        const valueSpan = volumeCard.querySelector('.metric-value');
                        if (valueSpan) {{
                            const volumeBillion = data.global.total_volume_usd / 1_000_000_000;
                            valueSpan.textContent = '$' + volumeBillion.toFixed(1) + 'B';
                            updateCount++;
                        }}
                    }}

                    const btcDomCard = doc.getElementById('btc-dominance-card');
                    if (btcDomCard && data.global.btc_dominance !== undefined) {{
                        const valueSpan = btcDomCard.querySelector('.metric-value');
                        if (valueSpan) {{
                            valueSpan.textContent = data.global.btc_dominance.toFixed(2) + '%';
                            updateCount++;
                        }}
                    }}
                }}

                // 마지막 업데이트 시간
                const timeElement = doc.querySelector('.refresh-update-text span');
                if (timeElement && timestamp) {{
                    const date = new Date(timestamp);
                    const formatted = date.getFullYear() + '-' +
                        String(date.getMonth() + 1).padStart(2, '0') + '-' +
                        String(date.getDate()).padStart(2, '0') + ' ' +
                        String(date.getHours()).padStart(2, '0') + ':' +
                        String(date.getMinutes()).padStart(2, '0') + ':' +
                        String(date.getSeconds()).padStart(2, '0');
                    timeElement.innerHTML = '마지막 업데이트: ' + formatted + ' | 암호화폐 시장 지수 설정 주기별 갱신';
                }}

                console.log('[WebSocket] 업데이트 완료 (' + updateCount + '개)');
            }}
        }};

        // 1초 후 연결
        setTimeout(function() {{
            window.parent.btsDashboardWebSocket.connect();
        }}, 1000);
    }})();
    </script>
    """

    components.html(websocket_js, height=1)

if __name__ == "__main__":
    main()
