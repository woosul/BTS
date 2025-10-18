"""
BTS 포트폴리오 관리 페이지

자금 배분 및 리밸런싱
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
from decimal import Decimal

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 전역 스타일 적용
from presentation.styles.global_styles import apply_global_styles
apply_global_styles()

from application.services.portfolio_service import PortfolioService
from application.services.wallet_service import WalletService
from infrastructure.exchanges.upbit_client import UpbitClient
from infrastructure.database.connection import SessionLocal
from utils.logger import get_logger

logger = get_logger(__name__)

def get_services():
    """서비스 인스턴스 가져오기"""
    if 'db' not in st.session_state:
        st.session_state.db = SessionLocal()

    if 'portfolio_service' not in st.session_state:
        exchange = UpbitClient()
        st.session_state.portfolio_service = PortfolioService(st.session_state.db, exchange)

    if 'wallet_service' not in st.session_state:
        st.session_state.wallet_service = WalletService(st.session_state.db)

    return st.session_state.portfolio_service, st.session_state.wallet_service

def main():
    st.markdown("<h1>포트폴리오 관리</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

    # 서비스 초기화
    portfolio_service, wallet_service = get_services()

    # 사이드바: 지갑 및 전략 설정
    with st.sidebar:
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>지갑 선택</h3>", unsafe_allow_html=True)

        # 지갑 목록 조회
        try:
            wallets = wallet_service.get_all_wallets()

            if wallets:
                wallet_options = {
                    f"{w.name} ({w.wallet_type.value})": w.id
                    for w in wallets
                }

                selected_wallet_name = st.selectbox(
                    "지갑",
                    options=list(wallet_options.keys()),
                    key="portfolio_wallet_selector",
                    label_visibility="collapsed"
                )

                if selected_wallet_name:
                    st.session_state.portfolio_wallet_id = wallet_options[selected_wallet_name]
                    wallet = wallet_service.get_wallet(st.session_state.portfolio_wallet_id)
                    st.caption(f"잔액: ₩{float(wallet.balance_krw):,.0f}")

            else:
                st.warning("등록된 지갑이 없습니다.")
                st.session_state.portfolio_wallet_id = None

        except Exception as e:
            logger.error(f"지갑 목록 조회 실패: {e}")
            st.error(f"지갑 목록 조회 실패: {e}")
            st.session_state.portfolio_wallet_id = None

        st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

        # 포트폴리오 전략 선택
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>배분 전략</h3>", unsafe_allow_html=True)

        strategy_type = st.selectbox(
            "전략",
            options=["equal_weight", "proportional_weight", "kelly_criterion", "risk_parity", "dynamic_allocation"],
            format_func=lambda x: {
                "equal_weight": "균등 배분",
                "proportional_weight": "비율 배분",
                "kelly_criterion": "켈리 기준",
                "risk_parity": "리스크 패리티",
                "dynamic_allocation": "동적 배분"
            }[x],
            help="자금 배분 전략 선택",
            label_visibility="collapsed"
        )

        st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

        # 전략별 파라미터
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>전략 파라미터</h3>", unsafe_allow_html=True)

        strategy_params = {}

        if strategy_type == "equal_weight":
            st.info("모든 종목에 동일 금액 배분")

        elif strategy_type == "proportional_weight":
            st.write("**가중치 방식**")
            weight_mode = st.radio(
                "방식",
                options=["rank", "custom"],
                format_func=lambda x: "순위 기반" if x == "rank" else "사용자 지정",
                label_visibility="collapsed"
            )

            if weight_mode == "rank":
                st.caption("1위부터 차등 가중치 자동 부여")
            else:
                st.caption("종목별 가중치 직접 입력")

            strategy_params["weight_mode"] = weight_mode

        elif strategy_type == "kelly_criterion":
            st.write("**켈리 파라미터**")
            kelly_fraction = st.slider(
                "켈리 분수",
                0.1, 1.0, 0.5, 0.1,
                help="Full Kelly의 비율 (0.5 = Half Kelly)"
            )
            strategy_params["kelly_fraction"] = kelly_fraction

        elif strategy_type == "risk_parity":
            st.write("**변동성 계산**")
            lookback_days = st.slider(
                "계산 기간 (일)",
                7, 60, 30, 1,
                help="변동성 계산 기간"
            )
            strategy_params["lookback_days"] = lookback_days

        elif strategy_type == "dynamic_allocation":
            st.write("**동적 배분 설정**")
            reserve_ratio = st.slider(
                "현금 예비비 (%)",
                0.0, 0.5, 0.2, 0.05,
                help="시장 리스크에 따른 현금 보유 비율"
            )
            strategy_params["reserve_ratio"] = reserve_ratio

        st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

        # 종목 입력
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>종목 선택</h3>", unsafe_allow_html=True)

        # 스크리닝 결과 불러오기 옵션
        use_screening = st.checkbox(
            "스크리닝 결과 사용",
            value=False,
            help="종목선정 페이지의 결과 사용"
        )

        if use_screening and 'screening_results' in st.session_state:
            screening_results = st.session_state.screening_results
            selected_symbols = [r.symbol for r in screening_results[:10]]
            st.success(f"{len(selected_symbols)}개 종목 자동 선택됨")
            st.caption(", ".join(selected_symbols))
        else:
            symbol_input = st.text_area(
                "종목 (쉼표 구분)",
                value="KRW-BTC, KRW-ETH, KRW-XRP",
                help="예: KRW-BTC, KRW-ETH, KRW-XRP",
                label_visibility="collapsed"
            )
            selected_symbols = [s.strip() for s in symbol_input.split(",") if s.strip()]

        # 커스텀 가중치 (proportional_weight + custom mode)
        custom_weights = {}
        if strategy_type == "proportional_weight" and strategy_params.get("weight_mode") == "custom":
            st.write("**종목별 가중치**")
            total_weight = 0.0
            for symbol in selected_symbols:
                weight = st.slider(
                    symbol,
                    0.0, 1.0, 1.0 / len(selected_symbols), 0.05,
                    key=f"weight_{symbol}"
                )
                custom_weights[symbol] = weight
                total_weight += weight

            if abs(total_weight - 1.0) > 0.01:
                st.warning(f"가중치 합계: {total_weight:.2f} (1.0이어야 함)")

            strategy_params["weights"] = custom_weights

        st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

        # 배분 실행 버튼
        run_allocation = st.button(
            "배분 실행",
            type="primary",
            use_container_width=True
        )

    # 메인 영역
    if not st.session_state.get('portfolio_wallet_id'):
        st.warning("왼쪽 사이드바에서 지갑을 선택하세요.")
        return

    # 배분 실행
    if run_allocation:
        if not selected_symbols:
            st.error("종목을 입력하세요.")
        else:
            with st.spinner("포트폴리오 배분 중..."):
                try:
                    wallet = wallet_service.get_wallet(st.session_state.portfolio_wallet_id)

                    # 배분 실행
                    result = portfolio_service.calculate_allocation(
                        available_balance=wallet.balance_krw,
                        selected_symbols=selected_symbols,
                        strategy_type=strategy_type,
                        strategy_params=strategy_params
                    )

                    # 결과 저장
                    st.session_state.allocation_result = result
                    st.session_state.allocation_time = datetime.now()
                    st.session_state.allocation_strategy = strategy_type
                    st.session_state.allocation_symbols = selected_symbols

                    st.success("배분 완료!")

                except Exception as e:
                    logger.error(f"배분 실패: {e}")
                    st.error(f"배분 실패: {e}")
                    import traceback
                    st.text(traceback.format_exc())

    # 결과 표시
    if 'allocation_result' in st.session_state and st.session_state.allocation_result:
        result = st.session_state.allocation_result

        st.markdown("<h3 style='margin-bottom: 10px;'>배분 결과</h3>", unsafe_allow_html=True)

        # 메타 정보
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">전략</div>
                <div class="metric-value">{
                    {
                        "equal_weight": "균등 배분",
                        "proportional_weight": "비율 배분",
                        "kelly_criterion": "켈리 기준",
                        "risk_parity": "리스크 패리티",
                        "dynamic_allocation": "동적 배분"
                    }.get(st.session_state.allocation_strategy, "Unknown")
                }</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">종목 수</div>
                <div class="metric-value">{len(result.allocations)}개</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">실행 시간</div>
                <div class="metric-value">{st.session_state.allocation_time.strftime("%H:%M:%S")}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin: 12px 0;'></div>", unsafe_allow_html=True)

        # 배분 테이블
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>배분 내역</h3>", unsafe_allow_html=True)

        data = []
        total_allocation = Decimal("0")
        for symbol in result.allocations:
            allocation = result.allocations[symbol]
            weight = result.weights[symbol]
            total_allocation += allocation

            data.append({
                "종목": symbol,
                "배분 금액": float(allocation),
                "비중": float(weight) * 100,
            })

        df = pd.DataFrame(data)

        # 합계 행 추가
        total_row = pd.DataFrame([{
            "종목": "합계",
            "배분 금액": float(total_allocation),
            "비중": sum(df["비중"]),
        }])
        df = pd.concat([df, total_row], ignore_index=True)

        # 컬럼 설정
        column_config = {
            "종목": st.column_config.TextColumn(
                "종목",
                width=120
            ),
            "배분 금액": st.column_config.NumberColumn(
                "배분 금액 (KRW)",
                format="₩%.0f",
                width=150
            ),
            "비중": st.column_config.NumberColumn(
                "비중 (%)",
                format="%.2f%%",
                width=100
            ),
        }

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )

        # 원형 차트
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>비중 분포</h3>", unsafe_allow_html=True)

        import plotly.graph_objects as go

        # 합계 행 제외
        pie_df = df[df["종목"] != "합계"]

        fig = go.Figure(data=[go.Pie(
            labels=pie_df["종목"],
            values=pie_df["비중"],
            hole=0.4,
            marker=dict(
                colors=['#54A0FD', '#FF6B6B', '#4ECDC4', '#FFE66D', '#A8E6CF', '#FF8B94', '#C7CEEA'],
                line=dict(color='#262730', width=2)
            ),
            textinfo='label+percent',
            textfont=dict(color='#FAFAFA', size=12)
        )])

        fig.update_layout(
            showlegend=True,
            height=400,
            margin=dict(l=40, r=40, t=40, b=40),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FAFAFA'),
            legend=dict(
                bgcolor='#1E1E1E',
                bordercolor='#3d3d4a',
                borderwidth=1
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        # 추가 정보 (메타데이터)
        if result.metadata:
            st.markdown("<h3 style='margin-bottom: 0.8rem;'>추가 정보</h3>", unsafe_allow_html=True)

            with st.expander("메타데이터 보기"):
                st.json(result.metadata)

        # CSV 다운로드
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="CSV 다운로드",
            data=csv,
            file_name=f"portfolio_{st.session_state.allocation_time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    else:
        # 초기 화면
        st.info(
            "왼쪽 사이드바에서 지갑, 전략, 종목을 선택한 후 "
            "'배분 실행' 버튼을 클릭하세요."
        )

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        # 가이드
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>포트폴리오 전략 소개</h3>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **균등 배분 (Equal Weight)**
            - 모든 종목에 동일 금액 배분
            - 가장 단순하고 안정적
            - 소규모 포트폴리오에 적합

            **비율 배분 (Proportional Weight)**
            - 순위 기반 또는 사용자 지정 가중치
            - 전략적 비중 조절 가능
            - 유연한 포트폴리오 구성

            **켈리 기준 (Kelly Criterion)**
            - 수학적 최적 포지션 크기
            - 승률과 손익비 기반
            - Half Kelly 권장 (안정성)
            """)

        with col2:
            st.markdown("""
            **리스크 패리티 (Risk Parity)**
            - 변동성 기반 역가중치
            - 리스크 균등 배분
            - 안정적인 포트폴리오

            **동적 배분 (Dynamic Allocation)**
            - 시장 상황 반영
            - 변동성에 따른 현금 비중 조절
            - 공격적/보수적 자동 전환
            """)

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        st.markdown("<h3 style='margin-bottom: 0.8rem;'>사용 팁</h3>", unsafe_allow_html=True)

        st.markdown("""
        - **스크리닝 연계**: 종목선정 페이지 결과를 바로 사용 가능
        - **리밸런싱**: 정기적으로 재배분하여 목표 비중 유지
        - **백테스팅**: 전략별 성과를 백테스트로 검증
        - **분산투자**: 5-10개 종목 권장
        """)

if __name__ == "__main__":
    main()
