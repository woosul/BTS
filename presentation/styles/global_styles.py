"""
전역 스타일 정의

모든 페이지에서 공통으로 사용하는 CSS 스타일
"""
import streamlit as st


def apply_global_styles():
    """
    전역 CSS 스타일 적용
    
    모든 페이지의 시작 부분에서 호출하여 일관된 스타일 적용
    """
    st.markdown("""
    <style>
    /* ==================== 폰트 로드 ==================== */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    /* ==================== 전체 폰트 적용 ==================== */
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif !important;
    }

    p, h1, h2, h3, h4, h5, h6, label, input, textarea, select, button,
    [data-testid] div, [data-testid] span, [data-testid] p,
    .stMarkdown, .stText, .stCaption {
        font-family: 'Noto Sans KR', sans-serif !important;
    }

    /* Material Icons 요소는 원래 폰트 유지 */
    .material-symbols-outlined,
    [class*="material-icons"],
    span[data-testid*="stIcon"],
    button span,
    [role="button"] span {
        font-family: 'Material Symbols Outlined', 'Material Icons' !important;
    }

    /* ==================== 사이드바 네비게이션 ==================== */
    [data-testid="stSidebarNav"] {
        padding-top: 0 !important;
    }
    [data-testid="stSidebarNav"] > div:first-child {
        padding: 1.5rem 1rem !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }
    [data-testid="stSidebarNav"] a {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }
    [data-testid="stSidebarNav"] img {
        width: 90% !important;
        max-width: 280px !important;
        height: auto !important;
    }
    [data-testid="stSidebarNav"] ul {
        margin-top: 1rem !important;
    }
    [data-testid="stSidebarNav"] ul li a {
        text-align: left !important;
        justify-content: flex-start !important;
        background-color: var(--primary-color) !important;
        border-radius: 4px !important;
        margin-bottom: 4px !important;
    }

    /* ==================== 타이틀 크기 조정 ==================== */
    h1 {
        font-size: 1.8rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    h2 {
        font-size: 1.3rem !important;
        margin-top: 0.8rem !important;
        margin-bottom: 0.5rem !important;
    }
    h3 {
        font-size: 1.1rem !important;
        margin-top: 0.6rem !important;
        margin-bottom: 0.4rem !important;
    }

    /* ==================== 레이아웃 여백 ==================== */
    hr {
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }

    /* ==================== 폼 요소 스타일 ==================== */
    /* 셀렉트박스 */
    [data-baseweb="select"] > div {
        font-size: 0.875em !important;
    }
    [data-baseweb="select"] input {
        font-size: 0.875em !important;
    }
    [data-baseweb="select"] div[role="button"] {
        border-radius: 4px !important;
    }

    /* 멀티셀렉트 태그 */
    [data-baseweb="tag"] {
        font-size: 0.875rem !important;
        font-family: "Noto Sans KR", sans-serif !important;
    }
    [data-baseweb="tag"] span {
        font-size: 0.875rem !important;
        font-family: "Noto Sans KR", sans-serif !important;
    }

    /* ==================== 버튼 스타일 ==================== */
    button[data-testid^="stBaseButton"] {
        font-size: 0.875rem !important;
    }
    button[data-testid^="stBaseButton"] p {
        font-size: 0.875rem !important;
    }
    .stButton button {
        font-size: 0.875rem !important;
    }
    .stDownloadButton button {
        font-size: 0.875rem !important;
    }

    /* ==================== 기타 UI 요소 ==================== */
    /* 상단 더보기 메뉴 */
    [data-testid="stAppViewBlockContainer"] button[kind="header"] {
        font-size: 0.875rem !important;
    }
    div[data-baseweb="popover"] ul li {
        font-size: 0.875rem !important;
    }
    div[data-baseweb="popover"] button {
        font-size: 0.875rem !important;
    }

    /* 사이드바 expander */
    [data-testid="stSidebar"] [data-testid="stExpander"] p,
    [data-testid="stSidebar"] [data-testid="stExpander"] div {
        font-size: 0.875rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
