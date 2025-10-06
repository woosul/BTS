"""
BTS 폼 컴포넌트

입력 폼 UI 컴포넌트
"""
import streamlit as st
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime, date

from core.enums import (
    OrderType,
    OrderSide,
    WalletType,
    TimeFrame,
    StrategyStatus
)
from core.models import (
    OrderCreate,
    WalletCreate,
    StrategyCreate,
    WalletUpdate,
    StrategyUpdate
)


def render_order_form(wallet_id: int) -> Optional[OrderCreate]:
    """
    주문 생성 폼

    Args:
        wallet_id: 지갑 ID

    Returns:
        Optional[OrderCreate]: 주문 데이터 (제출 시)
    """
    st.subheader("📝 주문 생성")

    with st.form("order_form"):
        col1, col2 = st.columns(2)

        with col1:
            order_side = st.selectbox(
                "주문 구분",
                options=[OrderSide.BUY.value, OrderSide.SELL.value],
                format_func=lambda x: "🟢 매수" if x == "buy" else "🔴 매도"
            )

            symbol = st.text_input(
                "거래 심볼",
                value="KRW-BTC",
                help="예: KRW-BTC, KRW-ETH"
            )

            quantity = st.number_input(
                "수량",
                min_value=0.0,
                value=0.001,
                step=0.001,
                format="%.8f",
                help="주문 수량"
            )

        with col2:
            order_type = st.selectbox(
                "주문 타입",
                options=[OrderType.MARKET.value, OrderType.LIMIT.value],
                format_func=lambda x: "시장가" if x == "market" else "지정가"
            )

            price = None
            if order_type == OrderType.LIMIT.value:
                price = st.number_input(
                    "지정가",
                    min_value=0.0,
                    value=50000000.0,
                    step=100000.0,
                    format="%.0f",
                    help="지정가 주문 시 가격"
                )

            strategy_id = st.number_input(
                "전략 ID (선택)",
                min_value=0,
                value=0,
                help="전략 기반 주문인 경우 전략 ID"
            )

        submitted = st.form_submit_button("주문 실행", type="primary")

        if submitted:
            try:
                order_data = OrderCreate(
                    wallet_id=wallet_id,
                    symbol=symbol,
                    order_type=OrderType(order_type),
                    order_side=OrderSide(order_side),
                    quantity=Decimal(str(quantity)),
                    price=Decimal(str(price)) if price else None,
                    strategy_id=strategy_id if strategy_id > 0 else None
                )
                return order_data

            except Exception as e:
                st.error(f"주문 데이터 생성 실패: {e}")
                return None

    return None


def render_wallet_creation_form() -> Optional[WalletCreate]:
    """
    지갑 생성 폼

    Returns:
        Optional[WalletCreate]: 지갑 생성 데이터 (제출 시)
    """
    st.subheader("💰 지갑 생성")

    with st.form("wallet_creation_form"):
        name = st.text_input(
            "지갑 이름",
            value="",
            help="지갑 이름을 입력하세요"
        )

        wallet_type = st.selectbox(
            "지갑 유형",
            options=[WalletType.VIRTUAL.value, WalletType.REAL.value],
            format_func=lambda x: "가상지갑 (모의투자)" if x == "virtual" else "실거래 지갑"
        )

        initial_balance = st.number_input(
            "초기 자본 (KRW)",
            min_value=0.0,
            value=10000000.0,
            step=1000000.0,
            format="%.0f",
            help="초기 원화 잔고"
        )

        submitted = st.form_submit_button("지갑 생성", type="primary")

        if submitted:
            if not name:
                st.error("지갑 이름을 입력하세요")
                return None

            try:
                wallet_data = WalletCreate(
                    name=name,
                    wallet_type=WalletType(wallet_type),
                    initial_balance=Decimal(str(initial_balance))
                )
                return wallet_data

            except Exception as e:
                st.error(f"지갑 데이터 생성 실패: {e}")
                return None

    return None


def render_strategy_creation_form() -> Optional[StrategyCreate]:
    """
    전략 생성 폼

    Returns:
        Optional[StrategyCreate]: 전략 생성 데이터 (제출 시)
    """
    st.subheader("🎯 전략 생성")

    with st.form("strategy_creation_form"):
        name = st.text_input(
            "전략 이름",
            value="",
            help="전략 이름을 입력하세요"
        )

        description = st.text_area(
            "설명",
            value="",
            help="전략 설명 (선택)"
        )

        timeframe = st.selectbox(
            "시간 프레임",
            options=[
                TimeFrame.MINUTE_1.value,
                TimeFrame.MINUTE_3.value,
                TimeFrame.MINUTE_5.value,
                TimeFrame.MINUTE_15.value,
                TimeFrame.MINUTE_30.value,
                TimeFrame.HOUR_1.value,
                TimeFrame.HOUR_4.value,
                TimeFrame.DAY_1.value,
                TimeFrame.WEEK_1.value
            ],
            format_func=lambda x: {
                "1m": "1분", "3m": "3분", "5m": "5분", "15m": "15분",
                "30m": "30분", "1h": "1시간", "4h": "4시간",
                "1d": "1일", "1w": "1주"
            }.get(x, x)
        )

        st.markdown("#### 전략 파라미터")

        # RSI 전략 파라미터 (기본)
        col1, col2, col3 = st.columns(3)

        with col1:
            rsi_period = st.number_input(
                "RSI 기간",
                min_value=1,
                max_value=100,
                value=14,
                help="RSI 계산 기간"
            )

        with col2:
            oversold = st.number_input(
                "과매도 기준",
                min_value=0,
                max_value=100,
                value=30,
                help="RSI 과매도 기준선"
            )

        with col3:
            overbought = st.number_input(
                "과매수 기준",
                min_value=0,
                max_value=100,
                value=70,
                help="RSI 과매수 기준선"
            )

        submitted = st.form_submit_button("전략 생성", type="primary")

        if submitted:
            if not name:
                st.error("전략 이름을 입력하세요")
                return None

            try:
                parameters = {
                    "rsi_period": rsi_period,
                    "oversold": oversold,
                    "overbought": overbought
                }

                strategy_data = StrategyCreate(
                    name=name,
                    description=description or "",
                    timeframe=TimeFrame(timeframe),
                    parameters=parameters
                )
                return strategy_data

            except Exception as e:
                st.error(f"전략 데이터 생성 실패: {e}")
                return None

    return None


