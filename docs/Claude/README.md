# Claude Code 히스토리 관리 가이드

## 개요

이 디렉토리에는 Claude Code의 전역 설정, 히스토리 관리 스크립트, 그리고 모든 프로젝트에서 공통으로 사용하는 리소스가 포함되어 있습니다.

## 전역 설정 vs 프로젝트별 설정

### 전역 설정 (모든 프로젝트 자동 적용)
- **위치**: `~/.claude/`
- **자동 로드**: 모든 프로젝트에서 자동으로 적용
- **용도**:
  - 공통 instruction (`CLAUDE.md`)
  - 공통 슬래시 커맨드 (`commands/`)
  - 히스토리 관리 스크립트
  - 환경변수 및 API 키

### 프로젝트별 설정
- **위치**: `<프로젝트 루트>/.claude/`
- **용도**: 해당 프로젝트에만 적용되는 설정
- **예시**: 프로젝트 특화 instruction, MCP 서버 등

## 파일 구조

### 전역 디렉토리 (~/.claude/)
```
~/.claude/
├── CLAUDE.md                 # 전역 instruction (모든 프로젝트 자동 로드) ⭐
├── commands/                 # 전역 슬래시 커맨드 (모든 프로젝트) ⭐
│   └── history-status.md
├── cleanup_history.sh        # 히스토리 정리 스크립트 (52KB)
├── cleanup_sessions.sh       # 세션 파일 정리 스크립트 (30MB+)
├── setup_cron.sh             # Cron Job 자동 설정 스크립트
├── settings.json             # Claude Code 사용자 전역 설정
├── .env                      # 환경변수 (API 키 등)
├── README.md                 # 이 가이드 파일
└── projects/                 # 프로젝트별 세션 파일 (30MB+)
    └── <프로젝트명>/
        └── *.jsonl           # 대화 세션 파일들

~/.claude.json                # Claude Code 내부 상태 (자동 관리)
~/.claude-backups/            # 백업 디렉토리
```

### 프로젝트 디렉토리 예시
```
/Users/denny/.../BTS/
└── .claude/
    ├── settings.json         # 프로젝트 공유 설정 (Git 커밋)
    └── settings.local.json   # 개인 설정 (Git 제외)
```

## 사용 방법

### 1. 가벼운 정리 (히스토리 목록)

**`~/.claude.json`** 파일만 정리 (약 52KB):

```bash
~/.claude/cleanup_history.sh
```

**실행 결과:**
- 각 프로젝트의 채팅 히스토리 목록을 최근 20개만 유지
- `/resume` 명령어에서 표시되는 대화 목록 정리
- 백업 자동 생성 (`~/.claude-backups/`)
- 30일 이상 된 백업 자동 삭제

⚠️ **주의:** 전체 대화 내용은 삭제되지 않음 (30MB+ 파일들)

---

### 2. 무거운 정리 (세션 파일) ⭐ 용량 절약

**`~/.claude/projects/`** 디렉토리 정리 (약 30MB+):

```bash
~/.claude/cleanup_sessions.sh
```

**실행 결과:**
- 30일 이상 된 대화 세션 파일 삭제
- 실제 디스크 공간 확보 (수 MB ~ 수십 MB)
- 프로젝트별 크기 통계 표시
- 삭제 전 확인 프롬프트

⚠️ **주의:** 삭제된 세션은 복구 불가능! `/resume`로 재개할 수 없음

---

### 3. 자동 실행 설정 (월 1회)

Cron Job을 설정하여 매월 1일 오전 2시에 자동 실행:

```bash
~/.claude/setup_cron.sh
```

**설정 후 확인:**
```bash
# Cron Job 목록 확인
crontab -l

# 로그 확인
tail -f ~/.claude/cleanup_history.log
```

---

### 4. Cron Job 제거

자동 실행을 중단하려면:

```bash
crontab -e
# 에디터에서 cleanup_history.sh 관련 줄 삭제 후 저장
```

또는:

```bash
crontab -l | grep -v cleanup_history.sh | crontab -
```

## 스크립트 상세

### cleanup_history.sh

**기능:**
1. ✅ `~/.claude.json` 백업 생성
2. ✅ 각 프로젝트의 히스토리를 최근 20개로 제한
3. ✅ 30일 이상 된 백업 자동 삭제
4. ✅ 정리 전/후 통계 표시
5. ✅ 색상 구분된 출력

**설정 커스터마이징:**

`cleanup_history.sh` 파일의 다음 라인을 수정하세요:

```bash
KEEP_HISTORY_COUNT=20  # 유지할 히스토리 개수 (기본: 20)
```

예시:
- 최근 10개만 유지: `KEEP_HISTORY_COUNT=10`
- 최근 50개 유지: `KEEP_HISTORY_COUNT=50`

### setup_cron.sh

**기능:**
1. ✅ Cron Job 자동 등록 (매월 1일 오전 2시)
2. ✅ 기존 등록 확인 및 중복 방지
3. ✅ 로그 파일 자동 설정

**실행 주기 변경:**

다른 주기로 실행하려면 `setup_cron.sh`의 `CRON_ENTRY` 라인을 수정:

```bash
# 기본: 매월 1일 오전 2시
CRON_ENTRY="0 2 1 * * $SCRIPT_PATH >> $LOG_PATH 2>&1"

# 예시: 매주 일요일 오전 3시
CRON_ENTRY="0 3 * * 0 $SCRIPT_PATH >> $LOG_PATH 2>&1"

# 예시: 매일 오전 4시
CRON_ENTRY="0 4 * * * $SCRIPT_PATH >> $LOG_PATH 2>&1"
```

