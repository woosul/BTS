"""
BTS 메트릭 컴포넌트

주요 지표 표시 UI 컴포넌트
"""
import streamlit as st
from decimal import Decimal
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from core.models import WalletResponse, OrderResponse, TradeResponse


def render_ai_evaluation_card(
    evaluation: Dict,
    title: str = "AI 평가"
) -> None:
    """
    AI 평가 결과 카드

    Args:
        evaluation: AI 평가 결과
        title: 카드 제목
    """
    recommendation = evaluation.get("recommendation", "hold")
    confidence = evaluation.get("confidence", 50)
    reasoning = evaluation.get("reasoning", "N/A")
    warnings = evaluation.get("warnings", "")

    # 추천에 따른 색상
    rec_color = {
        "buy": "#4ECDC4",
        "sell": "#FF6B6B",
        "hold": "#FFE66D"
    }.get(recommendation, "#9ca3af")

    rec_text = {
        "buy": "매수",
        "sell": "매도",
        "hold": "보류"
    }.get(recommendation, recommendation.upper())

    # Fallback 정보
    fallback_used = evaluation.get("_fallback_used", False)
    model_used = evaluation.get("_model_used", "")

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #404040;
        margin-bottom: 12px;
    ">
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        ">
            <div style="font-size: 1rem; font-weight: 600; color: #FAFAFA;">
                {title}
            </div>
            <div style="
                background-color: {rec_color};
                color: #1E1E1E;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: 700;
                font-size: 0.9rem;
            ">
                {rec_text}
            </div>
        </div>
        <div style="margin-bottom: 8px;">
            <div style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 4px;">
                확신도
            </div>
            <div style="
                background-color: #262730;
                border-radius: 4px;
                height: 24px;
                position: relative;
                overflow: hidden;
            ">
                <div style="
                    background: linear-gradient(90deg, {rec_color} 0%, {rec_color}AA 100%);
                    height: 100%;
                    width: {confidence}%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #FAFAFA;
                    font-size: 0.75rem;
                    font-weight: 600;
                ">
                    {confidence}%
                </div>
            </div>
        </div>
        <div style="margin-bottom: 8px;">
            <div style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 4px;">
                분석
            </div>
            <div style="font-size: 0.85rem; color: #FAFAFA; line-height: 1.4;">
                {reasoning}
            </div>
        </div>
        {"<div style='margin-bottom: 8px; background-color: #00CCAC20; border-left: 3px solid #00CCAC; padding: 12px; border-radius: 4px;'><div style='font-size: 0.75rem; color: #00CCAC; margin-bottom: 4px; font-weight: 600;'>⚠️ 주의사항</div><div style='font-size: 0.85rem; color: #FAFAFA; line-height: 1.4;'>" + warnings + "</div></div>" if warnings else ""}
        {"<div style='font-size: 0.7rem; color: #9ca3af; margin-top: 8px;'>🔄 Fallback 모델 사용: " + model_used + "</div>" if fallback_used else ""}
    </div>
    """, unsafe_allow_html=True)


def display_wallet_metrics(wallet: WalletResponse) -> None:
    """
    지갑 메트릭 표시

    Args:
        wallet: 지갑 정보
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="원화 잔고",
            value=f"₩{wallet.balance_krw:,.0f}",
            help="현재 보유 원화"
        )

    with col2:
        st.metric(
            label="총 자산",
            value=f"₩{wallet.total_value_krw:,.0f}",
            help="원화 + 코인 평가액"
        )

    with col3:
        # 초기 자본 대비 수익 (임시로 1000만원 가정)
        initial_balance = Decimal("10000000")
        profit = wallet.total_value_krw - initial_balance
        profit_rate = (profit / initial_balance) * 100 if initial_balance > 0 else Decimal("0")

        st.metric(
            label="수익률",
            value=f"{profit_rate:+.2f}%",
            delta=f"₩{profit:+,.0f}",
            delta_color="normal",
            help="초기 자본 대비 수익률"
        )

    with col4:
        st.metric(
            label="지갑 유형",
            value="가상" if wallet.wallet_type.value == "virtual" else "실거래",
            help="지갑 타입"
        )


