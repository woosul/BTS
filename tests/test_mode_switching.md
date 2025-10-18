# 모드 전환 테스트 결과

## 현재 상태 (23:47)
- Dashboard 클라이언트 연결됨: `[('::1', 60244, 0, 0)]`
- 글로벌 업데이트 간격: **3초** (Dashboard 모드)
- 업비트 업데이트 간격: **6초** (Dashboard 모드)

## 테스트 시나리오
1. Dashboard 닫기 → 백그라운드 모드로 전환 확인
2. Dashboard 다시 열기 → Dashboard 모드로 복귀 확인

## 예상 결과
- **Dashboard 모드**: 3초/6초 간격
- **백그라운드 모드**: 사용자 설정값 (기본 60초) 또는 config.BACKGROUND_UPDATE_INTERVAL

## 테스트 진행
- [ ] Dashboard 브라우저 탭 닫기
- [ ] 로그에서 간격 변경 확인 (3초 → 60초+)
- [ ] Dashboard 다시 열기
- [ ] 로그에서 간격 복귀 확인 (60초+ → 3초)