**Cron 표현식 형식:**
```
분 시 일 월 요일 명령어
0  2  1  *  *   (매월 1일 오전 2시)
```

## 백업 관리

### 백업 위치
```
~/.claude-backups/
└── claude.json.YYYYMMDD_HHMMSS.bak
```

### 백업 복구

문제가 발생한 경우 백업에서 복구:

```bash
# 백업 목록 확인
ls -lht ~/.claude-backups/

# 가장 최근 백업으로 복구
cp ~/.claude-backups/claude.json.YYYYMMDD_HHMMSS.bak ~/.claude.json
```

### 백업 보관 정책

- **자동 삭제:** 30일 이상 된 백업
- **보관 기간 변경:** `cleanup_history.sh`에서 다음 라인 수정

```bash
# 30일 이상 -> 90일 이상으로 변경
find "$BACKUP_DIR" -name "claude.json.*.bak" -mtime +90 -delete
```

## 파일 설명

### ~/.claude.json
**Claude Code 내부 상태 파일** (자동 관리, 직접 편집 금지)

**저장 내용:**
- 프로젝트별 채팅 히스토리 목록 (제목만, 최근 20개)
- MCP 서버 설정 (프로젝트별로 저장됨)
- 사용자 인증 정보
- 앱 상태 및 캐시

⚠️ **중요**: 이 파일은 대화 목록만 저장하며, 실제 대화 내용은 `~/.claude/projects/` 디렉토리에 저장됩니다.

### ~/.claude/settings.json
**사용자 전역 설정** (직접 편집 가능)

**저장 내용:**
- 상태 라인 커스터마이징
- 모델 기본값
- 환경변수
- 권한 설정 (permissions)
- 훅(hooks) 설정

**예시:**
```json
{
  "statusLine": {
    "type": "command",
    "command": "..."
  },
  "alwaysThinkingEnabled": false,
  "permissions": {
    "allow": ["Bash(git:*)", "Read(**/*.py)"],
    "deny": ["Bash(rm:*)"]
  }
}
```

### ~/.claude/.env
**환경변수 파일** (민감정보 보관)

**저장 내용:**
- API 키/토큰
- 민감한 환경변수

**예시:**
```bash
FIGMA_PERSONAL_ACCESS_TOKEN=figd_xxx...
UPBIT_API_KEY=xxx...
```

⚠️ **주의:** 이 파일은 절대 Git에 커밋하지 마세요!

## 트러블슈팅

### jq 설치 오류

```bash
❌ jq가 설치되어 있지 않습니다.
```

**해결:**
```bash
brew install jq
```

### 권한 오류

```bash
❌ Permission denied
```

**해결:**
```bash
chmod +x ~/.claude/cleanup_history.sh
chmod +x ~/.claude/setup_cron.sh
```

### Cron Job이 실행되지 않음

**확인:**
1. Cron Job 등록 확인: `crontab -l`
2. 로그 확인: `tail -f ~/.claude/cleanup_history.log`
3. 수동 실행 테스트: `~/.claude/cleanup_history.sh`

### 백업 복구 실패

```bash
# 현재 파일 백업
cp ~/.claude.json ~/.claude.json.broken

# 특정 백업으로 복구
cp ~/.claude-backups/claude.json.YYYYMMDD_HHMMSS.bak ~/.claude.json

# Claude Code 재시작
```

## FAQ

### Q: 전역 설정과 프로젝트별 설정의 차이는?
**A:**
- **전역** (`~/.claude/`): 모든 프로젝트에 자동 적용 (CLAUDE.md, 슬래시 커맨드 등)
- **프로젝트별** (`.claude/`): 해당 프로젝트에만 적용 (프로젝트 특화 설정)

### Q: 새 프로젝트를 만들 때 설정을 복사해야 하나요?
**A:** 아니요! 전역 설정(`~/.claude/CLAUDE.md`, 슬래시 커맨드 등)은 자동으로 모든 프로젝트에 적용됩니다.

### Q: 히스토리가 자동으로 다시 쌓이나요?
**A:** 네, Claude Code를 사용하면서 새로운 대화가 계속 기록됩니다. 주기적인 정리가 필요합니다.

### Q: 백업은 얼마나 보관하나요?
**A:** 기본적으로 30일간 보관하며, 30일 이상 된 백업은 자동 삭제됩니다.

### Q: cleanup_history.sh vs cleanup_sessions.sh 차이는?
**A:**
- **cleanup_history.sh**: `~/.claude.json`만 정리 (52KB, 대화 목록)
- **cleanup_sessions.sh**: `~/.claude/projects/` 정리 (30MB+, 실제 대화 내용)

### Q: 정리하면 대화 내용이 완전히 사라지나요?
**A:**
- **cleanup_history.sh**: 대화 목록만 정리, 내용은 유지
- **cleanup_sessions.sh**: 오래된 대화 내용 완전 삭제 (복구 불가)

### Q: MCP 서버 설정도 삭제되나요?
**A:** 아니요, MCP 서버 설정은 유지됩니다. 히스토리만 정리됩니다.

### Q: /history-status는 어떻게 모든 프로젝트에서 사용 가능한가요?
**A:** `~/.claude/commands/` 디렉토리의 슬래시 커맨드는 전역으로 적용되어 모든 프로젝트에서 자동으로 사용할 수 있습니다.

## 참고 자료

- [Claude Code 공식 문서](https://docs.claude.com/en/docs/claude-code)
- [jq 매뉴얼](https://jqlang.github.io/jq/manual/)
- [Cron 표현식 가이드](https://crontab.guru/)

## 버전 정보

- **버전:** 1.0.0
- **최종 수정:** 2025-10-12
- **작성자:** Claude Code Assistant
