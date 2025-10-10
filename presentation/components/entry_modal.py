"""
매수 전략 설정 팝업 모달
"""
import streamlit as st
from typing import Dict, Optional
from presentation.components.modal_utils import apply_modal_styles


@st.dialog("매수 전략 설정", width="large")
def show_entry_config_modal(
    strategy_name: str,
    strategy_type: str,
    current_params: Optional[Dict] = None
) -> Optional[Dict]:
    """
    매수 전략 설정 팝업 모달

    Args:
        strategy_name: 전략 이름
        strategy_type: 전략 타입 (macd_entry, stochastic_entry, etc.)
        current_params: 현재 설정된 파라미터

    Returns:
        Optional[Dict]: 설정된 파라미터 (취소 시 None)
    """
    # 모달창 공통 스타일 적용
    apply_modal_styles()
    
    st.markdown(f"### {strategy_name}")

    params = current_params.copy() if current_params else {}

    # 전략 타입별 설정 UI
    if strategy_type == "macd_entry":
        params = _macd_entry_config_ui(params)
    elif strategy_type == "stochastic_entry":
        params = _stochastic_entry_config_ui(params)
    elif strategy_type == "multi_indicator_entry":
        params = _multi_indicator_entry_config_ui(params)
    elif strategy_type == "hybrid_entry":
        params = _hybrid_entry_config_ui(params)

    # 하단 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("적용", type="primary", use_container_width=True):
            st.session_state[f"entry_params_{strategy_type}"] = params
            st.rerun()
    with col2:
        if st.button("취소", use_container_width=True):
            st.rerun()

    return None


def _macd_entry_config_ui(params: Dict) -> Dict:
    """MACD 매수 전략 설정 UI"""
    st.write("**MACD 파라미터**")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["fast_period"] = st.number_input(
            "Fast Period",
            5, 30,
            params.get("fast_period", 12),
            1,
            help="단기 EMA 기간"
        )
    with col2:
        params["slow_period"] = st.number_input(
            "Slow Period",
            15, 60,
            params.get("slow_period", 26),
            1,
            help="장기 EMA 기간"
        )
    with col3:
        params["signal_period"] = st.number_input(
            "Signal Period",
            5, 20,
            params.get("signal_period", 9),
            1,
            help="시그널 라인 기간"
        )

    st.markdown("---")
    st.write("**매수 조건**")

    params["cross_mode"] = st.checkbox(
        "골든 크로스 매수",
        params.get("cross_mode", True),
        help="MACD가 시그널을 상향 돌파 시 매수"
    )

    params["histogram_mode"] = st.checkbox(
        "히스토그램 양전환 매수",
        params.get("histogram_mode", False),
        help="히스토그램이 음에서 양으로 전환 시 매수"
    )

    params["min_confidence"] = st.slider(
        "최소 신뢰도",
        0.0, 1.0,
        params.get("min_confidence", 0.6),
        0.05,
        help="이 신뢰도 이상일 때만 매수"
    )

    return params


def _stochastic_entry_config_ui(params: Dict) -> Dict:
    """Stochastic 매수 전략 설정 UI"""
    st.write("**Stochastic 파라미터**")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["k_period"] = st.number_input(
            "%K Period",
            5, 30,
            params.get("k_period", 14),
            1
        )
    with col2:
        params["d_period"] = st.number_input(
            "%D Period",
            1, 10,
            params.get("d_period", 3),
            1
        )
    with col3:
        params["smooth"] = st.number_input(
            "Smooth",
            1, 10,
            params.get("smooth", 3),
            1
        )

    st.markdown("---")
    st.write("**매수 조건**")

    params["oversold_level"] = st.slider(
        "과매도 기준",
        0, 50,
        params.get("oversold_level", 20),
        5,
        help="이 값 이하일 때 과매도로 판단"
    )

    params["cross_mode"] = st.checkbox(
        "%K와 %D 골든 크로스",
        params.get("cross_mode", True),
        help="%K가 %D를 상향 돌파 시 매수"
    )

    return params


def _multi_indicator_entry_config_ui(params: Dict) -> Dict:
    """복합 지표 매수 전략 설정 UI"""
    st.write("**사용할 지표 선택**")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["use_rsi"] = st.checkbox("RSI", params.get("use_rsi", True))
    with col2:
        params["use_macd"] = st.checkbox("MACD", params.get("use_macd", True))
    with col3:
        params["use_bb"] = st.checkbox("Bollinger Bands", params.get("use_bb", True))

    st.markdown("---")
    st.write("**조합 방식**")

    params["combination_mode"] = st.radio(
        "신호 조합",
        options=["AND", "OR"],
        index=0 if params.get("combination_mode", "AND") == "AND" else 1,
        help="AND: 모든 지표 동시 충족 / OR: 하나만 충족"
    )

    if params.get("use_rsi"):
        with st.expander("RSI 설정"):
            params["rsi_period"] = st.number_input("RSI 기간", 5, 50, params.get("rsi_period", 14), 1)
            params["rsi_oversold"] = st.slider("과매도 기준", 0, 50, params.get("rsi_oversold", 30), 5)

    if params.get("use_macd"):
        with st.expander("MACD 설정"):
            col1, col2, col3 = st.columns(3)
            with col1:
                params["macd_fast"] = st.number_input("Fast", 5, 30, params.get("macd_fast", 12), 1)
            with col2:
                params["macd_slow"] = st.number_input("Slow", 15, 60, params.get("macd_slow", 26), 1)
            with col3:
                params["macd_signal"] = st.number_input("Signal", 5, 20, params.get("macd_signal", 9), 1)

    if params.get("use_bb"):
        with st.expander("Bollinger Bands 설정"):
            col1, col2 = st.columns(2)
            with col1:
                params["bb_period"] = st.number_input("기간", 5, 50, params.get("bb_period", 20), 1)
            with col2:
                params["bb_std"] = st.slider("표준편차", 1.0, 3.0, params.get("bb_std", 2.0), 0.1)

    return params


def _hybrid_entry_config_ui(params: Dict) -> Dict:
    """하이브리드 매수 전략 설정 UI"""
    st.write("**전략 가중치 설정** (합계 1.0)")

    col1, col2, col3 = st.columns(3)
    with col1:
        macd_w = st.slider("MACD", 0.0, 1.0, 0.4, 0.05, key="entry_hybrid_macd_w")
    with col2:
        stoch_w = st.slider("Stochastic", 0.0, 1.0, 0.3, 0.05, key="entry_hybrid_stoch_w")
    with col3:
        rsi_w = st.slider("RSI", 0.0, 1.0, 0.3, 0.05, key="entry_hybrid_rsi_w")

    total = macd_w + stoch_w + rsi_w
    if abs(total - 1.0) > 0.01:
        st.warning(f"전략 가중치 합계: {total:.2f}")
    else:
        st.success(f"전략 가중치 합계: {total:.2f}")

    params["strategy_weights"] = {
        "macd": macd_w,
        "stochastic": stoch_w,
        "rsi": rsi_w
    }

    st.markdown("---")
    params["min_confidence"] = st.slider(
        "최소 신뢰도",
        0.0, 1.0,
        params.get("min_confidence", 0.6),
        0.05,
        help="이 신뢰도 이상일 때만 매수"
    )

    return params
