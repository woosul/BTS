"""
BTS 대시보드 페이지

전체 현황 및 주요 지표 표시
"""
import streamlit as st
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.database.connection import get_db_session
from application.services.wallet_service import WalletService
from application.services.trading_service import TradingService
from application.services.strategy_service import StrategyService
from infrastructure.exchanges.upbit_client import UpbitClient
from presentation.components.metrics import (
    display_wallet_metrics,
    display_trading_metrics,
    display_performance_summary,
    display_recent_trades_table
)
from presentation.components.charts import (
    render_profit_chart,
    render_candlestick_chart
)
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="대시보드 - BTS",
    page_icon="📊",
    layout="wide"
)

def get_services():
    """서비스 인스턴스 가져오기"""
    if 'db' not in st.session_state:
        db_gen = get_db_session()
        st.session_state.db = next(db_gen)

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
    st.title("📊 대시보드")
    st.markdown("---")

    # 서비스 초기화
    wallet_service, trading_service, strategy_service = get_services()

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

    # 지갑 메트릭
    st.subheader("💰 지갑 현황")
    display_wallet_metrics(wallet)

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

            st.subheader("📈 트레이딩 통계")
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

    # 전략 현황
    try:
        strategies = strategy_service.get_all_strategies()
        active_strategies = [s for s in strategies if s.status.value == "active"]

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🎯 활성 전략")
            if active_strategies:
                for strategy in active_strategies:
                    with st.expander(f"📌 {strategy.name}", expanded=False):
                        st.write(f"**설명**: {strategy.description}")
                        st.write(f"**시간프레임**: {strategy.timeframe.value}")
                        st.write(f"**파라미터**:")
                        for key, value in strategy.parameters.items():
                            st.write(f"  - {key}: {value}")
            else:
                st.info("활성화된 전략이 없습니다.")

        with col2:
            st.subheader("📡 최근 시그널")
            if active_strategies:
                # 첫 번째 활성 전략의 시그널 생성
                try:
                    strategy = active_strategies[0]
                    signal = strategy_service.generate_signal(
                        strategy.id,
                        "KRW-BTC"
                    )

                    # 시그널 표시
                    signal_colors = {
                        "buy": "🟢",
                        "sell": "🔴",
                        "hold": "🟡"
                    }

                    signal_text = {
                        "buy": "매수",
                        "sell": "매도",
                        "hold": "관망"
                    }

                    icon = signal_colors.get(signal.signal.value, "⚪")
                    text = signal_text.get(signal.signal.value, signal.signal.value)

                    st.markdown(f"### {icon} {text}")
                    st.metric(
                        "확신도",
                        f"{signal.confidence * 100:.1f}%",
                        help="시그널 확신도"
                    )

                    if signal.metadata:
                        st.write("**메타데이터**:")
                        for key, value in signal.metadata.items():
                            if isinstance(value, float):
                                st.write(f"  - {key}: {value:.2f}")
                            else:
                                st.write(f"  - {key}: {value}")

                except Exception as e:
                    logger.error(f"시그널 생성 실패: {e}")
                    st.error(f"시그널 생성 실패: {e}")
            else:
                st.info("활성화된 전략이 없습니다.")

    except Exception as e:
        logger.error(f"전략 조회 실패: {e}")
        st.error(f"전략 조회 실패: {e}")

    st.markdown("---")

    # 차트
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 가격 차트")
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
        st.subheader("💰 수익 차트")
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
    st.subheader("📜 최근 거래 내역")
    if trades:
        display_recent_trades_table(trades, limit=10)
    else:
        st.info("거래 내역이 없습니다.")

if __name__ == "__main__":
    main()
