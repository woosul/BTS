# Claude Code 설정 동기화 가이드

## 개요

두 대 이상의 Mac에서 Claude Code 설정을 동일하게 유지하는 방법을 설명합니다.

---

## 🔄 동기화가 필요한 파일

### 전역 설정 파일들 (~/.claude/)

```
~/.claude/
├── CLAUDE.md                 # 전역 instruction ⭐
├── commands/                 # 전역 슬래시 커맨드 ⭐
│   └── history-status.md
├── cleanup_history.sh        # 히스토리 정리 스크립트 ⭐
├── cleanup_sessions.sh       # 세션 정리 스크립트 ⭐
├── setup_cron.sh             # Cron 설정 스크립트 ⭐
├── settings.json             # 사용자 전역 설정 ⭐
├── .env                      # 환경변수/API 키 ⭐
└── README.md                 # 가이드 문서 ⭐
```

### 동기화하면 안 되는 파일들

```
~/.claude/
├── .claude.json              # ❌ 머신별 상태 (동기화 금지)
├── projects/                 # ❌ 대화 세션 파일 (동기화 금지)
├── history.jsonl             # ❌ 전역 히스토리 (동기화 금지)
└── file-history/             # ❌ 파일 변경 이력 (동기화 금지)
```

---

## 방법 1: Git 저장소로 관리 (추천) ⭐

### 장점
- ✅ 변경 이력 추적 가능
- ✅ 양방향 동기화
- ✅ 충돌 해결 가능
- ✅ 자동화 용이

### 단계별 가이드

#### 집 Mac (초기 설정)

```bash
# 1. Git 저장소 초기화
cd ~/.claude
git init

# 2. .gitignore 생성
cat > .gitignore << 'EOF'
# 동기화 제외 파일
.claude.json
projects/
history.jsonl
file-history/
shell-snapshots/
statsig/
todos/
debug/
ide/

# 백업 제외
*-backups/

# 로그 파일
*.log
EOF

# 3. 파일 추가
git add CLAUDE.md
git add commands/
git add cleanup_history.sh
git add cleanup_sessions.sh
git add setup_cron.sh
git add settings.json
git add .env
git add README.md
git add SYNC_GUIDE.md
git add .gitignore

# 4. 커밋
git commit -m "Initial Claude Code settings"

# 5. GitHub 저장소 생성 후 연결 (Private 저장소 권장)
git remote add origin git@github.com:YOUR_USERNAME/claude-settings.git
git branch -M main
git push -u origin main
```

#### 회사 Mac (동기화)

```bash
# 1. 기존 설정 백업 (있다면)
mv ~/.claude ~/.claude.backup.$(date +%Y%m%d)

# 2. 저장소 클론
git clone git@github.com:YOUR_USERNAME/claude-settings.git ~/.claude

# 3. 스크립트 실행 권한 부여
chmod +x ~/.claude/cleanup_history.sh
chmod +x ~/.claude/cleanup_sessions.sh
chmod +x ~/.claude/setup_cron.sh

# 4. 완료!
```

#### 양방향 동기화 (변경 사항 반영)

**집 Mac에서 변경 후:**
```bash
cd ~/.claude
git add -A
git commit -m "Update settings"
git push
```

**회사 Mac에서 가져오기:**
```bash
cd ~/.claude
git pull
```

---

## 방법 2: iCloud Drive 동기화

### 장점
- ✅ 자동 동기화
- ✅ 설정 간단
- ❌ 충돌 해결 어려움
- ❌ 버전 관리 없음

### 단계별 가이드

#### 집 Mac (초기 설정)

```bash
# 1. iCloud Drive에 디렉토리 생성
mkdir -p ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings

# 2. 파일 복사
cp ~/.claude/CLAUDE.md ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/
cp -r ~/.claude/commands ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/
cp ~/.claude/cleanup_history.sh ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/
cp ~/.claude/cleanup_sessions.sh ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/
cp ~/.claude/setup_cron.sh ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/
cp ~/.claude/settings.json ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/
cp ~/.claude/.env ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/
cp ~/.claude/README.md ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/
cp ~/.claude/SYNC_GUIDE.md ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/

# 3. 심볼릭 링크 생성 (자동 동기화)
mv ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak
ln -s ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/CLAUDE.md ~/.claude/CLAUDE.md
# (다른 파일들도 동일하게)
```

#### 회사 Mac (동기화)

```bash
# iCloud Drive가 동기화되면 자동으로 파일 생성됨
# 심볼릭 링크 생성
ln -s ~/Library/Mobile\ Documents/com~apple~CloudDocs/ClaudeSettings/CLAUDE.md ~/.claude/CLAUDE.md
# (다른 파일들도 동일하게)
```

---

## 방법 3: rsync로 수동 동기화

### 장점
- ✅ 완전한 제어
- ✅ 선택적 동기화
- ❌ 수동 작업 필요

### 동기화 스크립트 생성

