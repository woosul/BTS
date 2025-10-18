"""
메트릭 카드 컴포넌트

대시보드용 커스텀 메트릭 카드
"""
import streamlit as st
from typing import Optional


def render_metric_card(
    label: str,
    value: str,
    delta: Optional[float] = None,
    width: int = 200,
    height: int = 60,
    card_id: Optional[str] = None
):
    """
    커스텀 메트릭 카드 렌더링 (반응형)

    Args:
        label: 지수명
        value: 지수값 (문자열)
        delta: 증감율 (백분율, 예: 1.5 = +1.5%)
        width: 카드 기본 너비 (px) - 실제로는 100% 사용
        height: 카드 높이 (px)
        card_id: 카드 고유 ID (WebSocket 업데이트용)
    """
    # 증감 여부에 따른 색상 및 아이콘 결정
    if delta is not None:
        if delta > 0:
            delta_color = "#ef5350"  # 상승: 빨간색
            delta_symbol = "▲"
            delta_text = f"<span style='font-size: 8px;'>{delta_symbol}</span> {abs(delta):.2f}%"
            value_color = "#ef5350"  # 지수값도 상승 색상
        elif delta < 0:
            delta_color = "#42a5f5"  # 하강: 파란색
            delta_symbol = "▼"
            delta_text = f"<span style='font-size: 8px;'>{delta_symbol}</span> {abs(delta):.2f}%"
            value_color = "#42a5f5"  # 지수값도 하강 색상
        else:
            delta_color = "#9e9e9e"  # 변동 없음: 회색
            delta_text = "<span style='font-size: 8px;'>-</span> 0.00%"
            value_color = "white"
    else:
        delta_color = "#9e9e9e"
        delta_text = ""
        value_color = "white"  # delta 없으면 white

    # ID 속성 추가 (있을 경우)
    id_attr = f'id="{card_id}"' if card_id else ''

    # HTML 카드 생성 (반응형, default background : transparent)
    card_html = f"""
    <div {id_attr} style="
        width: 100%;
        min-width: 120px;
        max-width: {width}px;
        height: {height}px;
        background-color: #FFFFFF0C;
        border-radius: 0px;
        padding: 8px clamp(8px, 2vw, 14px) 12px clamp(8px, 2vw, 14px);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
    ">
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            line-height: 1.2;
        ">
            <span style="
                font-size: 14px;
                color: #585a5C;
                font-weight: 400;
            ">{label}</span>
            <span class="metric-delta" style="
                font-size: 13px;
                color: {delta_color};
                font-weight: 400;
                line-height: 1.2;
            ">{delta_text}</span>
        </div>
        <div style="
            display: flex;
            justify-content: flex-end;
            align-items: flex-end;
            margin-top: 2px;
        ">
            <span class="metric-value" style="
                font-size: 20px;
                color: {value_color};
                font-weight: 700;
                line-height: 1;
            ">{value}</span>
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)


def render_metric_card_group(
    title: str,
    metrics: list[dict],
    columns: int = 5,
    attribution: str = None
):
    """
    메트릭 카드 그룹 렌더링

    Args:
        title: 그룹 제목
        metrics: 메트릭 리스트 [{"label": "...", "value": "...", "delta": ..., "card_id": "..."}, ...]
        columns: 열 개수
        attribution: 우측에 표시할 attribution 텍스트 (HTML 지원)
    """
    # 그룹 제목 - deep gray, no bold (default color is #54A0FD)
    if title:
        if attribution:
            # 타이틀과 attribution을 flexbox로 양쪽 정렬
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                    <div style='color: #66686a; font-size: 14px; font-weight: 600;'>{title}</div>
                    <div style='color: #808080; font-size: 11px;'>{attribution}</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #66686a; font-size: 14px; font-weight: 600; margin-bottom: 8px;'>{title}</div>", unsafe_allow_html=True)

    # 카드를 st.columns로 배치 (gap 설정)
    cols = st.columns(columns, gap="small")  # small gap ≈ 12px

    for idx, metric in enumerate(metrics):
        col_idx = idx % columns
        with cols[col_idx]:
            render_metric_card(
                label=metric.get("label", ""),
                value=metric.get("value", "N/A"),
                delta=metric.get("delta", None),
                card_id=metric.get("card_id", None)  # NEW: Pass card_id if available
            )