def render_deposit_form(wallet_id: int) -> Optional[Decimal]:
    """
    입금 폼

    Args:
        wallet_id: 지갑 ID

    Returns:
        Optional[Decimal]: 입금액 (제출 시)
    """
    with st.form("deposit_form"):
        amount = st.number_input(
            "입금액 (KRW)",
            min_value=0.0,
            value=1000000.0,
            step=100000.0,
            format="%.0f"
        )

        description = st.text_input(
            "메모 (선택)",
            value=""
        )

        submitted = st.form_submit_button("입금", type="primary")

        if submitted:
            if amount <= 0:
                st.error("입금액은 0보다 커야 합니다")
                return None

            return Decimal(str(amount))

    return None


def render_withdraw_form(wallet_id: int, max_amount: Decimal) -> Optional[Decimal]:
    """
    출금 폼

    Args:
        wallet_id: 지갑 ID
        max_amount: 최대 출금 가능 금액

    Returns:
        Optional[Decimal]: 출금액 (제출 시)
    """
    with st.form("withdraw_form"):
        amount = st.number_input(
            "출금액 (KRW)",
            min_value=0.0,
            max_value=float(max_amount),
            value=min(1000000.0, float(max_amount)),
            step=100000.0,
            format="%.0f"
        )

        description = st.text_input(
            "메모 (선택)",
            value=""
        )

        submitted = st.form_submit_button("출금", type="primary")

        if submitted:
            if amount <= 0:
                st.error("출금액은 0보다 커야 합니다")
                return None

            if Decimal(str(amount)) > max_amount:
                st.error(f"출금 가능 금액을 초과했습니다 (최대: ₩{max_amount:,.0f})")
                return None

            return Decimal(str(amount))

    return None


def render_backtest_form() -> Optional[Dict[str, Any]]:
    """
    백테스팅 폼

    Returns:
        Optional[Dict]: 백테스팅 설정 (제출 시)
    """
    st.subheader("📊 백테스팅 설정")

    with st.form("backtest_form"):
        col1, col2 = st.columns(2)

        with col1:
            strategy_id = st.number_input(
                "전략 ID",
                min_value=1,
                value=1,
                help="백테스팅할 전략 ID"
            )

            symbol = st.text_input(
                "거래 심볼",
                value="KRW-BTC",
                help="백테스팅 대상 심볼"
            )

        with col2:
            start_date = st.date_input(
                "시작일",
                value=date.today().replace(day=1),
                help="백테스팅 시작일"
            )

            end_date = st.date_input(
                "종료일",
                value=date.today(),
                help="백테스팅 종료일"
            )

        initial_balance = st.number_input(
            "초기 자본 (KRW)",
            min_value=0.0,
            value=10000000.0,
            step=1000000.0,
            format="%.0f",
            help="백테스팅 초기 자본"
        )

        submitted = st.form_submit_button("백테스팅 시작", type="primary")

        if submitted:
            if start_date >= end_date:
                st.error("시작일은 종료일보다 이전이어야 합니다")
                return None

            return {
                "strategy_id": strategy_id,
                "symbol": symbol,
                "start_date": datetime.combine(start_date, datetime.min.time()),
                "end_date": datetime.combine(end_date, datetime.max.time()),
                "initial_balance": Decimal(str(initial_balance))
            }

    return None


def render_strategy_update_form(strategy_id: int, current_params: Dict) -> Optional[StrategyUpdate]:
    """
    전략 수정 폼

    Args:
        strategy_id: 전략 ID
        current_params: 현재 파라미터

    Returns:
        Optional[StrategyUpdate]: 전략 수정 데이터 (제출 시)
    """
    st.subheader("✏️ 전략 수정")

    with st.form("strategy_update_form"):
        name = st.text_input(
            "전략 이름",
            value=""
        )

        description = st.text_area(
            "설명",
            value=""
        )

        st.markdown("#### 파라미터 수정")

        col1, col2, col3 = st.columns(3)

        with col1:
            rsi_period = st.number_input(
                "RSI 기간",
                min_value=1,
                max_value=100,
                value=current_params.get("rsi_period", 14)
            )

        with col2:
            oversold = st.number_input(
                "과매도 기준",
                min_value=0,
                max_value=100,
                value=current_params.get("oversold", 30)
            )

        with col3:
            overbought = st.number_input(
                "과매수 기준",
                min_value=0,
                max_value=100,
                value=current_params.get("overbought", 70)
            )

        submitted = st.form_submit_button("수정", type="primary")

        if submitted:
            try:
                update_data = {}

                if name:
                    update_data["name"] = name

                if description:
                    update_data["description"] = description

                # 파라미터가 변경된 경우만 업데이트
                new_params = {
                    "rsi_period": rsi_period,
                    "oversold": oversold,
                    "overbought": overbought
                }

                if new_params != current_params:
                    update_data["parameters"] = new_params

                if not update_data:
                    st.warning("변경된 내용이 없습니다")
                    return None

                strategy_update = StrategyUpdate(**update_data)
                return strategy_update

            except Exception as e:
                st.error(f"전략 수정 데이터 생성 실패: {e}")
                return None

    return None
