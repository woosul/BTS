#!/usr/bin/env python3
"""
WebSocket 클라이언트 테스트
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ WebSocket 연결 성공: {uri}")
            
            # 3번의 메시지를 받아서 출력
            for i in range(3):
                print(f"\n[{i+1}] 메시지 대기 중...")
                message = await websocket.recv()
                data = json.loads(message)
                print(f"📨 수신: {data['type']}")
                print(f"⏰ 시간: {data['timestamp']}")
                if 'data' in data:
                    print(f"📊 업비트: {list(data['data'].get('upbit', {}).keys())}")
                    print(f"💵 USD/KRW: {'OK' if data['data'].get('usd_krw') else 'NO'}")
                    print(f"🌍 글로벌: {'OK' if data['data'].get('global') else 'NO'}")
                    
    except ConnectionRefusedError:
        print("❌ WebSocket 서버에 연결할 수 없습니다")
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())