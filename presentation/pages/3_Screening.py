"""
BTS 종목선정 페이지

KRW/BTC 시장에서 투자 가치가 높은 종목을 선정
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from application.services.screening_service import ScreeningService
from infrastructure.exchanges.upbit_client import UpbitClient
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="종목선정 - BTS",
    page_icon="",
    layout="wide"
)

# 사이드바 로고 설정
# 사이드바 로고 설정
logo_path = str(project_root / "resource" / "image" / "peaknine_logo_01.svg")
icon_path = str(project_root / "resource" / "image" / "peaknine_02.png")
st.logo(
    image=logo_path,
    icon_image=logo_path
)

# 로고 크기 조정 및 메뉴 스타일
st.markdown("""
<style>
    /* Noto Sans KR 폰트 로드 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
    /* Bootstrap Icons 로드 */
    @import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');
    /* Material Icons 로드 */
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    /* 전체 폰트 적용 (아이콘 제외) */
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif !important;
    }

    /* Streamlit 내부 요소 폰트 적용 */
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
    }
</style>
""", unsafe_allow_html=True)

def get_services():
    """서비스 인스턴스 가져오기"""
    if 'db' not in st.session_state:
        from infrastructure.database.connection import SessionLocal
        st.session_state.db = SessionLocal()

    if 'screening_service' not in st.session_state:
        exchange = UpbitClient()
        st.session_state.screening_service = ScreeningService(st.session_state.db, exchange)

    return st.session_state.screening_service

def main():
    # 전체 페이지 스타일 조정
    st.markdown("""
    <style>
    /* 타이틀 크기 조정 */
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
    /* 구분선 여백 조정 */
    hr {
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
    }
    /* 블록 요소 여백 조정 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1>종목선정</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

    # 서비스 초기화
    screening_service = get_services()

    # 사이드바: 스크리닝 설정
    with st.sidebar:
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>스크리닝 설정</h3>", unsafe_allow_html=True)

        # 시장 선택
        market = st.selectbox(
            "시장",
            options=["KRW", "BTC"],
            help="대상 시장 선택"
        )

        # 전략 선택
        strategy_type = st.selectbox(
            "전략",
            options=["momentum", "volume", "technical", "hybrid"],
            format_func=lambda x: {
                "momentum": "모멘텀 기반",
                "volume": "거래량 기반",
                "technical": "기술지표 복합",
                "hybrid": "하이브리드"
            }[x],
            help="스크리닝 전략 선택"
        )

        # 시장의 전체 종목 수 미리 조회 (대략적인 수)
        try:
            from infrastructure.exchanges.upbit_client import UpbitClient
            temp_exchange = UpbitClient()
            market_symbols = temp_exchange.get_market_symbols(market)
            total_symbols = len(market_symbols)
            # 5의 배수로 올림
            max_symbols = ((total_symbols + 4) // 5) * 5
        except:
            total_symbols = 200
            max_symbols = 200

        # 상위 종목 수
        # 한 줄에 배치하기 위해 columns 사용
        cols = st.columns([0.65, 0.35])

        with cols[0]:
            st.markdown("<h3 style='margin-bottom: 0.5rem;'>선정 종목 수</h3>", unsafe_allow_html=True)

        with cols[1]:
            # 수직 정렬 및 우측 정렬을 위해 HTML 사용
            st.markdown(
                """
                <div style="display: flex; justify-content: flex-end; align-items: center; height: 40px;">
                </div>
                """,
                unsafe_allow_html=True
            )
            # 우측 정렬을 위한 컨테이너
            col_right = st.container()
            with col_right:
                show_all = st.toggle("All", value=False, help="전체 종목 표시", key="show_all_toggle")

        if show_all:
            st.info(f"전체 종목을 표시합니다 (총 {total_symbols}개)")
            top_n = total_symbols
        else:
            top_n = st.slider(
                "상위 종목",
                min_value=5,
                max_value=max_symbols,
                value=10,
                step=5,
                help=f"상위 N개 종목 선정 (최대 {max_symbols}개)",
                label_visibility="collapsed"
            )
            st.caption(f"상위 {top_n}개 종목 (전체 {total_symbols}개 중)")

        st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

        # 전략별 파라미터 설정
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>전략 파라미터</h3>", unsafe_allow_html=True)

        strategy_params = {}

        if strategy_type == "momentum":
            st.write("**가중치 설정** (합계 1.0)")
            price_weight = st.slider(
                "가격 상승률",
                0.0, 1.0, 0.4, 0.1,
                help="가격 변동률 가중치"
            )
            volume_weight = st.slider(
                "거래량 증가율",
                0.0, 1.0, 0.3, 0.1,
                help="거래량 변동률 가중치"
            )
            rsi_weight = st.slider(
                "RSI 모멘텀",
                0.0, 1.0, 0.3, 0.1,
                help="RSI 모멘텀 가중치"
            )

            # 가중치 합계 체크
            total = price_weight + volume_weight + rsi_weight
            if abs(total - 1.0) > 0.01:
                st.warning(f"가중치 합계: {total:.2f} (1.0이어야 함)")

            strategy_params = {
                "price_weight": price_weight,
                "volume_weight": volume_weight,
                "rsi_weight": rsi_weight,
                "lookback_days": 7
            }

        elif strategy_type == "volume":
            st.info("기본 설정 사용")
            strategy_params = {}

        elif strategy_type == "technical":
            st.info("기본 설정 사용 (RSI + MACD + MA)")
            strategy_params = {}

        elif strategy_type == "hybrid":
            st.warning("하이브리드 전략은 추후 구현 예정")
            strategy_params = {
                "strategies": [],
                "weights": []
            }

        st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)

        # 스크리닝 실행 버튼
        run_screening = st.button(
            "스크리닝 실행",
            type="primary",
            use_container_width=True
        )

    # 메인 영역
    if run_screening:
        with st.spinner("스크리닝 실행 중..."):
            try:
                # 스크리닝 실행
                results = screening_service.screen_symbols(
                    market=market,
                    strategy_type=strategy_type,
                    strategy_params=strategy_params,
                    top_n=top_n
                )

                # 결과 저장
                st.session_state.screening_results = results
                st.session_state.screening_market = market
                st.session_state.screening_strategy = strategy_type
                st.session_state.screening_time = datetime.now()

            except Exception as e:
                logger.error(f"스크리닝 실패: {e}")
                st.error(f"스크리닝 실패: {e}")
                import traceback
                st.text(traceback.format_exc())

    # 결과 표시
    if 'screening_results' in st.session_state and st.session_state.screening_results:
        results = st.session_state.screening_results

        st.markdown(f"<h3 style='margin-bottom: 10px;'>스크리닝 결과 (상위 {len(results)}개)</h3>", unsafe_allow_html=True)

        # 메타 정보 - 카드형 스타일
        st.markdown("""
        <style>
        .metric-card {
            background-color: #1E1E1E;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 12px;
            border: 1px solid #3d3d4a;
        }
        .metric-label {
            font-size: 0.75rem;
            color: #9ca3af;
            margin-bottom: 4px;
        }
        .metric-value {
            font-size: 1rem;
            font-weight: 600;
            color: #FAFAFA;
        }
        </style>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">시장</div>
                <div class="metric-value">{st.session_state.screening_market}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            strategy_name = {
                "momentum": "모멘텀",
                "volume": "거래량",
                "technical": "기술지표",
                "hybrid": "하이브리드"
            }.get(st.session_state.screening_strategy, "Unknown")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">전략</div>
                <div class="metric-value">{strategy_name}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">실행 시간</div>
                <div class="metric-value">{st.session_state.screening_time.strftime("%H:%M:%S")}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin: 12px 0;'></div>", unsafe_allow_html=True)

        # 결과 테이블
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>선정 종목</h3>", unsafe_allow_html=True)

        # DataFrame 생성
        data = []
        for i, result in enumerate(results, 1):
            row = {
                "순위": i,
                "종목": result.symbol,
                "점수": result.score,
            }

            # 세부 점수 추가
            for key, value in result.details.items():
                if isinstance(value, (int, float)):
                    row[key] = value
                else:
                    row[key] = str(value)

            data.append(row)

        df = pd.DataFrame(data)

        # 숫자형 컬럼 식별
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns

        # 컬럼 순서를 재배열하기 위한 새로운 DataFrame 구성
        new_columns = ["순위", "종목"]

        for col in numeric_columns:
            if col not in ["순위"]:  # 전체 순위 컬럼은 제외
                # 순위 계산 (내림차순 - 높은 값이 좋음)
                rank_col = f"{col}_R"
                df[rank_col] = df[col].rank(ascending=False, method='min').astype(int)

                # 값 컬럼과 순위 컬럼을 순서대로 추가
                new_columns.append(col)
                new_columns.append(rank_col)

        # 문자열 컬럼 추가 (순위가 없는 컬럼들)
        for col in df.columns:
            if col not in new_columns and col not in numeric_columns:
                new_columns.append(col)

        # 컬럼 순서 재배열
        df = df[new_columns]

        # 전체 컬럼 수 계산하여 동적 width 설정
        total_cols = len(df.columns)

        # 1-5위 순위를 강조하기 위해 텍스트로 변환
        display_df = df.copy()
        for col in df.columns:
            if col.endswith("_R"):
                # 1-5위는 "1 ●", "2 ●" 형식으로 표시
                display_df[col] = df[col].apply(
                    lambda x: f"{int(x)} ●" if x <= 5 else str(int(x))
                )

        # 동적으로 컬럼 너비 계산
        # 전체 컬럼 수에 따라 값 컬럼과 R 컬럼 너비 조정
        num_value_cols = len([c for c in df.columns if c not in ["순위", "종목"] and not c.endswith("_R")])

        # 고정 컬럼: 순위(60px), 종목(120px)
        # R 컬럼: 40px
        # 나머지를 값 컬럼들이 균등 분배

        # 컬럼 설정
        column_config = {}
        for col in display_df.columns:
            if col == "순위":
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    width=60
                )
            elif col == "종목":
                column_config[col] = st.column_config.TextColumn(
                    col,
                    width=100
                )
            elif col.endswith("_R"):
                # 순위 컬럼 - "R"로 표시
                column_config[col] = st.column_config.TextColumn(
                    "R",
                    width=45
                )
            elif col in numeric_columns and col != "순위":
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    width=90,
                    format="%.2f"
                )

        # 스타일 적용 - 행 선택 가능하도록 변경
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config=column_config,
            on_select="rerun",
            selection_mode="single-row"
        )

        # 다운로드 버튼
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="CSV 다운로드",
            data=csv,
            file_name=f"screening_{st.session_state.screening_market}_{st.session_state.screening_time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        # 상세 정보
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>종목 상세 정보</h3>", unsafe_allow_html=True)

        # 테이블에서 선택된 행이 있는지 확인
        selected_symbol = None
        if event.selection and event.selection.rows:
            selected_row_idx = event.selection.rows[0]
            # display_df의 해당 행에서 종목명 가져오기
            selected_symbol = display_df.iloc[selected_row_idx]["종목"]
            st.info(f"선택된 종목: **{selected_symbol}**")
        else:
            # 테이블에서 선택이 없으면 selectbox로 선택
            selected_symbol = st.selectbox(
                "종목 선택",
                options=[r.symbol for r in results],
                format_func=lambda x: f"{x} ({next(r.score for r in results if r.symbol == x):.2f}점)"
            )

        if selected_symbol:
            selected_result = next(r for r in results if r.symbol == selected_symbol)

            col1, col2 = st.columns(2)

            with col1:
                st.write("**기본 정보**")
                st.write(f"- 종목: {selected_result.symbol}")
                st.write(f"- 총점: {selected_result.score:.2f}")
                st.write(f"- 평가 시간: {selected_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            with col2:
                st.write("**세부 점수**")

                # 숫자형 세부 점수만 추출
                numeric_scores = {}
                for key, value in selected_result.details.items():
                    if isinstance(value, (int, float)):
                        numeric_scores[key] = value

                if numeric_scores:
                    # Radar chart 생성
                    import plotly.graph_objects as go

                    categories = list(numeric_scores.keys())
                    values = list(numeric_scores.values())

                    fig = go.Figure()

                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=categories,
                        fill='toself',
                        name=selected_result.symbol,
                        line=dict(color='#54A0FD'),
                        fillcolor='rgba(84, 160, 253, 0.3)'
                    ))

                    fig.update_layout(
                        polar=dict(
                            bgcolor='#262730',
                            radialaxis=dict(
                                visible=True,
                                range=[0, max(values) * 1.1] if values else [0, 100],
                                gridcolor='#3d3d4a',
                                linecolor='#3d3d4a'
                            ),
                            angularaxis=dict(
                                gridcolor='#3d3d4a',
                                linecolor='#3d3d4a',
                                color='#FAFAFA'
                            )
                        ),
                        showlegend=False,
                        height=400,
                        margin=dict(l=80, r=80, t=40, b=40),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#FAFAFA')
                    )

                    st.plotly_chart(fig, use_container_width=True)

                # 비숫자형 항목은 텍스트로 표시
                non_numeric = {k: v for k, v in selected_result.details.items()
                              if not isinstance(v, (int, float))}
                if non_numeric:
                    st.write("**기타 정보**")
                    for key, value in non_numeric.items():
                        st.write(f"- {key}: {value}")

    else:
        # 초기 화면
        st.info(
            "왼쪽 사이드바에서 시장과 전략을 선택한 후 "
            "'스크리닝 실행' 버튼을 클릭하세요."
        )

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        # 가이드
        st.markdown("<h3 style='margin-bottom: 0.8rem;'>스크리닝 전략 소개</h3>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **모멘텀 기반**
            - 가격 상승률
            - 거래량 증가율
            - RSI 모멘텀
            - 가중치 조합

            **거래량 기반**
            - 거래대금 순위
            - 거래량 급증 감지
            - 유동성 점수
            """)

        with col2:
            st.markdown("""
            **기술지표 복합**
            - RSI
            - MACD
            - 이동평균 정배열
            - 복합 지표 점수

            **하이브리드**
            - 여러 전략 조합
            - 전략별 가중치
            - 최적 조합 탐색
            """)

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        st.markdown("<h3 style='margin-bottom: 0.8rem;'>사용 방법</h3>", unsafe_allow_html=True)

        st.markdown("""
        1. **시장 선택**: KRW 또는 BTC 시장
        2. **전략 선택**: 4가지 스크리닝 전략 중 선택
        3. **파라미터 설정**: 전략별 가중치 및 옵션 설정
        4. **스크리닝 실행**: 상위 N개 종목 자동 선정
        5. **결과 분석**: 선정된 종목의 점수 및 세부 정보 확인
        """)

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        st.markdown("<h3 style='margin-bottom: 0.8rem;'>주의사항</h3>", unsafe_allow_html=True)

        st.markdown("""
        <div style='background-color: #00CCAC70; border-left: 4px solid #00CCAC; padding: 16px; border-radius: 4px;'>
            <div style='font-size: 0.875rem; color: #FAFAFA; line-height: 1.6;'>
                • 스크리닝 결과는 투자 참고 자료일 뿐, 투자 결정의 근거가 될 수 없습니다<br>
                • 시장 상황에 따라 점수가 달라질 수 있습니다<br>
                • 여러 전략을 조합하여 사용하는 것을 권장합니다<br>
                • 백테스팅을 통해 전략의 유효성을 검증하세요
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
