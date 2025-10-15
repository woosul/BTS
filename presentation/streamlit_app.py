# -*- coding: utf-8 -*-
"""
BTS - Bitcoin Auto Trading System
Streamlit 메인 애플리케이션 (st.navigation 방식)

최신 Streamlit navigation API를 사용한 SPA 구조
"""
import streamlit as st
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="BTS | Bitcoin Trading System",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 로고 설정
# 프로젝트 루트에서 실행되므로 resource 폴더 참조
try:
    import os
    from pathlib import Path

    # 프로젝트 루트 기준 경로
    logo_svg = "resource/image/peaknine_logo_01.svg"
    logo_png = "resource/image/peaknine_02.png"

    if os.path.exists(logo_svg) and os.path.exists(logo_png):
        st.logo(
            image=logo_svg,
            icon_image=logo_png
        )
    else:
        logger.warning(f"로고 파일을 찾을 수 없습니다: {logo_svg}")
except Exception as e:
    logger.warning(f"로고 설정 실패: {e}")

# 전역 스타일
st.markdown("""
    <style>
    /* 모든 버튼의 border-radius를 0으로 설정 (number input 제외) */
    button:not([data-testid="stNumberInput"] button) {
        border-radius: 0 !important;
    }
    
    /* 사이드바 width 설정 제거 - Streamlit 기본 동작 사용 */
    /* 필요시 나중에 재적용 */

    /* 사이드바 네비게이션 메뉴 스타일 */
    /* 기본 메뉴 아이템 */
    [data-testid="stSidebarNav"] li a {
        border-radius: 2px !important;
        transition: all 0.2s ease !important;
    }
    
    /* Hover 상태 */
    [data-testid="stSidebarNav"] li a:hover {
        background-color: rgba(84, 160, 253, 0.1) !important;
        border-radius: 2px !important;
    }
    
    /* 선택된 메뉴 (active) */
    [data-testid="stSidebarNav"] li a[aria-current="page"] {
        background-color: #54A0FD !important;
        border-radius: 2px !important;
        font-weight: 600 !important;
    }
    
    /* 선택된 메뉴의 아이콘과 텍스트 색상 */
    [data-testid="stSidebarNav"] li a[aria-current="page"] span,
    [data-testid="stSidebarNav"] li a[aria-current="page"] p {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# 페이지 정의 (st.Page 객체)
home_page = st.Page(
    "pages/Home.py",
    title="홈",
    icon=":material/home:",
    default=True
)

dashboard_page = st.Page(
    "pages/Dashboard.py",
    title="대시보드",
    icon=":material/dashboard:"
)

wallet_page = st.Page(
    "pages/Wallet.py",
    title="지갑",
    icon=":material/account_balance_wallet:"
)

portfolio_page = st.Page(
    "pages/Portfolio.py",
    title="포트폴리오",
    icon=":material/pie_chart:"
)

strategy_page = st.Page(
    "pages/Strategy.py",
    title="전략설정",
    icon=":material/strategy:"
)

filtering_page = st.Page(
    "pages/Filtering.py",
    title="종목필터",
    icon=":material/filter_alt:"
)

screening_page = st.Page(
    "pages/Screening.py",
    title="종목선정",
    icon=":material/search:"
)

transaction_page = st.Page(
    "pages/Transaction.py",
    title="거래",
    icon=":material/receipt_long:"
)

backtest_page = st.Page(
    "pages/Backtest.py",
    title="백테스트",
    icon=":material/history:"
)

setting_page = st.Page(
    "pages/Setting.py",
    title="설정",
    icon=":material/settings:"
)

# 네비게이션 구성
pg = st.navigation([
    home_page,
    dashboard_page,
    wallet_page,
    portfolio_page,
    strategy_page,
    filtering_page,
    screening_page,
    transaction_page,
    backtest_page,
    setting_page
])

# 선택된 페이지 실행
pg.run()