```bash
# 집 Mac에서 회사 Mac으로
cat > ~/.claude/sync_to_office.sh << 'EOF'
#!/bin/bash
# 회사 Mac IP 또는 호스트명
OFFICE_MAC="office-mac.local"

rsync -avz --exclude='.claude.json' \
           --exclude='projects/' \
           --exclude='history.jsonl' \
           --exclude='file-history/' \
           --exclude='shell-snapshots/' \
           ~/.claude/ \
           $OFFICE_MAC:~/.claude/

echo "Sync completed!"
EOF

chmod +x ~/.claude/sync_to_office.sh
```

---

## 방법 4: Dropbox/Google Drive

### 장점
- ✅ 자동 동기화
- ✅ 버전 관리 (제한적)
- ❌ 충돌 가능성

### 단계별 가이드

```bash
# 1. Dropbox에 디렉토리 생성
mkdir -p ~/Dropbox/ClaudeSettings

# 2. 파일 이동 및 심볼릭 링크
mv ~/.claude/CLAUDE.md ~/Dropbox/ClaudeSettings/
ln -s ~/Dropbox/ClaudeSettings/CLAUDE.md ~/.claude/CLAUDE.md

# 3. 다른 Mac에서도 동일하게 심볼릭 링크 생성
```

---

## ⚠️ 주의사항

### 1. 민감정보 보호

**절대 공개 저장소에 올리면 안 되는 파일:**
- `.env` (API 키 포함)
- `settings.json` (개인 토큰 포함)

**Git 사용 시 권장:**
```bash
# .env 파일은 템플릿만 공유
cp ~/.claude/.env ~/.claude/.env.example
# .env.example 파일에서 실제 값 제거 후 커밋

# .gitignore에 추가
echo ".env" >> ~/.claude/.gitignore
echo ".env.example" > ~/.claude/.gitignore  # 템플릿은 공유
```

### 2. 머신별 차이 처리

**settings.json의 머신별 설정:**
```json
{
  "statusLine": {
    "type": "command",
    "command": "..."  // 머신마다 다를 수 있음
  }
}
```

**해결책: 조건부 설정**
```bash
# 머신별 설정 파일 생성
if [ "$(hostname)" = "home-mac" ]; then
  ln -sf ~/.claude/settings.home.json ~/.claude/settings.json
else
  ln -sf ~/.claude/settings.office.json ~/.claude/settings.json
fi
```

### 3. MCP 서버 경로 차이

**문제:**
```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "/Users/denny/.nvm/versions/node/v22.17.0/bin/mcp-server-puppeteer"
    }
  }
}
```
→ Node.js 버전이 다르면 경로가 다름

**해결책:**
```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "mcp-server-puppeteer"  // PATH에서 찾도록 설정
    }
  }
}
```

또는:
```bash
# 각 Mac에서 동일한 경로로 심볼릭 링크 생성
ln -s $(which mcp-server-puppeteer) ~/.local/bin/mcp-server-puppeteer
```

---

## 🎯 추천 워크플로우

### Git + Private Repository (최고 추천)

1. **초기 설정** (한 번만)
   ```bash
   cd ~/.claude
   git init
   # .gitignore 설정 (위 참고)
   git add .
   git commit -m "Initial settings"
   git remote add origin git@github.com:YOUR_USERNAME/claude-settings-private.git
   git push -u origin main
   ```

2. **다른 Mac에서**
   ```bash
   git clone git@github.com:YOUR_USERNAME/claude-settings-private.git ~/.claude
   chmod +x ~/.claude/*.sh
   ```

3. **변경 사항 동기화**
   - 집 Mac: `cd ~/.claude && git add -A && git commit -m "Update" && git push`
   - 회사 Mac: `cd ~/.claude && git pull`

### 자동화 스크립트

```bash
# ~/.claude/quick_sync.sh
#!/bin/bash
cd ~/.claude

# 변경사항 확인
if [[ -n $(git status -s) ]]; then
    echo "📝 Changes detected. Committing..."
    git add -A
    git commit -m "Auto-sync: $(date '+%Y-%m-%d %H:%M:%S')"
    git push
    echo "✅ Pushed to remote"
else
    echo "📥 Pulling from remote..."
    git pull
    echo "✅ Up to date"
fi
```

---

## 🔍 동기화 확인

### 동기화 후 확인 체크리스트

```bash
# 1. 파일 존재 확인
ls -la ~/.claude/CLAUDE.md
ls -la ~/.claude/commands/history-status.md
ls -la ~/.claude/cleanup_history.sh
ls -la ~/.claude/cleanup_sessions.sh

# 2. 실행 권한 확인
ls -l ~/.claude/*.sh

# 3. 슬래시 커맨드 확인
# Claude Code 실행 후 /history-status 입력

# 4. 전역 instruction 확인
# 아무 프로젝트에서 claude 실행 시 자동 로드 확인
```

---

## 📚 참고 링크

- [Git 공식 문서](https://git-scm.com/doc)
- [GitHub Private Repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories#about-repository-visibility)
- [rsync 매뉴얼](https://linux.die.net/man/1/rsync)

---

## 버전 정보

- **작성일**: 2025-10-12
- **버전**: 1.0.0
- **작성자**: Claude Code Assistant