def display_trading_metrics(
    total_trades: int,
    win_rate: float,
    avg_profit: Decimal,
    total_profit: Decimal
) -> None:
    """
    트레이딩 메트릭 표시

    Args:
        total_trades: 총 거래 횟수
        win_rate: 승률 (%)
        avg_profit: 평균 수익
        total_profit: 총 수익
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="총 거래",
            value=f"{total_trades}회",
            help="총 거래 횟수"
        )

    with col2:
        st.metric(
            label="승률",
            value=f"{win_rate:.1f}%",
            help="수익 거래 비율"
        )

    with col3:
        st.metric(
            label="평균 수익",
            value=f"₩{avg_profit:+,.0f}",
            delta_color="off",
            help="거래당 평균 수익"
        )

    with col4:
        st.metric(
            label="총 수익",
            value=f"₩{total_profit:+,.0f}",
            delta_color="normal" if total_profit >= 0 else "inverse",
            help="누적 수익"
        )


def display_strategy_metrics(
    total_strategies: int,
    active_strategies: int,
    total_signals: int,
    signal_accuracy: float
) -> None:
    """
    전략 메트릭 표시

    Args:
        total_strategies: 총 전략 수
        active_strategies: 활성 전략 수
        total_signals: 총 시그널 수
        signal_accuracy: 시그널 정확도 (%)
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="총 전략",
            value=f"{total_strategies}개",
            help="등록된 전략 수"
        )

    with col2:
        st.metric(
            label="활성 전략",
            value=f"{active_strategies}개",
            help="현재 활성화된 전략"
        )

    with col3:
        st.metric(
            label="시그널",
            value=f"{total_signals}개",
            help="생성된 시그널 수"
        )

    with col4:
        st.metric(
            label="정확도",
            value=f"{signal_accuracy:.1f}%",
            help="시그널 정확도"
        )


