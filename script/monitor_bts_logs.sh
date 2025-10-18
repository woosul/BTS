#!/bin/bash
# BTS 로그 모니터링 스크립트
# 실시간으로 중요한 이벤트만 필터링해서 표시

LOG_FILE="/Users/denny/Gaia/30_Share/33_DEVELOPMENT/BTS/logs/bts.log"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  BTS 실시간 로그 모니터링"
echo "=========================================="
echo "모니터링 대상:"
echo "  - CoinGecko API 호출 상태 (429 에러 포함)"
echo "  - 글로벌 데이터 수집 및 저장"
echo "  - BTC 도미넌스 값"
echo "  - WebSocket 업데이트"
echo ""
echo "종료: Ctrl+C"
echo "=========================================="
echo ""

# 로그 파일 실시간 모니터링
tail -f "$LOG_FILE" | while read line; do
    # 타임스탬프 추출
    timestamp=$(echo "$line" | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")

    # 429 에러 (빨간색, 굵게)
    if echo "$line" | grep -q "429"; then
        echo -e "${RED}[ERROR 429] $timestamp - CoinGecko API Rate Limit 초과!${NC}"
        echo "$line" | grep -oE "https://[^ ]+"
        echo ""

    # CoinGecko 성공 (초록색)
    elif echo "$line" | grep -qE "(글로벌 업데이터.*완료|글로벌 지수 저장 완료)"; then
        duration=$(echo "$line" | grep -oE "[0-9]+\.[0-9]+초")
        echo -e "${GREEN}[SUCCESS] $timestamp - 글로벌 데이터 수집 성공 (소요: $duration)${NC}"

    # 글로벌 데이터 내용 (파란색)
    elif echo "$line" | grep -q "글로벌 데이터 내용"; then
        market_cap=$(echo "$line" | grep -oE "시가총액=\\\$[0-9,]+" | grep -oE "[0-9,]+")
        btc_dom=$(echo "$line" | grep -oE "BTC도미넌스=[0-9]+\.[0-9]+%" | grep -oE "[0-9]+\.[0-9]+")

        if [ "$btc_dom" = "0.00" ]; then
            echo -e "${RED}[WARNING] $timestamp - BTC 도미넌스 0.00% 감지! (API 실패)${NC}"
        else
            echo -e "${BLUE}[DATA] $timestamp - 시가총액: \$$market_cap | BTC 도미넌스: ${btc_dom}%${NC}"
        fi

    # 빈 데이터 저장 방지 (노란색)
    elif echo "$line" | grep -q "DB 업데이트 스킵"; then
        echo -e "${YELLOW}[PROTECTED] $timestamp - 빈 데이터 감지, DB 업데이트 스킵 (이전 데이터 보존)${NC}"

    # WebSocket 전송 (청록색)
    elif echo "$line" | grep -q "WebSocket 데이터 전송 완료"; then
        echo -e "${CYAN}[WEBSOCKET] $timestamp - 클라이언트에 데이터 전송 완료${NC}"

    # 업비트 데이터 수집 성공 (초록색, 간결)
    elif echo "$line" | grep -q "업비트 업데이터.*완료"; then
        duration=$(echo "$line" | grep -oE "[0-9]+\.[0-9]+초")
        echo -e "${GREEN}[UPBIT] $timestamp - 업비트 데이터 수집 완료 (소요: $duration)${NC}"

    # Dashboard 조회 (자주색)
    elif echo "$line" | grep -q "Dashboard.*BTC 도미넌스"; then
        btc_dom=$(echo "$line" | grep -oE "[0-9]+\.[0-9]+" | tail -1)
        echo -e "${MAGENTA}[DASHBOARD] $timestamp - BTC 도미넌스: ${btc_dom}%${NC}"

    # 에러 메시지 (빨간색)
    elif echo "$line" | grep -qE "ERROR|실패"; then
        error_msg=$(echo "$line" | grep -oE "ERROR.*$" | cut -c1-100)
        echo -e "${RED}[ERROR] $timestamp - $error_msg${NC}"
    fi
done
