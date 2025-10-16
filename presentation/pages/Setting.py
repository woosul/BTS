"""
BTS 시스템 설정

사용자, 운영시간, 운영방법 및 운영전략에 대한 시스템 설정
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.repositories.user_settings_repository import UserSettingsRepository
from domain.entities.user_settings import UserSettings
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    st.title("시스템 설정")
    st.markdown("---")
    
    # UserSettingsRepository 인스턴스 생성
    settings_repo = UserSettingsRepository()
    
    # 시스템 설정값 불러오기
    from config.market_index_config import MarketIndexConfig
    config = MarketIndexConfig()

    # 화면 업데이트 설정 섹션 (Dashboard 갱신)
    st.markdown("<h3 style='margin-bottom: 0.8rem;'>화면 업데이트 설정</h3>", unsafe_allow_html=True)
    st.markdown("**WebSocket 실시간 업데이트**와 별개로, 대시보드 페이지 전체를 새로고침하는 간격입니다.")
    st.info("WebSocket이 5초마다 데이터를 자동 업데이트하므로, 일반적으로 OFF를 권장합니다.")

    # 현재 설정값 가져오기
    current_dashboard_setting = settings_repo.get_by_key(UserSettings.DASHBOARD_REFRESH_INTERVAL)
    current_dashboard_interval = int(current_dashboard_setting.setting_value) if current_dashboard_setting else 0

    # 간격 옵션
    dashboard_interval_options = {
        "OFF (WebSocket만 사용)": 0,
        "10초": 10,
        "30초": 30,
        "1분": 60,
        "3분": 180,
        "5분": 300,
        "10분": 600
    }

    # 현재 설정에 맞는 라벨 찾기
    current_dashboard_label = next((k for k, v in dashboard_interval_options.items() if v == current_dashboard_interval), "OFF (WebSocket만 사용)")
    current_dashboard_index = list(dashboard_interval_options.keys()).index(current_dashboard_label)

    # selectbox와 버튼을 한 줄에 배치
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_dashboard_label = st.selectbox(
            "대시보드 페이지 새로고침 간격",
            options=list(dashboard_interval_options.keys()),
            index=current_dashboard_index,
            key="dashboard_refresh_setting",
            help="WebSocket이 실시간 업데이트를 제공하므로 OFF 권장. 페이지 전체 새로고침이 필요한 경우에만 활성화하세요.",
            label_visibility="collapsed"
        )
    with col2:
        save_btn = st.button("저장", key="save_dashboard_refresh", use_container_width=True)

    if save_btn:
        selected_dashboard_interval = dashboard_interval_options[selected_dashboard_label]
        settings_repo.upsert(
            key=UserSettings.DASHBOARD_REFRESH_INTERVAL,
            value=str(selected_dashboard_interval),
            description="대시보드 페이지 자동 갱신 간격 (초)"
        )
        if selected_dashboard_interval == 0:
            st.success("화면 새로고침이 OFF로 설정되었습니다. WebSocket이 실시간 업데이트를 제공합니다.")
        else:
            st.success(f"화면 새로고침 간격이 {selected_dashboard_label}로 설정되었습니다.")
        st.rerun()

    st.markdown("---")

    # 백그라운드 업데이트 설정 섹션
    st.markdown("<h3 style='margin-bottom: 0.8rem;'>백그라운드 업데이트 설정</h3>", unsafe_allow_html=True)
    st.markdown("대시보드 외 다른 페이지에 있을 때의 백그라운드 데이터 업데이트 간격을 설정합니다.")
    st.info("종목선정/매수분석 시 API 충돌 방지를 위해 백그라운드 업데이트 주기를 조절합니다.")

    # 현재 설정값 가져오기
    current_general_setting = settings_repo.get_by_key(UserSettings.GENERAL_UPDATE_INTERVAL)
    current_general_interval = int(current_general_setting.setting_value) if current_general_setting else config.DEFAULT_BACKGROUND_UPDATE_INTERVAL

    # 간격 옵션을 config에서 가져오기
    available_intervals = config.get_available_background_intervals()
    interval_options = {}
    for interval in available_intervals:
        label = config.get_background_interval_label(interval)
        interval_options[label] = interval

    # 현재 설정에 맞는 라벨 찾기
    current_general_label = config.get_background_interval_label(current_general_interval)
    if current_general_label not in interval_options:
        # 설정값이 옵션에 없으면 가장 가까운 값으로 매칭
        closest = min(interval_options.values(), key=lambda x: abs(x - current_general_interval))
        current_general_label = config.get_background_interval_label(closest)
    current_general_index = list(interval_options.keys()).index(current_general_label)

    # selectbox와 버튼을 한 줄에 배치
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_general_label = st.selectbox(
            "백그라운드 업데이트 간격",
            options=list(interval_options.keys()),
            index=current_general_index,
            key="general_update_interval_setting",
            help=f"다른 페이지에 있을 때 백그라운드에서 데이터를 수집하는 간격입니다. (최소 {config.SYSTEM_MIN_UPDATE_INTERVAL}초)",
            label_visibility="collapsed"
        )
    with col2:
        save_general_btn = st.button("저장", key="save_general", use_container_width=True)

    if save_general_btn:
        selected_general_interval = interval_options[selected_general_label]

        # 시스템 최소값 유효성 검증
        validated_interval = config.validate_update_interval(selected_general_interval)

        if validated_interval != selected_general_interval:
            st.warning(f"선택한 간격이 시스템 최소값보다 작아 {validated_interval}초로 조정되었습니다.")

        settings_repo.upsert(
            key=UserSettings.GENERAL_UPDATE_INTERVAL,
            value=str(validated_interval),
            description="백그라운드 일반 업데이트 간격 (초)"
        )
        st.success(f"백그라운드 업데이트 간격이 {validated_interval}초로 저장되었습니다.")
        st.rerun()
    
    # 현재 설정 표시
    st.markdown("---")
    st.markdown("<h3 style='margin-bottom: 0.8rem;'>현재 설정 상태</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("백그라운드 업데이트", f"{current_general_interval}초")

    with col2:
        st.metric("시스템 최소값", f"{config.SYSTEM_MIN_UPDATE_INTERVAL}초")

    with col3:
        st.metric("마지막 확인", datetime.now().strftime("%H:%M:%S"))
    
    # 데이터 소스별 수집 주기 섹션
    st.markdown("---")
    st.markdown("<h3 style='margin-bottom: 0.8rem;'>데이터 소스별 수집 주기</h3>", unsafe_allow_html=True)
    st.markdown("각 데이터 소스는 독립적인 스레드로 실행되며, 서로 다른 업데이트 주기를 가집니다.")

    source_col1, source_col2 = st.columns(2)

    with source_col1:
        st.markdown("**실시간 업데이트**")
        st.markdown(f"- 업비트 지수: {config.UPDATE_INTERVAL_UPBIT_SCRAPING}초 (웹스크래핑)")
        st.markdown(f"- USD/KRW 환율: {config.UPDATE_INTERVAL_UPBIT_SCRAPING}초 (Upbit에서 함께 수집)")
        st.markdown(f"- 글로벌 지수: {config.UPDATE_INTERVAL_COINGECKO}초 (CoinGecko)")
        st.success("업비트 지수는 5초마다, 글로벌 지수는 6초마다 업데이트됩니다.")

    with source_col2:
        st.markdown("**Fallback API (1시간+)**")
        st.markdown(f"- FxRatesAPI: {config.UPDATE_INTERVAL_FXRATES // 3600}시간")
        st.markdown(f"  - Upbit 스크래핑 실패 시 자동 전환")
        st.markdown(f"  - 무료 플랜: 1000 requests/month")
        st.markdown(f"- Currency API: 일일 업데이트 (최종 fallback)")
        st.info("Upbit에서 실시간 USD/KRW를 가져오므로 fallback은 거의 사용되지 않습니다.")

    # WebSocket 전송 주기 섹션
    st.markdown("---")
    st.markdown("<h3 style='margin-bottom: 0.8rem;'>화면 업데이트 주기</h3>", unsafe_allow_html=True)
    st.markdown("대시보드 화면에 데이터가 표시되는 주기입니다.")

    ws_col1, ws_col2, ws_col3 = st.columns(3)

    with ws_col1:
        st.metric("WebSocket 전송", f"{config.WEBSOCKET_UPDATE_INTERVAL}초")
        st.caption("화면 업데이트 주기")

    with ws_col2:
        st.metric("데이터 수집", f"{config.UPDATE_INTERVAL_UPBIT_SCRAPING}~{config.UPDATE_INTERVAL_COINGECKO}초")
        st.caption("업비트(5초)/글로벌(6초)")

    with ws_col3:
        st.metric("실시간성", "95%+")
        st.caption("5초 주기, 시장 변화 즉시 반영")

    st.success("고속 업데이트: 화면 업데이트(5초), 업비트 데이터 수집(5초), 글로벌 데이터 수집(6초)이 비동기로 실행됩니다.")

    # API Rate Limit 정보 섹션
    st.markdown("---")
    st.markdown("<h3 style='margin-bottom: 0.8rem;'>API Rate Limit 정보</h3>", unsafe_allow_html=True)
    st.markdown("외부 API의 속도 제한으로 인한 업데이트 주기 설정 근거입니다.")

    rate_col1, rate_col2 = st.columns(2)

    with rate_col1:
        st.markdown("**API 최소 간격**")
        st.markdown(f"- 업비트 스크래핑: {config.API_MIN_INTERVAL_UPBIT_SCRAPING}ms (5초)")
        st.markdown(f"- 업비트 API: {config.API_MIN_INTERVAL_UPBIT_API}ms (100ms)")
        st.markdown(f"- CoinGecko: {config.API_MIN_INTERVAL_COINGECKO}ms (4초)")
        st.markdown(f"- FxRatesAPI: {config.API_MIN_INTERVAL_FXRATES // 1000}초 (1시간)")
        st.markdown("- Currency API: 일일 업데이트 (fallback)")

    with rate_col2:
        st.markdown("**내부 제한값 (API+20%)**")
        st.markdown(f"- 업비트 스크래핑: {config.INTERNAL_MIN_INTERVAL_UPBIT_SCRAPING}ms (6초)")
        st.markdown(f"- 업비트 API: {config.INTERNAL_MIN_INTERVAL_UPBIT_API}ms (120ms)")
        st.markdown(f"- CoinGecko: {config.INTERNAL_MIN_INTERVAL_COINGECKO}ms (5초)")
        st.markdown("- FxRatesAPI: 1시간+20% (무료 제한)")
        st.markdown("- Currency API: 일일+20% (fallback)")

    st.info(f"시스템 최소값 {config.SYSTEM_MIN_UPDATE_INTERVAL}초는 화면 업데이트 최소값(10초) 기준으로 설정됩니다.")
    
if __name__ == "__main__":
    main()
