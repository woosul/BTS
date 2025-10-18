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
        border-radius: 4px !important;
        margin-bottom: 4px !important;
    }

    /* hover 상태 - Streamlit primaryColor 40% 투명도 사용 */
    [data-testid="stSidebarNav"] ul li a:hover {
        background-color: color-mix(in srgb, var(--primary-color) 40%, transparent) !important;
    }

    /* select 상태 (클릭/포커스) - Streamlit primaryColor 70% 투명도 사용 */
    [data-testid="stSidebarNav"] ul li a:focus,
    [data-testid="stSidebarNav"] ul li a:active {
        background-color: color-mix(in srgb, var(--primary-color) 70%, transparent) !important;
    }

    /* active 상태 (현재 페이지) - Streamlit primaryColor 100% 사용 */
    [data-testid="stSidebarNav"] ul li a[aria-current="page"],
    [data-testid="stSidebarNav"] ul li a[data-selected="true"],
    [data-testid="stSidebarNav"] ul li a.selected,
    [data-testid="stSidebarNav"] ul li.selected a,
    [data-testid="stSidebarNav"] ul li a[aria-selected="true"],
    [data-testid="stSidebarNav"] ul li.active a,
    [data-testid="stSidebarNav"] ul li a.active,
    [data-testid="stSidebarNav"] a[data-active="true"],
    [data-testid="stSidebarNav"] li[aria-selected="true"] a {
        background-color: var(--primary-color) !important;
        font-weight: bold !important;
        color: white !important;
    }

    /* ==================== 타이틀 크기 조정 ==================== */
    h1 {
        font-size: 1.8rem !important;
        margin-top: 0 !important;
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

    /* 토글 위젯 */
    [data-testid="stToggle"] label {
        font-size: 0.875rem !important;
    }
    [data-testid="stToggle"] label p {
        font-size: 0.875rem !important;
    }
    [data-testid="stToggle"] label div {
        font-size: 0.875rem !important;
    }
    [data-testid="stToggle"] label span {
        font-size: 0.875rem !important;
    }
    /* Toggle 내부 텍스트 강제 적용 */
    .stToggle label p,
    .stToggle label div,
    .stToggle label span {
        font-size: 0.875rem !important;
    }
    /* Toggle 컨테이너 내 모든 텍스트 */
    div[data-testid="stToggle"] * {
        font-size: 0.875rem !important;
    }
    /* stWidgetLabel 내부 */
    [data-testid="stWidgetLabel"] p {
        font-size: 0.875rem !important;
    }
    [data-testid="stWidgetLabel"] [data-testid="stMarkdownContainer"] p {
        font-size: 0.875rem !important;
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

    /* ==================== 코드 블록 스타일 ==================== */
    /* 코드 블록 컨테이너 */
    [data-testid="stCode"] {
        font-size: 0.875rem !important;
    }
    [data-testid="stCode"] pre {
        font-size: 0.875rem !important;
    }
    [data-testid="stCode"] code {
        font-size: 0.875rem !important;
    }
    /* 코드 블록 내부 모든 요소 */
    .stCode code,
    .stCode pre,
    code[class*="language-"],
    pre[class*="language-"] {
        font-size: 0.875rem !important;
    }

    /* ==================== 버튼 스타일 ==================== */
    button[data-testid^="stBaseButton"] {
        font-size: 0.875rem !important;
        border-radius: 0 !important;
    }
    button[data-testid^="stBaseButton"] p {
        font-size: 0.875rem !important;
    }
    .stButton button {
        font-size: 0.875rem !important;
        border-radius: 0 !important;
    }
    .stDownloadButton button {
        font-size: 0.875rem !important;
        border-radius: 0 !important;
    }
    
    /* 모든 버튼의 border-radius를 0으로 설정 (number input 제외) */
    button:not([data-testid="stNumberInput"] button) {
        border-radius: 0 !important;
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

    /* ==================== 모달 스타일 (전역 적용) ==================== */
    /* 모달 컨테이너 */
    [data-testid="stModal"] {
        /* 배경 오버레이 스타일 */
        background-color: rgba(0, 0, 0, 0.5) !important;
    }

    /* 모달 다이얼로그 박스 */
    [data-testid="stModal"] > div[role="dialog"] {
        /* 크기 조정 */
        max-width: 800px !important;
        width: 90% !important;
        max-height: 85vh !important;

        /* 위치 조정 - 화면 상단에서 약간 아래로 */
        margin-top: 5vh !important;

        /* 모서리 */
        border-radius: 8px !important;

        /* 그림자 강화 */
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;

        /* 스크롤 */
        overflow-y: auto !important;
    }

    /* 모달 헤더 스타일 */
    [data-testid="stModal"] > div[role="dialog"] > div:first-child {
        /* 헤더 패딩 */
        padding: 1rem 1.5rem !important;

        /* 하단 경계선 */
        border-bottom: 1px solid rgba(128, 128, 128, 0.2) !important;

        /* Flexbox 정렬 */
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
    }

    /* 모달 제목 스타일 */
    [data-testid="stModal"] h3 {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }

    /* 모달 본문 스타일 */
    [data-testid="stModal"] > div[role="dialog"] > div:nth-child(2) {
        padding: 1.5rem !important;
    }

    /* 모달 닫기 버튼 스타일 */
    [data-testid="stModal"] button[aria-label="Close"] {
        border-radius: 4px !important;
        padding: 0.25rem 0.5rem !important;
    }

    /* 반응형: 작은 화면에서 모달 조정 */
    @media (max-width: 768px) {
        [data-testid="stModal"] > div[role="dialog"] {
            width: 95% !important;
            max-height: 90vh !important;
            margin-top: 2vh !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