def display_market_metrics(
    current_price: Decimal,
    price_change_24h: Decimal,
    volume_24h: Decimal,
    market_cap: Optional[Decimal] = None
) -> None:
    """
    시장 메트릭 표시

    Args:
        current_price: 현재가
        price_change_24h: 24시간 변동률 (%)
        volume_24h: 24시간 거래량
        market_cap: 시가총액 (선택)
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="현재가",
            value=f"₩{current_price:,.0f}",
            help="실시간 가격"
        )

    with col2:
        st.metric(
            label="24h 변동",
            value=f"{price_change_24h:+.2f}%",
            delta=f"{price_change_24h:+.2f}%",
            delta_color="normal",
            help="24시간 가격 변동률"
        )

    with col3:
        st.metric(
            label="24h 거래량",
            value=f"₩{volume_24h:,.0f}",
            help="24시간 거래량"
        )

    with col4:
        if market_cap:
            st.metric(
                label="시가총액",
                value=f"₩{market_cap:,.0f}",
                help="시가총액"
            )
        else:
            st.metric(
                label="시가총액",
                value="N/A",
                help="시가총액 정보 없음"
            )


def display_order_status_badge(status: str) -> None:
    """
    주문 상태 뱃지 표시

    Args:
        status: 주문 상태
    """
    status_text = {
        "pending": "대기",
        "submitted": "제출",
        "filled": "체결",
        "cancelled": "취소",
        "rejected": "거부",
        "partial": "부분체결"
    }

    text = status_text.get(status, status)

    st.markdown(f"**{text}**")


def display_signal_badge(signal: str, confidence: float) -> None:
    """
    시그널 뱃지 표시

    Args:
        signal: 시그널 (buy/sell/hold)
        confidence: 확신도 (0~1)
    """
    signal_text = {
        "buy": "매수",
        "sell": "매도",
        "hold": "관망"
    }

    text = signal_text.get(signal, signal)
    confidence_pct = confidence * 100

    st.markdown(f"**{text}** ({confidence_pct:.1f}%)")


def display_performance_summary(
    trades: List[TradeResponse],
    days: int = 30
) -> None:
    """
    성과 요약 표시

    Args:
        trades: 거래 내역
        days: 조회 기간 (일)
    """
    if not trades:
        st.info("거래 내역이 없습니다.")
        return

    # 기간 필터링
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered_trades = [
        t for t in trades
        if t.created_at >= cutoff_date
    ]

    if not filtered_trades:
        st.info(f"최근 {days}일 거래 내역이 없습니다.")
        return

    # 통계 계산
    total_trades = len(filtered_trades)
    buy_trades = [t for t in filtered_trades if t.side.value == "buy"]
    sell_trades = [t for t in filtered_trades if t.side.value == "sell"]

    total_buy_amount = sum(t.total_amount + t.fee for t in buy_trades)
    total_sell_amount = sum(t.total_amount - t.fee for t in sell_trades)

    profit = total_sell_amount - total_buy_amount
    profit_rate = (profit / total_buy_amount * 100) if total_buy_amount > 0 else Decimal("0")

    # 승률 계산 (간단한 방식: 매도가 > 평균 매수가)
    wins = 0
    if buy_trades:
        avg_buy_price = sum(t.price for t in buy_trades) / len(buy_trades)
        wins = sum(1 for t in sell_trades if t.price > avg_buy_price)

    win_rate = (wins / len(sell_trades) * 100) if sell_trades else 0

    # 표시
    st.subheader(f"최근 {days}일 성과")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "총 거래",
            f"{total_trades}회",
            help=f"매수 {len(buy_trades)}회, 매도 {len(sell_trades)}회"
        )

    with col2:
        st.metric(
            "수익률",
            f"{profit_rate:+.2f}%",
            delta=f"₩{profit:+,.0f}",
            delta_color="normal"
        )

    with col3:
        st.metric(
            "승률",
            f"{win_rate:.1f}%",
            help="수익 거래 비율"
        )


def display_asset_table(holdings: List[Dict]) -> None:
    """
    자산 테이블 표시

    Args:
        holdings: 보유 자산 목록
            [{"symbol": str, "quantity": Decimal, "avg_price": Decimal,
              "current_price": Decimal, "profit_loss": Decimal, "profit_loss_rate": Decimal}]
    """
    if not holdings:
        st.info("보유 자산이 없습니다.")
        return

    import pandas as pd

    df = pd.DataFrame([
        {
            "코인": h["symbol"],
            "수량": f"{float(h['quantity']):.8f}",
            "평균단가": f"₩{float(h['avg_price']):,.0f}",
            "현재가": f"₩{float(h['current_price']):,.0f}",
            "평가금액": f"₩{float(h['quantity'] * h['current_price']):,.0f}",
            "손익": f"₩{float(h['profit_loss']):+,.0f}",
            "수익률": f"{float(h['profit_loss_rate']):+.2f}%"
        }
        for h in holdings
    ])

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


def display_recent_trades_table(
    trades: List[TradeResponse],
    limit: int = 10
) -> None:
    """
    최근 거래 내역 테이블 표시

    Args:
        trades: 거래 내역
        limit: 표시 개수
    """
    if not trades:
        st.info("거래 내역이 없습니다.")
        return

    import pandas as pd

    df = pd.DataFrame([
        {
            "시간": t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "심볼": t.symbol,
            "구분": "매수" if t.side.value == "buy" else "매도",
            "수량": f"{float(t.quantity):.8f}",
            "가격": f"₩{float(t.price):,.0f}",
            "금액": f"₩{float(t.total_amount):,.0f}",
            "수수료": f"₩{float(t.fee):,.0f}"
        }
        for t in trades[:limit]
    ])

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
