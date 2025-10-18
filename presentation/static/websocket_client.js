/**
 * Dashboard WebSocket Client (개선된 버전)
 *
 * 기능:
 * - 업비트 지수 실시간 업데이트
 * - 글로벌 시장 지수 실시간 업데이트
 * - 개별 코인 추세 실시간 업데이트
 * - 자동 재연결
 */

// 타임스탬프 헬퍼 함수
function getTimestamp() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const ms = String(now.getMilliseconds()).padStart(3, '0');
    return hours + ':' + minutes + ':' + seconds + '.' + ms;
}

console.log('[' + getTimestamp() + '] 초기화 시작');

let ws = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function connectWebSocket() {
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
        console.log('[' + getTimestamp() + '] 이미 연결 중 또는 연결됨');
        return;
    }

    // WS_URL은 Dashboard.py에서 전역 변수로 설정됨
    const wsUrl = typeof WS_URL !== 'undefined' ? WS_URL : 'ws://localhost:8765';
    console.log('[' + getTimestamp() + '] 연결 시도 #' + (reconnectAttempts + 1) + ': ' + wsUrl);
    ws = new WebSocket(wsUrl);

    ws.onopen = function() {
        console.log('[' + getTimestamp() + '] 연결 성공');
        reconnectAttempts = 0;

        // 클라이언트 정보 전송
        ws.send(JSON.stringify({
            type: 'client_info',
            page: 'dashboard',
            timestamp: new Date().toISOString()
        }));

        // 최신 데이터 요청
        ws.send('get_latest');
    };

    ws.onmessage = function(event) {
        if (event.data === 'pong') {
            return;  // pong은 로그 없이 처리
        }

        try {
            const message = JSON.parse(event.data);
            console.log('[' + getTimestamp() + '] 수신:', message.type);

            if (message.type === 'indices_updated' && message.data) {
                updateDashboard(message.data);
            }
        } catch (e) {
            console.error('[' + getTimestamp() + '] JSON 파싱 실패:', e);
        }
    };

    ws.onclose = function() {
        console.log('[' + getTimestamp() + '] 연결 종료');
        ws = null;

        if (reconnectAttempts < maxReconnectAttempts) {
            const delay = 3000 * Math.pow(1.5, reconnectAttempts);
            console.log('[' + getTimestamp() + '] ' + delay + 'ms 후 재연결 시도');
            setTimeout(function() {
                reconnectAttempts++;
                connectWebSocket();
            }, delay);
        }
    };

    ws.onerror = function(error) {
        console.error('[' + getTimestamp() + '] 연결 오류:', error);
    };
}

