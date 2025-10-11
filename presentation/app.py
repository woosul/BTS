"""
BTS - Bitcoin Auto Trading System
Streamlit 메인 애플리케이션 (st.navigation 방식)

최신 Streamlit navigation API를 사용한 SPA 구조
"""
import streamlit as st
from pathlib import Path
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 페이지 설정
st.set_page_config(
    page_title="BTS | Bitcoin Trading System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 로고 설정
logo_path = str(project_root / "resource" / "image" / "peaknine_logo_01.svg")
icon_path = str(project_root / "resource" / "image" / "peaknine_02.png")
st.logo(
    image=logo_path,
    icon_image=icon_path
)

# 페이지 정의
home_page = st.Page(
    "pages/00_Home_Content.py",
    title="홈",
    icon=":material/home:",
    default=True
)

dashboard_page = st.Page(
    "pages/1_Dashboard.py",
    title="대시보드",
    icon=":material/dashboard:"
)

wallet_page = st.Page(
    "pages/2_Wallet.py",
    title="지갑",
    icon=":material/account_balance_wallet:"
)

portfolio_page = st.Page(
    "pages/3_Portfolio.py",
    title="포트폴리오",
    icon=":material/pie_chart:"
)

strategy_page = st.Page(
    "pages/4_Strategy.py",
    title="전략설정",
    icon=":material/psychology:"
)

filtering_page = st.Page(
    "pages/5_Filtering.py",
    title="종목필터",
    icon=":material/filter_alt:"
)

screening_page = st.Page(
    "pages/6_Screening.py",
    title="종목선정",
    icon=":material/search:"
)

transaction_page = st.Page(
    "pages/7_Transaction.py",
    title="거래",
    icon=":material/receipt_long:"
)

backtest_page = st.Page(
    "pages/8_Backtest.py",
    title="백테스트",
    icon=":material/history:"
)

setting_page = st.Page(
    "pages/9_Setting.py",
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
