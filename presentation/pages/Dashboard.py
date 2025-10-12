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
from application.services.market_index_service import MarketIndexService
from infrastructure.exchanges.upbit_client import UpbitClient
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
    st.markdown("---")

    # 업비트 종합지수 + USD 환율
    try:
        market_index_service = MarketIndexService()

        # 캐시를 사용하여 Playwright 호출 최소화 (5분 캐시)
        @st.cache_data(ttl=300)
        def get_cached_upbit_indices():
            service = MarketIndexService()
            return service.get_upbit_indices()

        @st.cache_data(ttl=300)
        def get_cached_usd_rate():
            service = MarketIndexService()
            return service.get_usd_krw_rate()

        with st.spinner('업비트 지수 로딩 중...'):
            upbit_data = get_cached_upbit_indices()
            usd_data = get_cached_usd_rate()

        # 업비트 지수 카드 그룹 (4개 지수 + USD 환율 = 5개)
        upbit_metrics = []
        indices_config = [
            ('ubci', 'UBCI'),
            ('ubmi', 'UBMI'),
            ('ub10', 'UB10'),
            ('ub30', 'UB30')
        ]

        for key, label in indices_config:
            index_data = upbit_data.get(key, {})
            value = index_data.get('value', 0)
            change_rate = index_data.get('change_rate', 0)

            logger.info(f"Dashboard 업비트 지수: {key}={value}, change_rate={change_rate}")

            if value > 0:
                upbit_metrics.append({
                    "label": label,
                    "value": f"{value:,.2f}",
                    "delta": change_rate
                })
            else:
                upbit_metrics.append({
                    "label": label,
                    "value": "N/A",
                    "delta": None
                })

        # USD 환율 추가
        if usd_data['value'] > 0:
            upbit_metrics.append({
                "label": "USD/KRW",
                "value": f"₩{usd_data['value']:,.2f}",
                "delta": usd_data['change_rate']
            })
        else:
            upbit_metrics.append({
                "label": "USD/KRW",
                "value": "N/A",
                "delta": None
            })

        render_metric_card_group(
            title="업비트 종합지수",
            metrics=upbit_metrics,
            columns=5
        )

        st.markdown("")  # 간격

    except Exception as e:
        logger.error(f"업비트 지수 표시 실패: {e}", exc_info=True)
        st.error(f"업비트 지수를 불러오는데 실패했습니다: {str(e)}")

    # 글로벌 마켓 지수 + 7일 평균 (통합)
    try:
        market_index_service = MarketIndexService()
        global_data = market_index_service.get_global_crypto_data()

        # 상위 코인 7일 추세 데이터 가져오기
        @st.cache_data(ttl=300)  # 5분 캐시
        def get_cached_sparkline_data():
            return market_index_service.get_top_coins_with_sparkline(limit=10)

        coins_data = get_cached_sparkline_data()

        # 글로벌 + 7일 평균 통합 카드 (5개 구성)
        market_cap_trillion = global_data['total_market_cap_usd'] / 1_000_000_000_000
        volume_billion = global_data['total_volume_usd'] / 1_000_000_000

        combined_metrics = [
            {
                "label": "총 시가총액",
                "value": f"${market_cap_trillion:.2f}T",
                "delta": global_data['market_cap_change_24h']  # 24h 변동률 있음
            },
            {
                "label": "24h 거래량",
                "value": f"${volume_billion:.1f}B",
                "delta": None  # 변동률 데이터 없음
            },
            {
                "label": "BTC 도미넌스",
                "value": f"{global_data['btc_dominance']:.2f}%",
                "delta": None  # 변동률 데이터 없음
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
            title="글로벌 암호화폐 시장",
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

if __name__ == "__main__":
    main()
