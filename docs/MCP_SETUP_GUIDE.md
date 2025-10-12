# MCP (Model Context Protocol) Setup Guide

## 개요
Claude Desktop에서 MCP 서버를 통해 Browser 자동화와 Figma 연동을 사용할 수 있도록 설정하는 가이드입니다.

## 설치된 MCP 서버

### 1. Puppeteer Browser Server
- **패키지**: `@modelcontextprotocol/server-puppeteer`
- **기능**: 웹 브라우저 자동화, 스크린샷, 페이지 스크래핑
- **경로**: `/Users/denny/.nvm/versions/node/v22.17.0/bin/mcp-server-puppeteer`

### 2. Figma Developer MCP
- **패키지**: `figma-developer-mcp`
- **기능**: Figma 디자인 데이터 접근, 컴포넌트 추출, 디자인 to 코드
- **경로**: `/Users/denny/.nvm/versions/node/v22.17.0/bin/figma-developer-mcp`
- **홈페이지**: https://www.framelink.ai

## 설정 파일 위치
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

## 현재 설정

```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "/Users/denny/.nvm/versions/node/v22.17.0/bin/mcp-server-puppeteer"
    },
    "figma": {
      "command": "/Users/denny/.nvm/versions/node/v22.17.0/bin/figma-developer-mcp",
      "env": {
        "FIGMA_PERSONAL_ACCESS_TOKEN": "YOUR_FIGMA_TOKEN_HERE"
      }
    }
  }
}
```

## Figma Personal Access Token 발급 방법

### 1. Figma 계정 설정 접속
1. Figma 웹사이트 접속: https://www.figma.com/
2. 우측 상단 프로필 클릭 → **Settings** 선택

### 2. Personal Access Token 생성
1. 좌측 메뉴에서 **Account** 탭 선택
2. 아래로 스크롤하여 **Personal access tokens** 섹션 찾기
3. **Generate new token** 버튼 클릭
4. Token 이름 입력 (예: "Claude Desktop MCP")
5. **Generate token** 클릭
6. 생성된 토큰을 복사 (한 번만 표시됨!)

### 3. 설정 파일에 토큰 추가
```bash
# 설정 파일 편집
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

`YOUR_FIGMA_TOKEN_HERE`를 실제 토큰으로 교체:
```json
{
  "mcpServers": {
    "figma": {
      "command": "/Users/denny/.nvm/versions/node/v22.17.0/bin/figma-developer-mcp",
      "env": {
        "FIGMA_PERSONAL_ACCESS_TOKEN": "figd_실제토큰값"
      }
    }
  }
}
```

## Claude Desktop 재시작

설정 변경 후 **반드시 Claude Desktop을 완전히 종료하고 재시작**해야 합니다:

```bash
# Claude Desktop 종료
pkill -f "Claude"

# Claude Desktop 재실행 (Spotlight 또는 Applications에서)
open -a "Claude"
```

## MCP 서버 사용 방법

### Puppeteer (Browser) 사용 예시

**웹페이지 스크린샷:**
```
Take a screenshot of https://www.example.com
```

**웹페이지 스크래핑:**
```
Get the content from https://news.ycombinator.com and summarize the top stories
```

**웹 자동화:**
```
Navigate to https://github.com and search for "bitcoin trading"
```

### Figma 사용 예시

**Figma 파일 정보 조회:**
```
Get information about this Figma file: https://www.figma.com/file/FILE_ID
```

**컴포넌트 추출:**
```
Extract all components from this Figma design and generate React code
```

**디자인 토큰 추출:**
```
Extract color palette and typography tokens from the Figma file
```

## 문제 해결

### 1. MCP 서버가 표시되지 않는 경우
- Claude Desktop을 완전히 종료하고 재시작
- 설정 파일 JSON 형식 확인 (trailing comma 등)
- 경로가 올바른지 확인

### 2. Figma 연동이 작동하지 않는 경우
- Personal Access Token이 올바르게 설정되었는지 확인
- Token이 만료되지 않았는지 확인
- Figma 파일에 접근 권한이 있는지 확인

### 3. Puppeteer가 작동하지 않는 경우
- Node.js 버전 확인 (v22.17.0 이상 권장)
- Chromium 다운로드 확인:
  ```bash
  npm install -g puppeteer
  ```

## 추가 MCP 서버 설치

다른 MCP 서버를 추가하려면:

```bash
# 서버 검색
npm search mcp

# 서버 설치
npm install -g <package-name>

# 설정 파일에 추가
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

## 유용한 MCP 서버 목록

- **@modelcontextprotocol/server-filesystem**: 파일 시스템 접근
- **@modelcontextprotocol/server-github**: GitHub API 연동
- **@modelcontextprotocol/server-slack**: Slack 연동
- **mcp-server-sqlite**: SQLite 데이터베이스 접근

## 참고 자료

- MCP 공식 문서: https://modelcontextprotocol.io
- Claude Desktop 문서: https://docs.anthropic.com/claude/docs/desktop
- Figma API 문서: https://www.figma.com/developers/api
- Puppeteer 문서: https://pptr.dev/

---

**설정 완료일**: 2025-10-12
**작성자**: Claude Code
