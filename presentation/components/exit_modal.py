"""
매도 전략 설정 팝업 모달
"""
import streamlit as st
from typing import Dict, Optional


@st.dialog("매도 전략 설정", width="large")
def show_exit_config_modal(
    strategy_name: str,
    strategy_type: str,
    current_params: Optional[Dict] = None
) -> Optional[Dict]:
    """
    매도 전략 설정 팝업 모달

    Args:
        strategy_name: 전략 이름
        strategy_type: 전략 타입 (macd_exit, time_based_exit, etc.)
        current_params: 현재 설정된 파라미터

    Returns:
        Optional[Dict]: 설정된 파라미터 (취소 시 None)
    """
    st.markdown(f"### {strategy_name}")

    params = current_params.copy() if current_params else {}

    # 전략 타입별 설정 UI
    if strategy_type == "macd_exit":
        params = _macd_exit_config_ui(params)
    elif strategy_type == "stochastic_exit":
        params = _stochastic_exit_config_ui(params)
    elif strategy_type == "time_based_exit":
        params = _time_based_exit_config_ui(params)
    elif strategy_type == "fixed_target_exit":
        params = _fixed_target_exit_config_ui(params)
    elif strategy_type == "trailing_stop_exit":
        params = _trailing_stop_exit_config_ui(params)
    elif strategy_type == "hybrid_exit":
        params = _hybrid_exit_config_ui(params)

    # 하단 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("적용", type="primary", use_container_width=True):
            st.session_state[f"exit_params_{strategy_type}"] = params
            st.rerun()
    with col2:
        if st.button("취소", use_container_width=True):
            st.rerun()

    return None


def _macd_exit_config_ui(params: Dict) -> Dict:
    """MACD 매도 전략 설정 UI"""
    st.write("**MACD 파라미터**")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["fast_period"] = st.number_input(
            "Fast Period",
            5, 30,
            params.get("fast_period", 12),
            1
        )
    with col2:
        params["slow_period"] = st.number_input(
            "Slow Period",
            15, 60,
            params.get("slow_period", 26),
            1
        )
    with col3:
        params["signal_period"] = st.number_input(
            "Signal Period",
            5, 20,
            params.get("signal_period", 9),
            1
        )

    st.markdown("---")
    st.write("**매도 조건**")

    params["cross_mode"] = st.checkbox(
        "데드 크로스 매도",
        params.get("cross_mode", True),
        help="MACD가 시그널을 하향 돌파 시 매도"
    )

    params["min_confidence"] = st.slider(
        "최소 신뢰도",
        0.0, 1.0,
        params.get("min_confidence", 0.6),
        0.05
    )

    return params


def _stochastic_exit_config_ui(params: Dict) -> Dict:
    """Stochastic 매도 전략 설정 UI"""
    st.write("**Stochastic 파라미터**")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["k_period"] = st.number_input("%K Period", 5, 30, params.get("k_period", 14), 1)
    with col2:
        params["d_period"] = st.number_input("%D Period", 1, 10, params.get("d_period", 3), 1)
    with col3:
        params["smooth"] = st.number_input("Smooth", 1, 10, params.get("smooth", 3), 1)

    st.markdown("---")
    st.write("**매도 조건**")

    params["overbought_level"] = st.slider(
        "과매수 기준",
        50, 100,
        params.get("overbought_level", 80),
        5,
        help="이 값 이상일 때 과매수로 판단하여 매도"
    )

    return params


