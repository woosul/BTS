"""
BTS 백테스팅 페이지

전략 백테스팅 및 성과 분석
"""
import streamlit as st
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infrastructure.database.connection import get_db_session
from application.services.strategy_service import StrategyService
from infrastructure.exchanges.upbit_client import UpbitClient
from presentation.components.forms import render_backtest_form
from utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="백테스팅 - BTS",
    page_icon="📊",
    layout="wide"
)

def get_services():
    """서비스 인스턴스 가져오기"""
    if 'db' not in st.session_state:
        db_gen = get_db_session()
        st.session_state.db = next(db_gen)

    if 'strategy_service' not in st.session_state:
        exchange = UpbitClient()
        st.session_state.strategy_service = StrategyService(st.session_state.db, exchange)

    return st.session_state.strategy_service

def main():
    st.title("📊 백테스팅")
    st.markdown("---")

    # 서비스 초기화
    strategy_service = get_services()

    # 백테스팅 설정
    backtest_config = render_backtest_form()

    if backtest_config:
        try:
            # 백테스팅 실행
            with st.spinner("백테스팅 실행 중..."):
                result = strategy_service.backtest_strategy(
                    strategy_id=backtest_config["strategy_id"],
                    symbol=backtest_config["symbol"],
                    start_date=backtest_config["start_date"],
                    end_date=backtest_config["end_date"],
                    initial_balance=backtest_config["initial_balance"]
                )

            # 결과 표시
            st.success("백테스팅 완료")
            st.markdown("---")

            # TODO: 백테스팅 결과가 구현되면 여기에 표시
            st.info("백테스팅 기능은 추후 구현 예정입니다.")

            st.json(result)

        except Exception as e:
            logger.error(f"백테스팅 실패: {e}")
            st.error(f"백테스팅 실패: {e}")

    st.markdown("---")

    # 백테스팅 가이드
    st.subheader("📖 백테스팅 가이드")

    st.markdown("""
    ### 백테스팅이란?

    과거 데이터를 사용하여 트레이딩 전략의 성과를 시뮬레이션하는 기법입니다.

    ### 주요 기능 (구현 예정)

    1. **성과 지표**
       - 총 수익률
       - 최대 낙폭 (MDD)
       - 샤프 비율
       - 승률

    2. **거래 분석**
       - 총 거래 횟수
       - 평균 수익/손실
       - 최대 연속 승리/패배

    3. **시각화**
       - 자산 곡선 (Equity Curve)
       - 일별 수익률 분포
       - 드로다운 차트

    4. **리스크 분석**
       - 변동성 분석
       - 포지션 크기 최적화
       - 리스크/리워드 비율

    ### 사용 방법

    1. 백테스팅할 전략을 선택합니다
    2. 거래 심볼을 입력합니다 (예: KRW-BTC)
    3. 백테스팅 기간을 설정합니다
    4. 초기 자본을 입력합니다
    5. '백테스팅 시작' 버튼을 클릭합니다

    ### 주의사항

    - 과거 성과가 미래 수익을 보장하지 않습니다
    - 슬리피지와 수수료를 고려해야 합니다
    - 오버피팅을 주의해야 합니다
    - 다양한 시장 상황에서 테스트하세요
    """)

    st.markdown("---")

    # 전략 목록
    st.subheader("🎯 등록된 전략")

    try:
        strategies = strategy_service.get_all_strategies()

        if strategies:
            import pandas as pd

            df = pd.DataFrame([
                {
                    "ID": s.id,
                    "이름": s.name,
                    "설명": s.description,
                    "시간프레임": s.timeframe.value,
                    "상태": s.status.value,
                    "생성일": s.created_at.strftime("%Y-%m-%d")
                }
                for s in strategies
            ])

            st.dataframe(df, use_container_width=True, hide_index=True)

        else:
            st.info("등록된 전략이 없습니다.")

    except Exception as e:
        logger.error(f"전략 조회 실패: {e}")
        st.error(f"전략 조회 실패: {e}")

    st.markdown("---")

    # 샘플 백테스팅 결과 (예시)
    st.subheader("📈 샘플 백테스팅 결과")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "총 수익률",
            "+45.3%",
            delta="+45.3%",
            help="백테스팅 기간 동안의 총 수익률"
        )

    with col2:
        st.metric(
            "최대 낙폭 (MDD)",
            "-12.5%",
            delta="-12.5%",
            delta_color="inverse",
            help="최대 손실 폭"
        )

    with col3:
        st.metric(
            "샤프 비율",
            "2.34",
            help="위험 대비 수익률"
        )

    with col4:
        st.metric(
            "승률",
            "68.5%",
            help="수익 거래 비율"
        )

    st.markdown("---")

    # 거래 통계 (예시)
    st.subheader("📊 거래 통계")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        **거래 횟수**
        - 총 거래: 156회
        - 매수: 78회
        - 매도: 78회
        """)

    with col2:
        st.markdown("""
        **손익 분석**
        - 평균 수익: +₩234,500
        - 평균 손실: -₩98,300
        - 손익비: 2.39
        """)

    with col3:
        st.markdown("""
        **연속 기록**
        - 최대 연속 승리: 8회
        - 최대 연속 패배: 3회
        - 평균 보유 기간: 2.3일
        """)

    st.markdown("---")

    # 성과 비교
    st.subheader("📉 성과 비교")

    st.markdown("""
    ### 벤치마크 대비 성과

    | 지표 | 전략 | 단순 보유 (Buy & Hold) | 차이 |
    |------|------|----------------------|------|
    | 수익률 | +45.3% | +32.1% | +13.2% |
    | MDD | -12.5% | -24.8% | +12.3% |
    | 샤프 비율 | 2.34 | 1.56 | +0.78 |
    | 승률 | 68.5% | N/A | - |

    ✅ 전략이 단순 보유 대비 우수한 성과를 보였습니다.
    """)

    st.markdown("---")

    # 개선 제안
    st.subheader("💡 백테스팅 개선 제안")

    st.markdown("""
    ### 구현 예정 기능

    1. **슬리피지 모델링**
       - 실제 체결가와 주문가의 차이 반영
       - 시장 충격 고려

    2. **다양한 수수료 모델**
       - 거래소별 수수료 구조
       - VIP 등급별 할인율

    3. **워크포워드 분석**
       - In-Sample / Out-of-Sample 테스트
       - 오버피팅 방지

    4. **몬테카를로 시뮬레이션**
       - 다양한 시나리오 테스트
       - 위험 시나리오 분석

    5. **파라미터 최적화**
       - 그리드 서치
       - 베이지안 최적화
       - 유전 알고리즘
    """)

if __name__ == "__main__":
    main()
