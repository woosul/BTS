#!/bin/bash
# Real-time log monitoring script for BTS Streamlit app

echo "======================================"
echo "BTS Streamlit 실시간 로그 모니터링"
echo "======================================"
echo ""
echo "Ctrl+C로 종료"
echo ""

# Find the log file
LOG_FILE=""
if [ -f "presentation/streamlit.log" ]; then
    LOG_FILE="presentation/streamlit.log"
elif [ -f "streamlit.log" ]; then
    LOG_FILE="streamlit.log"
else
    echo "⚠️  로그 파일을 찾을 수 없습니다."
    echo "Streamlit이 실행 중인지 확인하세요."
    exit 1
fi

echo "📄 로그 파일: $LOG_FILE"
echo ""
echo "--------------------------------------"
echo ""

# Tail the log file with grep filtering for important keywords
tail -f "$LOG_FILE" | grep --line-buffered -E "(업비트|Upbit|upbit|스크래핑|Playwright|ERROR|Exception|Dashboard|market_index)"
