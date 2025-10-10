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
                format_func=lambda x: "매수" if x == "buy" else "매도"
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
    st.subheader("지갑 생성")

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


def render_strategy_creation_form(strategy_type: str = "rsi") -> Optional[StrategyCreate]:
    """
    전략 생성 폼

    Args:
        strategy_type: 전략 타입 (rsi, macd_entry, stochastic_entry 등)

    Returns:
        Optional[StrategyCreate]: 전략 생성 데이터 (제출 시)
    """
    st.subheader("전략 생성")

    with st.form(f"strategy_creation_form_{strategy_type}"):
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

        parameters = {}

        # 전략 타입별 파라미터 입력
        if strategy_type == "rsi":
            col1, col2, col3 = st.columns(3)
            with col1:
                parameters["rsi_period"] = st.number_input("RSI 기간", min_value=1, max_value=100, value=14)
            with col2:
                parameters["oversold"] = st.number_input("과매도 기준", min_value=0, max_value=100, value=30)
            with col3:
                parameters["overbought"] = st.number_input("과매수 기준", min_value=0, max_value=100, value=70)

        elif strategy_type == "macd_entry":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                parameters["fast_period"] = st.number_input("Fast EMA", min_value=1, max_value=100, value=12)
            with col2:
                parameters["slow_period"] = st.number_input("Slow EMA", min_value=1, max_value=100, value=26)
            with col3:
                parameters["signal_period"] = st.number_input("Signal", min_value=1, max_value=50, value=9)
            with col4:
                parameters["min_confidence"] = st.number_input("최소 확신도", min_value=0.0, max_value=1.0, value=0.65, step=0.05)

        elif strategy_type == "stochastic_entry":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                parameters["k_period"] = st.number_input("%K 기간", min_value=1, max_value=100, value=14)
            with col2:
                parameters["d_period"] = st.number_input("%D 기간", min_value=1, max_value=50, value=3)
            with col3:
                parameters["smooth"] = st.number_input("스무딩", min_value=1, max_value=10, value=3)
            with col4:
                parameters["oversold"] = st.number_input("과매도 기준", min_value=0, max_value=50, value=20)

        elif strategy_type == "multi_indicator_entry":
            st.markdown("**사용할 지표 선택**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                parameters["use_rsi"] = st.checkbox("RSI", value=True)
            with col2:
                parameters["use_macd"] = st.checkbox("MACD", value=True)
            with col3:
                parameters["use_bollinger"] = st.checkbox("Bollinger Bands", value=True)
            with col4:
                parameters["use_volume"] = st.checkbox("거래량", value=True)

            col1, col2 = st.columns(2)
            with col1:
                parameters["combination_mode"] = st.selectbox(
                    "조합 모드",
                    options=["AND", "OR"],
                    help="AND: 모든 지표 충족, OR: 최소 N개 지표 충족"
                )
            with col2:
                if parameters["combination_mode"] == "OR":
                    parameters["min_indicators"] = st.number_input("최소 충족 지표 수", min_value=1, max_value=4, value=2)

        elif strategy_type == "hybrid_entry":
            st.markdown("**전략 가중치 설정**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                macd_w = st.number_input("MACD 가중치", min_value=0.0, max_value=1.0, value=0.35, step=0.05)
            with col2:
                stoch_w = st.number_input("Stochastic 가중치", min_value=0.0, max_value=1.0, value=0.30, step=0.05)
            with col3:
                rsi_w = st.number_input("RSI 가중치", min_value=0.0, max_value=1.0, value=0.20, step=0.05)
            with col4:
                vol_w = st.number_input("거래량 가중치", min_value=0.0, max_value=1.0, value=0.15, step=0.05)

            total_weight = macd_w + stoch_w + rsi_w + vol_w
            if abs(total_weight - 1.0) > 0.01:
                st.markdown(f"""
                    <div style='
                        background-color: #1e1e1e;
                        border: 1px solid #ffa500;
                        border-radius: 4px;
                        padding: 8px 12px;
                        margin: 8px 0;
                    '>
                        <div style='color: #ffa500; font-size: 0.85rem;'>
                            가중치 합계가 1이 아닙니다: {total_weight:.2f}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            parameters["strategy_weights"] = {
                "macd": macd_w,
                "stochastic": stoch_w,
                "rsi": rsi_w,
                "volume": vol_w
            }
            parameters["buy_threshold"] = st.number_input("매수 임계값", min_value=0.0, max_value=1.0, value=0.65, step=0.05)

        # Exit 전략 파라미터
        elif strategy_type == "macd_exit":
            col1, col2, col3 = st.columns(3)
            with col1:
                parameters["fast_period"] = st.number_input("Fast EMA", min_value=1, max_value=100, value=12)
            with col2:
                parameters["slow_period"] = st.number_input("Slow EMA", min_value=1, max_value=100, value=26)
            with col3:
                parameters["signal_period"] = st.number_input("Signal", min_value=1, max_value=50, value=9)

            parameters["cross_mode"] = st.selectbox(
                "크로스 모드",
                options=["signal", "zero", "both"],
                help="signal: 시그널선 데드크로스, zero: 0선 하향돌파, both: 둘 다"
            )
            parameters["min_confidence"] = st.number_input("최소 확신도", min_value=0.0, max_value=1.0, value=0.70, step=0.05)

        elif strategy_type == "stochastic_exit":
            col1, col2, col3 = st.columns(3)
            with col1:
                parameters["k_period"] = st.number_input("%K 기간", min_value=1, max_value=100, value=14)
            with col2:
                parameters["d_period"] = st.number_input("%D 기간", min_value=1, max_value=50, value=3)
            with col3:
                parameters["smooth"] = st.number_input("스무딩", min_value=1, max_value=10, value=3)

            col1, col2 = st.columns(2)
            with col1:
                parameters["overbought"] = st.number_input("과매수 기준", min_value=50, max_value=100, value=80)
            with col2:
                parameters["cross_required"] = st.checkbox("데드크로스 필수", value=False)

        elif strategy_type == "time_based_exit":
            st.markdown("**기본 설정**")
            col1, col2 = st.columns(2)
            with col1:
                parameters["force_exit"] = st.checkbox("강제 매도 (손실 중에도)", value=False)
            with col2:
                parameters["min_profit_pct"] = st.number_input("최소 익절률 (%)", min_value=-10.0, max_value=100.0, value=0.0, step=1.0)

            st.markdown("**날짜/시간 제약 (선택)**")
            use_datetime = st.checkbox("날짜/시간 제약 사용", value=False)
            parameters["use_datetime_constraint"] = use_datetime

            if use_datetime:
                datetime_mode = st.radio(
                    "모드",
                    options=["relative", "absolute"],
                    format_func=lambda x: "상대 시간 (매수 후 N일/시간)" if x == "relative" else "절대 시각 (특정 날짜/시간)",
                    horizontal=True
                )
                parameters["datetime_mode"] = datetime_mode

                if datetime_mode == "relative":
                    col1, col2 = st.columns(2)
                    with col1:
                        parameters["relative_exit_days"] = st.number_input("매수 후 N일", min_value=0, max_value=365, value=0)
                    with col2:
                        parameters["relative_exit_hours"] = st.number_input("매수 후 N시간", min_value=0, max_value=8760, value=24)
                else:  # absolute
                    exit_datetime = st.datetime_input("목표 매도 시각", value=datetime.now())
                    parameters["absolute_exit_datetime"] = exit_datetime
            else:
                # 기존 모드
                col1, col2 = st.columns(2)
                with col1:
                    parameters["holding_periods"] = st.number_input("보유 기간 (캔들 수)", min_value=1, max_value=1000, value=24)
                with col2:
                    parameters["holding_hours"] = st.number_input("보유 시간 (시간, 선택)", min_value=0, max_value=8760, value=0)

        elif strategy_type == "fixed_target_exit":
            col1, col2 = st.columns(2)
            with col1:
                parameters["target_profit_pct"] = st.number_input("목표 익절률 (%)", min_value=0.0, max_value=1000.0, value=10.0, step=1.0)
            with col2:
                parameters["stop_loss_pct"] = st.number_input("손절률 (%)", min_value=-100.0, max_value=0.0, value=-5.0, step=1.0)

        elif strategy_type == "trailing_stop_exit":
            col1, col2, col3 = st.columns(3)
            with col1:
                parameters["trailing_pct"] = st.number_input("트레일링 비율 (%)", min_value=0.0, max_value=50.0, value=3.0, step=0.5)
            with col2:
                parameters["activation_profit"] = st.number_input("활성화 수익률 (%)", min_value=0.0, max_value=100.0, value=3.0, step=1.0)
            with col3:
                parameters["stop_loss_pct"] = st.number_input("손절률 (%)", min_value=-100.0, max_value=0.0, value=-5.0, step=1.0)

        elif strategy_type == "hybrid_exit":
            st.markdown("**전략 가중치 설정**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                fixed_w = st.number_input("Fixed Target", min_value=0.0, max_value=1.0, value=0.40, step=0.05)
            with col2:
                trail_w = st.number_input("Trailing Stop", min_value=0.0, max_value=1.0, value=0.35, step=0.05)
            with col3:
                rsi_w = st.number_input("RSI", min_value=0.0, max_value=1.0, value=0.15, step=0.05)
            with col4:
                time_w = st.number_input("Time-based", min_value=0.0, max_value=1.0, value=0.10, step=0.05)

            total_weight = fixed_w + trail_w + rsi_w + time_w
            if abs(total_weight - 1.0) > 0.01:
                st.markdown(f"""
                    <div style='
                        background-color: #1e1e1e;
                        border: 1px solid #ffa500;
                        border-radius: 4px;
                        padding: 8px 12px;
                        margin: 8px 0;
                    '>
                        <div style='color: #ffa500; font-size: 0.85rem;'>
                            가중치 합계가 1이 아닙니다: {total_weight:.2f}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            parameters["strategy_weights"] = {
                "fixed_target": fixed_w,
                "trailing_stop": trail_w,
                "rsi": rsi_w,
                "time_based": time_w
            }
            parameters["sell_threshold"] = st.number_input("매도 임계값", min_value=0.0, max_value=1.0, value=0.75, step=0.05)

        submitted = st.form_submit_button("전략 생성", type="primary")

        if submitted:
            if not name:
                st.error("전략 이름을 입력하세요")
                return None

            try:
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
    st.subheader("백테스팅 설정")

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
    st.subheader("전략 수정")

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
