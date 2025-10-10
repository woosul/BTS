"""
전략 설정 팝업 모달
"""
import streamlit as st
from typing import Dict, Optional
from presentation.components.modal_utils import apply_modal_styles


@st.dialog("전략 설정", width="large")
def show_strategy_config_modal(
    strategy_name: str,
    strategy_type: str,
    current_params: Optional[Dict] = None
) -> Optional[Dict]:
    """
    전략 설정 팝업 모달

    Args:
        strategy_name: 전략 이름
        strategy_type: 전략 타입 (momentum, volume, technical, hybrid)
        current_params: 현재 설정된 파라미터

    Returns:
        Optional[Dict]: 설정된 파라미터 (취소 시 None)
    """
    # 모달창 공통 스타일 적용
    apply_modal_styles()
    
    st.markdown(f"### {strategy_name} 전략 설정")

    params = current_params.copy() if current_params else {}

    # 전략 타입별 설정 UI
    if strategy_type == "momentum":
        params = _momentum_config_ui(params)
    elif strategy_type == "volume":
        params = _volume_config_ui(params)
    elif strategy_type == "technical":
        params = _technical_config_ui(params)
    elif strategy_type == "hybrid":
        params = _hybrid_config_ui(params)

    # 하단 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("적용", type="primary", use_container_width=True):
            # 전략별 검증 수행 (검증 실패 시 위의 메시지 블록에서 이미 표시됨)
            validation_error = _validate_strategy_params(strategy_type, params)
            
            if not validation_error:
                st.session_state[f"strategy_params_{strategy_type}"] = params
                st.rerun()
    with col2:
        if st.button("취소", use_container_width=True):
            st.rerun()

    return None


