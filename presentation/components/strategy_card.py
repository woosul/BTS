"""
전략 설정 카드 컴포넌트
"""
import streamlit as st
from typing import Dict, Optional


def render_strategy_card(
    strategy_name: str,
    strategy_type: str,
    strategy_params: Optional[Dict] = None,
    card_key: str = "",
    show_button: bool = True,
    is_hybrid_sub: bool = False
) -> bool:
    """
    전략 설정 카드 렌더링

    Args:
        strategy_name: 전략 이름 (모멘텀, 거래량, 기술지표, 하이브리드)
        strategy_type: 전략 타입 (momentum, volume, technical, hybrid)
        strategy_params: 전략 파라미터 (설정된 경우)
        card_key: 카드 고유 키
        show_button: 설정 버튼 표시 여부
        is_hybrid_sub: 하이브리드의 하위 전략 카드인지 여부

    Returns:
        bool: 설정 버튼 클릭 여부
    """
    # 전략 설명
    strategy_descriptions = {
        "momentum": "가격/거래량/RSI 모멘텀 분석",
        "volume": "거래대금 및 거래량 급증 분석",
        "technical": "RSI, MACD, 이동평균 복합 분석",
        "hybrid": "복수 전략 가중치 조합"
    }

    description = strategy_descriptions.get(strategy_type, "")

    # 파라미터 요약
    if strategy_params:
        params_summary = _summarize_params(strategy_type, strategy_params)
        # 설정 완료 시 설명 숨김
        show_description = False
    else:
        params_summary = "설정 없음"
        # 미설정 시 설명 표시
        show_description = True

    # 하이브리드 하위 카드의 경우 설명 숨김
    if is_hybrid_sub:
        show_description = False

    # 여백 설정
    header_margin = '0.4rem' if not show_description else '0.8rem'

    # 조건부 HTML 생성 (직접 문자열 연결)
    if show_description:
        description_html = '<div class="strategy-desc">' + description + '</div>'
    else:
        description_html = ''

    # 전체 HTML 조립 (직접 문자열 연결로 이스케이프 방지)
    full_html = (
        '<style>'
        '.strategy-card {'
        'background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);'
        'border: 1px solid #404040;'
        'border-radius: 12px;'
        'padding: 1.2rem;'
        'margin-bottom: 1rem;'
        'transition: all 0.3s ease;'
        '}'
        '.strategy-card:hover {'
        'border-color: #00b4d8;'
        'transform: translateY(-2px);'
        'box-shadow: 0 4px 12px rgba(0, 180, 216, 0.2);'
        '}'
        '.strategy-header {'
        'display: flex;'
        'align-items: center;'
        'gap: 0.8rem;'
        'margin-bottom: ' + header_margin + ';'
        '}'
        '.strategy-title {'
        'font-size: 1.1rem;'
        'font-weight: 600;'
        'color: #ffffff;'
        '}'
        '.strategy-desc {'
        'font-size: 0.85rem;'
        'color: #b0b0b0;'
        'margin-bottom: 1rem;'
        '}'
        '.strategy-params {'
        'font-size: 0.8rem;'
        'color: #90caf9;'
        'background: rgba(144, 202, 249, 0.1);'
        'padding: 0.6rem;'
        'border-radius: 6px;'
        'display: flex;'
        'flex-wrap: wrap;'
        'gap: 12px;'
        '}'
        '.param-item {'
        'flex: 1 1 auto;'
        'min-width: 120px;'
        '}'
        '</style>'
        '<div class="strategy-card">'
        '<div class="strategy-header">'
        '<span class="strategy-title">' + strategy_name + '</span>'
        '</div>'
        + description_html +
        '<div class="strategy-params">'
        + params_summary +
        '</div>'
        '</div>'
    )

    st.markdown(full_html, unsafe_allow_html=True)

    # 설정 버튼
    button_clicked = False
    if show_button:
        button_clicked = st.button(
            f"{strategy_name} 설정",
            key=f"config_btn_{card_key}",
            use_container_width=True,
            type="primary" if not strategy_params else "secondary"
        )

    return button_clicked