def _time_based_exit_config_ui(params: Dict) -> Dict:
    """시간 기반 매도 전략 설정 UI"""
    st.write("**보유 기간 설정**")

    params["holding_hours"] = st.number_input(
        "보유 시간 (시간)",
        1, 720,
        params.get("holding_hours", 24),
        1,
        help="설정된 시간이 경과하면 자동 매도"
    )

    st.markdown("---")
    st.write("**추가 조건**")

    params["allow_early_exit"] = st.checkbox(
        "조기 매도 허용",
        params.get("allow_early_exit", True),
        help="목표 수익 또는 손절 조건 충족 시 보유 기간 이전에도 매도"
    )

    if params.get("allow_early_exit"):
        col1, col2 = st.columns(2)
        with col1:
            params["target_profit_pct"] = st.slider(
                "목표 수익률 (%)",
                0, 50,
                params.get("target_profit_pct", 10),
                1
            )
        with col2:
            params["stop_loss_pct"] = st.slider(
                "손절률 (%)",
                -50, 0,
                params.get("stop_loss_pct", -5),
                1
            )

    return params


def _fixed_target_exit_config_ui(params: Dict) -> Dict:
    """고정 목표가 매도 전략 설정 UI"""
    st.write("**목표 수익/손절 설정**")

    col1, col2 = st.columns(2)
    with col1:
        params["target_profit_pct"] = st.slider(
            "목표 수익률 (%)",
            1, 100,
            params.get("target_profit_pct", 10),
            1,
            help="매수가 대비 이 비율 상승 시 매도"
        )
    with col2:
        params["stop_loss_pct"] = st.slider(
            "손절률 (%)",
            -50, -1,
            params.get("stop_loss_pct", -5),
            1,
            help="매수가 대비 이 비율 하락 시 매도"
        )

    st.markdown("---")
    st.write("**단계별 익절 (선택)**")

    params["use_ladder"] = st.checkbox(
        "단계별 익절 사용",
        params.get("use_ladder", False),
        help="여러 단계로 나눠 분할 매도"
    )

    if params.get("use_ladder"):
        params["ladder_levels"] = st.number_input(
            "익절 단계 수",
            2, 5,
            params.get("ladder_levels", 3),
            1
        )
        st.info(f"{params['ladder_levels']}단계로 나눠 분할 매도합니다.")

    return params


def _trailing_stop_exit_config_ui(params: Dict) -> Dict:
    """트레일링 스탑 매도 전략 설정 UI"""
    st.write("**트레일링 스탑 설정**")

    params["trailing_pct"] = st.slider(
        "트레일링 비율 (%)",
        1, 20,
        params.get("trailing_pct", 3),
        1,
        help="최고가 대비 이 비율만큼 하락 시 매도"
    )

    st.markdown("---")
    st.write("**활성화 조건**")

    params["activation_profit_pct"] = st.slider(
        "활성화 수익률 (%)",
        0, 50,
        params.get("activation_profit_pct", 5),
        1,
        help="이 수익률 이상일 때부터 트레일링 스탑 활성화"
    )

    st.info(f"수익률이 {params['activation_profit_pct']}% 이상일 때 트레일링 스탑이 작동합니다.")

    return params


def _hybrid_exit_config_ui(params: Dict) -> Dict:
    """하이브리드 매도 전략 설정 UI"""
    st.write("**전략 가중치 설정** (합계 1.0)")

    col1, col2, col3 = st.columns(3)
    with col1:
        target_w = st.slider("목표가", 0.0, 1.0, 0.4, 0.05, key="exit_hybrid_target_w")
    with col2:
        trail_w = st.slider("트레일링", 0.0, 1.0, 0.3, 0.05, key="exit_hybrid_trail_w")
    with col3:
        time_w = st.slider("시간 기반", 0.0, 1.0, 0.3, 0.05, key="exit_hybrid_time_w")

    total = target_w + trail_w + time_w
    if abs(total - 1.0) > 0.01:
        st.warning(f"전략 가중치 합계: {total:.2f}")
    else:
        st.success(f"전략 가중치 합계: {total:.2f}")

    params["strategy_weights"] = {
        "fixed_target": target_w,
        "trailing_stop": trail_w,
        "time_based": time_w
    }

    st.markdown("---")
    params["min_confidence"] = st.slider(
        "최소 신뢰도",
        0.0, 1.0,
        params.get("min_confidence", 0.6),
        0.05
    )

    return params