def _momentum_config_ui(params: Dict) -> Dict:
    """모멘텀 전략 설정 UI"""
    st.markdown("##### 가중치 설정 (합계 1.0)")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["price_weight"] = st.slider(
            "가격 상승률",
            0.0, 1.0,
            params.get("price_weight", 0.4),
            0.05,
            help="가격 변동률 가중치"
        )
    with col2:
        params["volume_weight"] = st.slider(
            "거래량 증가율",
            0.0, 1.0,
            params.get("volume_weight", 0.3),
            0.05,
            help="거래량 변동률 가중치"
        )
    with col3:
        params["rsi_weight"] = st.slider(
            "RSI 모멘텀",
            0.0, 1.0,
            params.get("rsi_weight", 0.3),
            0.05,
            help="RSI 모멘텀 가중치"
        )

    total = params["price_weight"] + params["volume_weight"] + params["rsi_weight"]
    is_valid = abs(total - 1.0) <= 0.01
    
    if not is_valid:
        # 에러 상태: 빨간 테두리와 텍스트
        st.markdown(f"""
            <div style='
                background-color: #262730;
                border: 1px solid #ff4444;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 8px 0;
            '>
                <div style='color: #ff4444; font-size: 0.875rem;'>
                    가중치 합계: {total:.2f} (1.0이어야 함)
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # 정상 상태: 테두리 없이 회색 텍스트만
        st.markdown(f"""
            <div style='
                background-color: #262730;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 8px 0;
            '>
                <div style='color: #6b7280; font-size: 0.875rem;'>
                    가중치 합계: {total:.2f}
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### 기간 설정")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["period_1d"] = st.checkbox("1일 모멘텀", params.get("period_1d", True))
    with col2:
        params["period_7d"] = st.checkbox("7일 모멘텀", params.get("period_7d", True))
    with col3:
        params["period_30d"] = st.checkbox("30일 모멘텀", params.get("period_30d", True))

    if not any([params.get("period_1d"), params.get("period_7d"), params.get("period_30d")]):
        st.error("최소 1개 기간을 선택해야 합니다.")
    
    st.markdown("---")
    st.markdown("##### 기간별 가중치 (활성화된 기간의 합계 1.0)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if params.get("period_1d", True):
            params["period_1d_weight"] = st.slider(
                "1일 가중치",
                0.0, 1.0,
                params.get("period_1d_weight", 0.5),
                0.05,
                help="단기 모멘텀의 중요도"
            )
        else:
            params["period_1d_weight"] = 0.0
            st.slider(
                "1일 가중치",
                0.0, 1.0,
                0.0,
                0.05,
                help="비활성화됨 (체크박스를 활성화하세요)",
                disabled=True
            )
    
    with col2:
        if params.get("period_7d", True):
            params["period_7d_weight"] = st.slider(
                "7일 가중치",
                0.0, 1.0,
                params.get("period_7d_weight", 0.3),
                0.05,
                help="중기 모멘텀의 중요도"
            )
        else:
            params["period_7d_weight"] = 0.0
            st.slider(
                "7일 가중치",
                0.0, 1.0,
                0.0,
                0.05,
                help="비활성화됨 (체크박스를 활성화하세요)",
                disabled=True
            )
    
    with col3:
        if params.get("period_30d", True):
            params["period_30d_weight"] = st.slider(
                "30일 가중치",
                0.0, 1.0,
                params.get("period_30d_weight", 0.2),
                0.05,
                help="장기 모멘텀의 중요도"
            )
        else:
            params["period_30d_weight"] = 0.0
            st.slider(
                "30일 가중치",
                0.0, 1.0,
                0.0,
                0.05,
                help="비활성화됨 (체크박스를 활성화하세요)",
                disabled=True
            )
    
    # 활성화된 기간의 가중치만 합계 확인
    active_period_total = params["period_1d_weight"] + params["period_7d_weight"] + params["period_30d_weight"]
    
    if active_period_total > 0:
        is_valid = abs(active_period_total - 1.0) <= 0.01
        
        if not is_valid:
            # 에러 상태: 빨간 테두리와 텍스트
            st.markdown(f"""
                <div style='
                    background-color: #262730;
                    border: 1px solid #ff4444;
                    border-radius: 4px;
                    padding: 8px 12px;
                    margin: 8px 0;
                '>
                    <div style='color: #ff4444; font-size: 0.875rem;'>
                        기간별 가중치 합계: {active_period_total:.2f} (1.0이어야 함)
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            # 정상 상태: 테두리 없이 회색 텍스트만
            st.markdown(f"""
                <div style='
                    background-color: #262730;
                    border-radius: 4px;
                    padding: 8px 12px;
                    margin: 8px 0;
                '>
                    <div style='color: #6b7280; font-size: 0.875rem;'>
                        기간별 가중치 합계: {active_period_total:.2f}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    return params


def _volume_config_ui(params: Dict) -> Dict:
    """거래량 전략 설정 UI"""
    st.markdown("##### 가중치 설정 (합계 1.0)")

    col1, col2 = st.columns(2)
    with col1:
        params["amount_weight"] = st.slider(
            "거래대금",
            0.0, 1.0,
            params.get("amount_weight", 0.5),
            0.05
        )
    with col2:
        params["surge_weight"] = st.slider(
            "거래량 급증",
            0.0, 1.0,
            params.get("surge_weight", 0.5),
            0.05
        )

    total = params["amount_weight"] + params["surge_weight"]
    is_valid = abs(total - 1.0) <= 0.01
    
    if not is_valid:
        # 에러 상태: 빨간 테두리와 텍스트
        st.markdown(f"""
            <div style='
                background-color: #262730;
                border: 1px solid #ff4444;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 8px 0;
            '>
                <div style='color: #ff4444; font-size: 0.875rem;'>
                    가중치 합계: {total:.2f} (1.0이어야 함)
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # 정상 상태: 테두리 없이 회색 텍스트만
        st.markdown(f"""
            <div style='
                background-color: #262730;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 8px 0;
            '>
                <div style='color: #6b7280; font-size: 0.875rem;'>
                    가중치 합계: {total:.2f}
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### 임계값 설정")

    col1, col2 = st.columns(2)
    with col1:
        params["threshold"] = st.slider(
            "거래량 배수",
            1.0, 5.0,
            params.get("threshold", 1.5),
            0.1
        )
    with col2:
        params["period"] = st.number_input(
            "평균 계산 기간 (일)",
            5, 100,
            params.get("period", 20),
            5
        )

    return params


def _technical_config_ui(params: Dict) -> Dict:
    """기술지표 전략 설정 UI"""
    st.markdown("##### 가중치 설정 (합계 1.0)")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["rsi_weight"] = st.slider(
            "RSI",
            0.0, 1.0,
            params.get("rsi_weight", 0.3),
            0.05
        )
    with col2:
        params["macd_weight"] = st.slider(
            "MACD",
            0.0, 1.0,
            params.get("macd_weight", 0.4),
            0.05
        )
    with col3:
        params["ma_weight"] = st.slider(
            "이동평균",
            0.0, 1.0,
            params.get("ma_weight", 0.3),
            0.05
        )

    total = params["rsi_weight"] + params["macd_weight"] + params["ma_weight"]
    is_valid = abs(total - 1.0) <= 0.01
    
    if not is_valid:
        # 에러 상태: 빨간 테두리와 텍스트
        st.markdown(f"""
            <div style='
                background-color: #262730;
                border: 1px solid #ff4444;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 8px 0;
            '>
                <div style='color: #ff4444; font-size: 0.875rem;'>
                    가중치 합계: {total:.2f} (1.0이어야 함)
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # 정상 상태: 테두리 없이 회색 텍스트만
        st.markdown(f"""
            <div style='
                background-color: #262730;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 8px 0;
            '>
                <div style='color: #6b7280; font-size: 0.875rem;'>
                    가중치 합계: {total:.2f}
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### 지표 사용 설정")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["use_rsi"] = st.checkbox("RSI 사용", params.get("use_rsi", True))
    with col2:
        params["use_macd"] = st.checkbox("MACD 사용", params.get("use_macd", True))
    with col3:
        params["use_ma"] = st.checkbox("MA 사용", params.get("use_ma", True))

    if not any([params.get("use_rsi"), params.get("use_macd"), params.get("use_ma")]):
        st.error("최소 1개 지표를 선택해야 합니다.")

    st.markdown("---")
    st.markdown("##### 상세 파라미터")

    tab_rsi, tab_macd, tab_ma = st.tabs(["RSI", "MACD", "이동평균"])

    with tab_rsi:
        params["rsi_period"] = st.number_input(
            "RSI 기간",
            5, 50,
            params.get("rsi_period", 14),
            1,
            help="일반적으로 14 사용"
        )

    with tab_macd:
        col1, col2, col3 = st.columns(3)
        with col1:
            params["macd_fast"] = st.number_input(
                "단기 EMA",
                5, 30,
                params.get("macd_fast", 12),
                1
            )
        with col2:
            params["macd_slow"] = st.number_input(
                "장기 EMA",
                15, 60,
                params.get("macd_slow", 26),
                1
            )
        with col3:
            params["macd_signal"] = st.number_input(
                "시그널",
                5, 20,
                params.get("macd_signal", 9),
                1
            )

    with tab_ma:
        col1, col2 = st.columns(2)
        with col1:
            params["ma_short"] = st.number_input(
                "단기 MA",
                5, 50,
                params.get("ma_short", 20),
                1
            )
        with col2:
            params["ma_long"] = st.number_input(
                "장기 MA",
                20, 120,
                params.get("ma_long", 60),
                1
            )

    return params


def _hybrid_config_ui(params: Dict) -> Dict:
    """하이브리드 전략 설정 UI"""
    st.markdown("##### 1단계: 전략 가중치 설정 (합계 1.0)")

    col1, col2, col3 = st.columns(3)
    with col1:
        momentum_w = st.slider("모멘텀", 0.0, 1.0, 0.40, 0.05, key="modal_hybrid_momentum_w")
    with col2:
        volume_w = st.slider("거래량", 0.0, 1.0, 0.30, 0.05, key="modal_hybrid_volume_w")
    with col3:
        technical_w = st.slider("기술지표", 0.0, 1.0, 0.30, 0.05, key="modal_hybrid_technical_w")

    total = momentum_w + volume_w + technical_w
    is_valid = abs(total - 1.0) <= 0.01
    
    if not is_valid:
        # 에러 상태: 빨간 테두리와 텍스트
        st.markdown(f"""
            <div style='
                background-color: #262730;
                border: 1px solid #ff4444;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 8px 0;
            '>
                <div style='color: #ff4444; font-size: 0.875rem;'>
                    전략 가중치 합계: {total:.2f} (1.0이어야 함)
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # 정상 상태: 테두리 없이 회색 텍스트만
        st.markdown(f"""
            <div style='
                background-color: #262730;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 8px 0;
            '>
                <div style='color: #6b7280; font-size: 0.875rem;'>
                    전략 가중치 합계: {total:.2f}
                </div>
            </div>
        """, unsafe_allow_html=True)

    params["strategy_weights"] = {
        "momentum": momentum_w,
        "volume": volume_w,
        "technical": technical_w
    }

    st.markdown("---")
    st.markdown("##### 2단계: 세부 전략 설정")

    tab_m, tab_v, tab_t = st.tabs([
        f"모멘텀 ({momentum_w:.0%})",
        f"거래량 ({volume_w:.0%})",
        f"기술지표 ({technical_w:.0%})"
    ])

    with tab_m:
        # 모멘텀 가중치
        st.markdown("##### 가중치")
        col1, col2, col3 = st.columns(3)
        with col1:
            params["momentum_price_weight"] = st.slider("가격", 0.0, 1.0, 0.4, 0.05, key="modal_mom_price")
        with col2:
            params["momentum_volume_weight"] = st.slider("거래량", 0.0, 1.0, 0.3, 0.05, key="modal_mom_vol")
        with col3:
            params["momentum_rsi_weight"] = st.slider("RSI", 0.0, 1.0, 0.3, 0.05, key="modal_mom_rsi")

        # 기간
        st.markdown("##### 기간")
        col1, col2, col3 = st.columns(3)
        with col1:
            params["momentum_period_1d"] = st.checkbox("1일", True, key="modal_mom_1d")
        with col2:
            params["momentum_period_7d"] = st.checkbox("7일", True, key="modal_mom_7d")
        with col3:
            params["momentum_period_30d"] = st.checkbox("30일", True, key="modal_mom_30d")
        
        # 기간별 가중치
        st.markdown("##### 기간별 가중치 (활성화된 기간의 합계 1.0)")
        col1, col2, col3 = st.columns(3)
        with col1:
            if params.get("momentum_period_1d", True):
                params["momentum_period_1d_weight"] = st.slider(
                    "1일", 0.0, 1.0, 0.5, 0.05, 
                    key="modal_mom_1d_w"
                )
            else:
                params["momentum_period_1d_weight"] = 0.0
                st.slider(
                    "1일", 0.0, 1.0, 0.0, 0.05, 
                    key="modal_mom_1d_w",
                    disabled=True
                )
        
        with col2:
            if params.get("momentum_period_7d", True):
                params["momentum_period_7d_weight"] = st.slider(
                    "7일", 0.0, 1.0, 0.3, 0.05, 
                    key="modal_mom_7d_w"
                )
            else:
                params["momentum_period_7d_weight"] = 0.0
                st.slider(
                    "7일", 0.0, 1.0, 0.0, 0.05, 
                    key="modal_mom_7d_w",
                    disabled=True
                )
        
        with col3:
            if params.get("momentum_period_30d", True):
                params["momentum_period_30d_weight"] = st.slider(
                    "30일", 0.0, 1.0, 0.2, 0.05, 
                    key="modal_mom_30d_w"
                )
            else:
                params["momentum_period_30d_weight"] = 0.0
                st.slider(
                    "30일", 0.0, 1.0, 0.0, 0.05, 
                    key="modal_mom_30d_w",
                    disabled=True
                )
        
        # 가중치 합계 검증
        momentum_period_total = (
            params["momentum_period_1d_weight"] + 
            params["momentum_period_7d_weight"] + 
            params["momentum_period_30d_weight"]
        )
        if momentum_period_total > 0:
            is_valid = abs(momentum_period_total - 1.0) <= 0.01
            
            if not is_valid:
                # 에러 상태: 빨간 테두리와 텍스트
                st.markdown(f"""
                    <div style='
                        background-color: #262730;
                        border: 1px solid #ff4444;
                        border-radius: 4px;
                        padding: 8px 12px;
                        margin: 8px 0;
                    '>
                        <div style='color: #ff4444; font-size: 0.875rem;'>
                            기간별 가중치 합계: {momentum_period_total:.2f} (1.0이어야 함)
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                # 정상 상태: 테두리 없이 회색 텍스트만
                st.markdown(f"""
                    <div style='
                        background-color: #262730;
                        border-radius: 4px;
                        padding: 8px 12px;
                        margin: 8px 0;
                    '>
                        <div style='color: #6b7280; font-size: 0.875rem;'>
                            기간별 가중치 합계: {momentum_period_total:.2f}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    with tab_v:
        # 거래량 가중치
        st.markdown("##### 가중치")
        col1, col2 = st.columns(2)
        with col1:
            params["volume_amount_weight"] = st.slider("거래대금", 0.0, 1.0, 0.5, 0.05, key="modal_vol_amt")
        with col2:
            params["volume_surge_weight"] = st.slider("급증", 0.0, 1.0, 0.5, 0.05, key="modal_vol_surge")

        st.markdown("##### 임계값")
        col1, col2 = st.columns(2)
        with col1:
            params["volume_threshold"] = st.slider("배수", 1.0, 5.0, 1.5, 0.1, key="modal_vol_thresh")
        with col2:
            params["volume_period"] = st.number_input("기간", 5, 100, 20, 5, key="modal_vol_period")

    with tab_t:
        # 기술지표 가중치
        st.markdown("##### 가중치")
        col1, col2, col3 = st.columns(3)
        with col1:
            params["technical_rsi_weight"] = st.slider("RSI", 0.0, 1.0, 0.3, 0.05, key="modal_tech_rsi_w")
        with col2:
            params["technical_macd_weight"] = st.slider("MACD", 0.0, 1.0, 0.4, 0.05, key="modal_tech_macd_w")
        with col3:
            params["technical_ma_weight"] = st.slider("MA", 0.0, 1.0, 0.3, 0.05, key="modal_tech_ma_w")

        st.markdown("##### 사용 여부")
        col1, col2, col3 = st.columns(3)
        with col1:
            params["technical_rsi"] = st.checkbox("RSI", True, key="modal_tech_rsi")
        with col2:
            params["technical_macd"] = st.checkbox("MACD", True, key="modal_tech_macd")
        with col3:
            params["technical_ma"] = st.checkbox("MA", True, key="modal_tech_ma")

        st.markdown("##### 상세 설정")
        with st.expander("RSI 설정"):
            params["technical_rsi_period"] = st.number_input("기간", 5, 50, 14, 1, key="modal_tech_rsi_period")
        with st.expander("MACD 설정"):
            col1, col2, col3 = st.columns(3)
            with col1:
                params["technical_macd_fast"] = st.number_input("Fast", 5, 30, 12, 1, key="modal_tech_macd_fast")
            with col2:
                params["technical_macd_slow"] = st.number_input("Slow", 15, 60, 26, 1, key="modal_tech_macd_slow")
            with col3:
                params["technical_macd_signal"] = st.number_input("Signal", 5, 20, 9, 1, key="modal_tech_macd_sig")
        with st.expander("이동평균 설정"):
            col1, col2 = st.columns(2)
            with col1:
                params["technical_ma_short"] = st.number_input("단기", 5, 50, 20, 1, key="modal_tech_ma_short")
            with col2:
                params["technical_ma_long"] = st.number_input("장기", 20, 120, 60, 1, key="modal_tech_ma_long")

    # 최소 점수
    st.markdown("---")
    params["min_score"] = st.slider(
        "최소 점수",
        0.0, 1.0,
        params.get("min_score", 0.5),
        0.05,
        key="modal_hybrid_min_score",
        help="이 점수 이상인 종목만 선정"
    )

    return params


def _validate_strategy_params(strategy_type: str, params: Dict) -> Optional[str]:
    """
    전략 파라미터 검증
    
    Args:
        strategy_type: 전략 타입
        params: 검증할 파라미터
    
    Returns:
        Optional[str]: 오류 메시지 (검증 성공 시 None)
    """
    if strategy_type == "momentum":
        # 가중치 합계 검증
        total = params.get("price_weight", 0) + params.get("volume_weight", 0) + params.get("rsi_weight", 0)
        if abs(total - 1.0) > 0.01:
            return f"가중치 합계가 1.0이 아닙니다: {total:.2f}"
        
        # 기간별 가중치 검증
        period_total = (
            params.get("period_1d_weight", 0) + 
            params.get("period_7d_weight", 0) + 
            params.get("period_30d_weight", 0)
        )
        if abs(period_total - 1.0) > 0.01:
            return f"기간별 가중치 합계가 1.0이 아닙니다: {period_total:.2f}\n\n활성화된 기간의 가중치 합계를 1.0으로 맞춰주세요."
        
        # 최소 1개 기간 활성화 확인
        if not any([params.get("period_1d"), params.get("period_7d"), params.get("period_30d")]):
            return "최소 1개 기간을 선택해야 합니다."
    
    elif strategy_type == "volume":
        # 가중치 합계 검증
        total = params.get("amount_weight", 0) + params.get("surge_weight", 0)
        if abs(total - 1.0) > 0.01:
            return f"가중치 합계가 1.0이 아닙니다: {total:.2f}"
    
    elif strategy_type == "technical":
        # 가중치 합계 검증
        total = params.get("rsi_weight", 0) + params.get("macd_weight", 0) + params.get("ma_weight", 0)
        if abs(total - 1.0) > 0.01:
            return f"가중치 합계가 1.0이 아닙니다: {total:.2f}"
        
        # 최소 1개 지표 활성화 확인
        if not any([params.get("use_rsi"), params.get("use_macd"), params.get("use_ma")]):
            return "최소 1개 지표를 선택해야 합니다."
    
    elif strategy_type == "hybrid":
        # 전략 가중치 합계 검증
        strategy_weights = params.get("strategy_weights", {})
        total = strategy_weights.get("momentum", 0) + strategy_weights.get("volume", 0) + strategy_weights.get("technical", 0)
        if abs(total - 1.0) > 0.01:
            return f"전략 가중치 합계가 1.0이 아닙니다: {total:.2f}"
        
        # 모멘텀 기간별 가중치 검증
        momentum_period_total = (
            params.get("momentum_period_1d_weight", 0) + 
            params.get("momentum_period_7d_weight", 0) + 
            params.get("momentum_period_30d_weight", 0)
        )
        if abs(momentum_period_total - 1.0) > 0.01:
            return f"모멘텀 기간별 가중치 합계가 1.0이 아닙니다: {momentum_period_total:.2f}\n\n활성화된 기간의 가중치 합계를 1.0으로 맞춰주세요."
    
    return None