def _summarize_params(strategy_type: str, params: Dict) -> str:
    """파라미터 요약 - Caption + Value 형태로 (반응형 그리드)"""
    summary_html = ""

    if strategy_type == "momentum":
        # 가중치 정보
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>가격 가중치</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('price_weight', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>거래량 가중치</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('volume_weight', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>RSI 가중치</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('rsi_weight', 0) * 100)) + "%</div></div>"
        # 기간 정보
        periods = []
        if params.get("period_1d"): periods.append("1일")
        if params.get("period_7d"): periods.append("7일")
        if params.get("period_30d"): periods.append("30일")
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>분석 기간</div><div style='font-size: 0.85rem; color: #ffffff;'>" + (', '.join(periods) if periods else '없음') + "</div></div>"

    elif strategy_type == "volume":
        # 가중치 정보
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>거래대금 가중치</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('amount_weight', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>급증 가중치</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('surge_weight', 0) * 100)) + "%</div></div>"
        # 임계값 정보
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>거래량 배수</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(round(params.get('threshold', 0), 1)) + "x</div></div>"
        # 기간 정보
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>평균 계산 기간</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('period', 20)) + "일</div></div>"

    elif strategy_type == "technical":
        # 가중치 정보
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>RSI 가중치</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('rsi_weight', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>MACD 가중치</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('macd_weight', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>MA 가중치</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('ma_weight', 0) * 100)) + "%</div></div>"
        # 사용 지표
        indicators = []
        if params.get("use_rsi"): indicators.append("RSI(" + str(params.get('rsi_period', 14)) + ")")
        if params.get("use_macd"):
            indicators.append("MACD(" + str(params.get('macd_fast', 12)) + "," + str(params.get('macd_slow', 26)) + "," + str(params.get('macd_signal', 9)) + ")")
        if params.get("use_ma"):
            indicators.append("MA(" + str(params.get('ma_short', 20)) + "/" + str(params.get('ma_long', 60)) + ")")

        summary_html += "<div class='param-item' style='flex: 1 1 100%;'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>사용 지표</div><div style='font-size: 0.85rem; color: #ffffff;'>" + (', '.join(indicators) if indicators else '없음') + "</div></div>"

    elif strategy_type == "hybrid":
        # 전략 가중치
        weights = params.get("strategy_weights", {})
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>모멘텀</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('momentum', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>거래량</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('volume', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>기술지표</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('technical', 0) * 100)) + "%</div></div>"
        # 최소 점수
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>최소 점수</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('min_score', 0.5) * 100)) + "%</div></div>"

    # Entry strategies
    elif strategy_type == "macd_entry":
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Fast Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('fast_period', 12)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Slow Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('slow_period', 26)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Signal Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('signal_period', 9)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>최소 신뢰도</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('min_confidence', 0.6) * 100)) + "%</div></div>"

    elif strategy_type == "stochastic_entry":
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>%K Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('k_period', 14)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>%D Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('d_period', 3)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Smooth</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('smooth', 3)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>과매도 기준</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('oversold_level', 20)) + "</div></div>"

    elif strategy_type == "multi_indicator_entry":
        indicators = []
        if params.get("use_rsi"): indicators.append("RSI")
        if params.get("use_macd"): indicators.append("MACD")
        if params.get("use_bb"): indicators.append("BB")
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>사용 지표</div><div style='font-size: 0.85rem; color: #ffffff;'>" + (', '.join(indicators) if indicators else '없음') + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>조합 방식</div><div style='font-size: 0.85rem; color: #ffffff;'>" + params.get('combination_mode', 'AND') + "</div></div>"

    elif strategy_type == "hybrid_entry":
        weights = params.get("strategy_weights", {})
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>MACD</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('macd', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Stochastic</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('stochastic', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>RSI</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('rsi', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>최소 신뢰도</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('min_confidence', 0.6) * 100)) + "%</div></div>"

    # Exit strategies
    elif strategy_type == "macd_exit":
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Fast Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('fast_period', 12)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Slow Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('slow_period', 26)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Signal Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('signal_period', 9)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>최소 신뢰도</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('min_confidence', 0.6) * 100)) + "%</div></div>"

    elif strategy_type == "stochastic_exit":
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>%K Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('k_period', 14)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>%D Period</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('d_period', 3)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>Smooth</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('smooth', 3)) + "</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>과매수 기준</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('overbought_level', 80)) + "</div></div>"

    elif strategy_type == "time_based_exit":
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>보유 시간</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('holding_hours', 24)) + "시간</div></div>"
        if params.get('allow_early_exit'):
            summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>목표 수익률</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('target_profit_pct', 10)) + "%</div></div>"
            summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>손절률</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('stop_loss_pct', -5)) + "%</div></div>"

    elif strategy_type == "fixed_target_exit":
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>목표 수익률</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('target_profit_pct', 10)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>손절률</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('stop_loss_pct', -5)) + "%</div></div>"
        if params.get('use_ladder'):
            summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>익절 단계</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('ladder_levels', 3)) + "단계</div></div>"

    elif strategy_type == "trailing_stop_exit":
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>트레일링 비율</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('trailing_pct', 3)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>활성화 수익률</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(params.get('activation_profit_pct', 5)) + "%</div></div>"

    elif strategy_type == "hybrid_exit":
        weights = params.get("strategy_weights", {})
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>목표가</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('fixed_target', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>트레일링</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('trailing_stop', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>시간 기반</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(weights.get('time_based', 0) * 100)) + "%</div></div>"
        summary_html += "<div class='param-item'><div style='font-size: 0.7rem; color: #9ca3af; margin-bottom: 2px;'>최소 신뢰도</div><div style='font-size: 0.85rem; color: #ffffff;'>" + str(int(params.get('min_confidence', 0.6) * 100)) + "%</div></div>"

    return summary_html if summary_html else "설정 정보 없음"
