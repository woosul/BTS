"""
BTS 가상지갑 페이지

지갑 관리, 입출금, 자산 조회
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
from infrastructure.exchanges.upbit_client import UpbitClient
from presentation.components.forms import (
    render_wallet_creation_form,
    render_deposit_form,
    render_withdraw_form,
    render_order_form
)
from presentation.components.metrics import (
    display_wallet_metrics,
    display_asset_table,
    display_recent_trades_table
)
from presentation.components.charts import render_portfolio_pie_chart
from core.enums import WalletType
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="가상지갑 - BTS",
    page_icon="💰",
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

    return (
        st.session_state.wallet_service,
        st.session_state.trading_service
    )

def main():
    st.title("💰 가상지갑")
    st.markdown("---")

    # 서비스 초기화
    wallet_service, trading_service = get_services()

    # 탭: 지갑 관리 / 지갑 생성
    tab1, tab2 = st.tabs(["📋 지갑 관리", "➕ 지갑 생성"])

    # ===== 탭 1: 지갑 관리 =====
    with tab1:
        try:
            # 가상지갑만 조회
            wallets = wallet_service.get_all_wallets(wallet_type=WalletType.VIRTUAL)

            if not wallets:
                st.info("등록된 가상지갑이 없습니다. '지갑 생성' 탭에서 새 지갑을 만드세요.")
            else:
                # 지갑 선택
                selected_wallet_id = st.selectbox(
                    "지갑 선택",
                    options=[w.id for w in wallets],
                    format_func=lambda x: next(
                        (f"{w.name} - ₩{w.balance_krw:,.0f}" for w in wallets if w.id == x),
                        str(x)
                    )
                )

                wallet = wallet_service.get_wallet(selected_wallet_id)

                # 지갑 메트릭
                st.markdown("### 📊 지갑 현황")
                display_wallet_metrics(wallet)

                st.markdown("---")

                # 입출금 및 거래
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("#### 💵 입금")
                    deposit_amount = render_deposit_form(wallet.id)

                    if deposit_amount:
                        try:
                            wallet = wallet_service.deposit(
                                wallet.id,
                                deposit_amount,
                                "수동 입금"
                            )
                            st.success(f"₩{deposit_amount:,.0f} 입금 완료")
                            st.rerun()

                        except Exception as e:
                            logger.error(f"입금 실패: {e}")
                            st.error(f"입금 실패: {e}")

                with col2:
                    st.markdown("#### 💸 출금")
                    withdraw_amount = render_withdraw_form(wallet.id, wallet.balance_krw)

                    if withdraw_amount:
                        try:
                            wallet = wallet_service.withdraw(
                                wallet.id,
                                withdraw_amount,
                                "수동 출금"
                            )
                            st.success(f"₩{withdraw_amount:,.0f} 출금 완료")
                            st.rerun()

                        except Exception as e:
                            logger.error(f"출금 실패: {e}")
                            st.error(f"출금 실패: {e}")

                with col3:
                    st.markdown("#### 🔄 주문")
                    order_data = render_order_form(wallet.id)

                    if order_data:
                        try:
                            # 주문 생성 및 실행
                            order = trading_service.create_order(order_data)
                            order = trading_service.execute_order(order.id)

                            st.success(
                                f"{order.symbol} "
                                f"{'매수' if order.order_side.value == 'buy' else '매도'} "
                                f"{order.quantity} 체결"
                            )
                            st.rerun()

                        except Exception as e:
                            logger.error(f"주문 실행 실패: {e}")
                            st.error(f"주문 실행 실패: {e}")

                st.markdown("---")

                # 보유 자산
                st.markdown("### 💎 보유 자산")

                try:
                    holdings = wallet_service.get_asset_holdings(wallet.id)

                    if holdings:
                        # 실시간 가격 조회
                        exchange = UpbitClient()
                        holdings_with_price = []

                        for holding in holdings:
                            try:
                                ticker = exchange.get_ticker(f"KRW-{holding.symbol}")
                                current_price = ticker.price

                                profit_loss = (current_price - holding.avg_price) * holding.quantity
                                profit_loss_rate = (
                                    (current_price - holding.avg_price) / holding.avg_price * 100
                                )

                                holdings_with_price.append({
                                    "symbol": holding.symbol,
                                    "quantity": holding.quantity,
                                    "avg_price": holding.avg_price,
                                    "current_price": current_price,
                                    "profit_loss": profit_loss,
                                    "profit_loss_rate": profit_loss_rate
                                })

                            except Exception as e:
                                logger.warning(f"{holding.symbol} 가격 조회 실패: {e}")
                                holdings_with_price.append({
                                    "symbol": holding.symbol,
                                    "quantity": holding.quantity,
                                    "avg_price": holding.avg_price,
                                    "current_price": holding.avg_price,
                                    "profit_loss": Decimal("0"),
                                    "profit_loss_rate": Decimal("0")
                                })

                        # 자산 테이블
                        display_asset_table(holdings_with_price)

                        # 포트폴리오 차트
                        st.markdown("---")
                        st.markdown("### 📊 포트폴리오 구성")

                        portfolio_data = [
                            {
                                "symbol": h["symbol"],
                                "value": h["quantity"] * h["current_price"]
                            }
                            for h in holdings_with_price
                        ]

                        # 원화 잔고 추가
                        if wallet.balance_krw > 0:
                            portfolio_data.append({
                                "symbol": "KRW",
                                "value": wallet.balance_krw
                            })

                        fig = render_portfolio_pie_chart(
                            portfolio_data,
                            title="자산 분포",
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    else:
                        st.info("보유 자산이 없습니다.")

                except Exception as e:
                    logger.error(f"자산 조회 실패: {e}")
                    st.error(f"자산 조회 실패: {e}")

                st.markdown("---")

                # 거래 내역
                st.markdown("### 📜 거래 내역")

                try:
                    trades = trading_service.get_wallet_trades(wallet.id, limit=20)

                    if trades:
                        display_recent_trades_table(trades, limit=20)
                    else:
                        st.info("거래 내역이 없습니다.")

                except Exception as e:
                    logger.error(f"거래 내역 조회 실패: {e}")
                    st.error(f"거래 내역 조회 실패: {e}")

        except Exception as e:
            logger.error(f"지갑 관리 오류: {e}")
            st.error(f"지갑 관리 오류: {e}")

    # ===== 탭 2: 지갑 생성 =====
    with tab2:
        wallet_data = render_wallet_creation_form()

        if wallet_data:
            # 가상지갑만 생성 가능
            if wallet_data.wallet_type != WalletType.VIRTUAL:
                st.warning("이 페이지에서는 가상지갑만 생성할 수 있습니다.")
            else:
                try:
                    wallet = wallet_service.create_wallet(wallet_data)
                    st.success(
                        f"가상지갑 '{wallet.name}' 생성 완료\n\n"
                        f"초기 자본: ₩{wallet.balance_krw:,.0f}"
                    )
                    logger.info(f"가상지갑 생성: {wallet.name}")
                    st.rerun()

                except Exception as e:
                    logger.error(f"지갑 생성 실패: {e}")
                    st.error(f"지갑 생성 실패: {e}")

if __name__ == "__main__":
    main()