function updateDashboard(data) {
    let updateCount = 0;

    // iframe 내부에서 실행되므로 parent.document로 접근
    const doc = window.parent ? window.parent.document : document;

    // ===== 타임스탬프 업데이트 =====
    const timestampElement = doc.getElementById('last-update-time');
    if (timestampElement) {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');

        timestampElement.textContent = year + '-' + month + '-' + day + ' ' + hours + ':' + minutes + ':' + seconds;
        updateCount++;
    }

    // ===== 업비트 지수 업데이트 =====
    if (data.upbit) {
        ['ubci', 'ubmi', 'ub10', 'ub30'].forEach(function(key) {
            if (data.upbit[key] && data.upbit[key].value !== undefined) {
                const card = doc.getElementById(key + '-card');
                if (card) {
                    const valueSpan = card.querySelector('.metric-value');
                    const deltaSpan = card.querySelector('.metric-delta');

                    if (valueSpan) {
                        const value = data.upbit[key].value || 0;
                        valueSpan.textContent = value > 0 ?
                            value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : 'N/A';

                        // 변동률 업데이트
                        if (deltaSpan && data.upbit[key].change_rate !== undefined) {
                            const changeRate = data.upbit[key].change_rate || 0;
                            if (changeRate > 0) {
                                deltaSpan.innerHTML = '<span style="font-size: 8px;">▲</span> ' + Math.abs(changeRate).toFixed(2) + '%';
                                deltaSpan.style.color = '#ef5350';
                                valueSpan.style.color = '#ef5350';
                            } else if (changeRate < 0) {
                                deltaSpan.innerHTML = '<span style="font-size: 8px;">▼</span> ' + Math.abs(changeRate).toFixed(2) + '%';
                                deltaSpan.style.color = '#42a5f5';
                                valueSpan.style.color = '#42a5f5';
                            } else {
                                deltaSpan.innerHTML = '<span style="font-size: 8px;">-</span> 0.00%';
                                deltaSpan.style.color = '#9e9e9e';
                                valueSpan.style.color = 'white';
                            }
                        }

                        updateCount++;
                    }
                }
            }
        });
    }

    // ===== USD/KRW 환율 업데이트 =====
    if (data.usd_krw && data.usd_krw.value !== undefined) {
        const card = doc.getElementById('usd-krw-card');
        if (card) {
            const valueSpan = card.querySelector('.metric-value');
            if (valueSpan) {
                const value = data.usd_krw.value || 0;
                valueSpan.textContent = value > 0 ?
                    '₩' + value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : 'N/A';
                updateCount++;
            }
        }
    }

    // ===== 글로벌 시장 지수 업데이트 =====
    if (data.global) {
        // 총 시가총액
        if (data.global.total_market_cap_usd) {
            const card = doc.getElementById('global-market-cap-card');
            if (card) {
                const valueSpan = card.querySelector('.metric-value');
                if (valueSpan) {
                    const marketCapTrillion = data.global.total_market_cap_usd / 1_000_000_000_000;
                    valueSpan.textContent = '$' + marketCapTrillion.toFixed(2) + 'T';
                    updateCount++;
                }
            }
        }

        // 24h 거래량
        if (data.global.total_volume_usd) {
            const card = doc.getElementById('global-volume-card');
            if (card) {
                const valueSpan = card.querySelector('.metric-value');
                if (valueSpan) {
                    const volumeBillion = data.global.total_volume_usd / 1_000_000_000;
                    valueSpan.textContent = '$' + volumeBillion.toFixed(1) + 'B';
                    updateCount++;
                }
            }
        }

        // BTC 도미넌스
        if (data.global.btc_dominance !== undefined) {
            const card = doc.getElementById('btc-dominance-card');
            if (card) {
                const valueSpan = card.querySelector('.metric-value');
                if (valueSpan) {
                    valueSpan.textContent = data.global.btc_dominance.toFixed(2) + '%';
                    updateCount++;
                }
            }
        }
    }

    // ===== 개별 코인 추세 업데이트 =====
    if (data.top_coins && Array.isArray(data.top_coins) && data.top_coins.length > 0) {
        // KRW 토글 상태 확인 (data-krw attribute 사용)
        const currencyModeElement = doc.getElementById('currency-mode');
        const isKRWMode = currencyModeElement ? currencyModeElement.getAttribute('data-krw') === 'True' : false;

        // ID 기반으로 카드 찾기 (예: coin-btc-card, coin-eth-card)
        for (let i = 0; i < Math.min(5, data.top_coins.length); i++) {
            const coin = data.top_coins[i];
            const symbol = coin.symbol ? coin.symbol.toLowerCase() : null;

            if (symbol) {
                const cardId = 'coin-' + symbol + '-card';
                const card = doc.getElementById(cardId);

                if (card) {
                    const valueSpan = card.querySelector('.metric-value');
                    const deltaSpan = card.querySelector('.metric-delta');

                    if (valueSpan) {
                        // 서버에서 전송한 포맷팅된 문자열 사용
                        const priceStr = isKRWMode ? 
                            (coin.price_krw_formatted || '₩N/A') : 
                            (coin.price_usd_formatted || '$N/A');
                        
                        valueSpan.textContent = priceStr;

                        if (deltaSpan && coin.price_change_percentage_7d !== undefined) {
                            const change = coin.price_change_percentage_7d || 0;
                            if (change > 0) {
                                deltaSpan.innerHTML = '<span style="font-size: 8px;">▲</span> ' + Math.abs(change).toFixed(1) + '%';
                                deltaSpan.style.color = '#ef5350';
                                valueSpan.style.color = '#ef5350';
                            } else if (change < 0) {
                                deltaSpan.innerHTML = '<span style="font-size: 8px;">▼</span> ' + Math.abs(change).toFixed(1) + '%';
                                deltaSpan.style.color = '#42a5f5';
                                valueSpan.style.color = '#42a5f5';
                            } else {
                                deltaSpan.innerHTML = '<span style="font-size: 8px;">-</span> 0.0%';
                                deltaSpan.style.color = '#9e9e9e';
                                valueSpan.style.color = 'white';
                            }
                        }

                        updateCount++;
                    }
                }
            }
        }
    }

    console.log('[' + getTimestamp() + '] 대시보드 업데이트 완료:', updateCount + '개 요소');
}

// 자동 연결 시작 (페이지 로드 후 1초 대기)
setTimeout(function() {
    console.log('[' + getTimestamp() + '] 자동 연결 시작...');
    connectWebSocket();
}, 1000);

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    if (ws) {
        ws.close();
    }
});
