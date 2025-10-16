#!/usr/bin/env python3
"""
테스트: pyupbit.get_orderbook() 동작 확인
"""
import pyupbit

# 테스트할 심볼들
test_symbols = ["KRW-TRUMP", "KRW-ETH", "KRW-SOL"]

print("=" * 80)
print("pyupbit.get_orderbook() 테스트")
print("=" * 80)

for symbol in test_symbols:
    print(f"\n{symbol} 테스트:")
    print("-" * 40)
    
    # 단일 심볼로 호출
    result = pyupbit.get_orderbook(symbol)
    print(f"  반환 타입: {type(result)}")
    print(f"  반환 값: {result}")
    
    if isinstance(result, list):
        print(f"  리스트 길이: {len(result)}")
        if len(result) > 0:
            print(f"  첫 항목 타입: {type(result[0])}")
            print(f"  첫 항목 키: {result[0].keys() if isinstance(result[0], dict) else 'N/A'}")

print("\n" + "=" * 80)
print("배치 호출 테스트 (리스트로 전달)")
print("=" * 80)

# 리스트로 한 번에 조회
batch_result = pyupbit.get_orderbook(test_symbols)
print(f"  반환 타입: {type(batch_result)}")
print(f"  반환 값 (첫 100자): {str(batch_result)[:100]}...")

if isinstance(batch_result, list):
    print(f"  리스트 길이: {len(batch_result)}")
    if len(batch_result) > 0:
        print(f"  첫 항목: {batch_result[0]}")
