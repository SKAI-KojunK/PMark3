# PMark3 빠른 시작 가이드

## 🚀 5분 만에 PMark3 실행하기

이 가이드는 PMark3 AI Assistant를 빠르게 설치하고 실행하는 방법을 설명합니다.

## 📋 사전 요구사항

- **Python 3.8+** 설치됨
- **Node.js 16+** 설치됨
- **OpenAI API 키** 보유
- **터미널/명령 프롬프트** 접근 가능

## ⚡ 빠른 설치 및 실행

### 1단계: 프로젝트 다운로드

```bash
# 프로젝트 클론 (또는 다운로드)
git clone [repository-url]
cd PMark3
```

### 2단계: 개발 환경 설정

```bash
# 자동 설정 스크립트 실행
python scripts/setup_dev.py
```

이 스크립트는 다음을 자동으로 수행합니다:
- 백엔드 가상환경 생성 및 의존성 설치
- 프론트엔드 의존성 설치
- 환경 변수 파일 생성
- 데이터베이스 초기화

### 3단계: OpenAI API 키 설정

`.env` 파일을 편집하여 OpenAI API 키를 설정:

```env
OPENAI_API_KEY=your_openai_api_key_here
BACKEND_PORT=8010
FRONTEND_PORT=3010
DATABASE_URL=sqlite:///./data/notifications.db
VECTOR_DB_PATH=./data/vector_db
LOG_LEVEL=INFO
```

### 4단계: 시스템 실행

```bash
# 백엔드 서버 시작
python scripts/start_backend.py
```

**성공 메시지:**
```
🚀 PMark3 Backend Server Starting...
🌐 Server running on:
   • Local:    http://localhost:8010
   • Network:  http://192.168.0.69:8010
📡 Other computers can access: http://192.168.0.69:8010
🛑 Press Ctrl+C to stop the server
INFO:     Uvicorn running on http://0.0.0.0:8010
🚀 PMark3 AI Assistant 시작 중...
✅ 데이터베이스 초기화 완료
INFO:     Application startup complete.
```

새 터미널을 열고:

```bash
# 프론트엔드 서버 시작
python scripts/start_frontend.py
```

**성공 메시지:**
```
🚀 PMark3 Frontend Server Starting...
📁 Current directory: /path/to/PMark3
🌐 Server running on:
   • Local:    http://localhost:3010
   • Network:  http://192.168.0.69:3010
📡 Other computers can access:
   • Chatbot:     http://192.168.0.69:3010/
```

### 5단계: 접속 확인

- **웹 브라우저**: http://localhost:3010
- **백엔드 API**: http://localhost:8010
- **API 문서**: http://localhost:8010/docs

## 🔧 시스템 종료

```bash
# 시스템 종료
python scripts/stop_dev.py
```

## 🧪 빠른 테스트

### 1. API 테스트

```bash
# 헬스 체크
curl http://localhost:8010/health

# 채팅 API 테스트
curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "No.1 PE 압력베젤 고장"}'
```

### 2. 웹 인터페이스 테스트

브라우저에서 http://localhost:3010 접속 후:

1. **기본 테스트**: "No.1 PE 압력베젤 고장" 입력
2. **위치 테스트**: "석유제품배합/저장 탱크 누설" 입력
3. **ITEMNO 테스트**: "ITEMNO PE-SE1304B" 입력

## 🚨 문제 해결

### 백엔드 서버가 시작되지 않는 경우

```bash
# 포트 확인
lsof -i :8010

# 프로세스 종료
pkill -f "python.*start_backend.py"

# 가상환경 재활성화
cd backend
source venv/bin/activate
python scripts/start_backend.py
```

### 프론트엔드 서버가 시작되지 않는 경우

```bash
# 포트 확인
lsof -i :3010

# Node.js 의존성 재설치
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 데이터베이스 오류

```bash
# 데이터베이스 재초기화
python scripts/init_database.py
```

### OpenAI API 오류

```bash
# API 키 확인
echo $OPENAI_API_KEY

# .env 파일 확인
cat .env
```

## 📊 시스템 상태 확인

### 포트 사용 현황

```bash
# 백엔드 포트 (8010)
lsof -i :8010

# 프론트엔드 포트 (3010)
lsof -i :3010
```

### 로그 확인

```bash
# 백엔드 로그
tail -f backend/logs/app.log

# 프론트엔드 로그
tail -f frontend/logs/server.log
```

## 🔍 주요 기능 테스트

### 1. 세션 관리 테스트

```bash
# 세션 생성
curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "안녕하세요"}'

# 세션 정보 조회 (응답에서 session_id 확인)
curl "http://localhost:8010/api/v1/session/{session_id}"
```

### 2. 자동완성 테스트

```bash
# 위치 자동완성
curl -X POST "http://localhost:8010/api/v1/autocomplete" \
     -H "Content-Type: application/json" \
     -d '{"partial_input": "No.1 PE", "category": "location"}'
```

### 3. 벡터 검색 테스트

```bash
# 유사도 검색
curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "펌프 고장", "session_id": "test_session"}'
```

## 📱 접속 정보 요약

| 서비스 | URL | 포트 | 설명 |
|--------|-----|------|------|
| 웹 인터페이스 | http://localhost:3010 | 3010 | 메인 챗봇 인터페이스 |
| 백엔드 API | http://localhost:8010 | 8010 | RESTful API 서버 |
| API 문서 | http://localhost:8010/docs | 8010 | Swagger UI |
| API 문서 (ReDoc) | http://localhost:8010/redoc | 8010 | ReDoc 문서 |

## ⚡ 빠른 체크리스트

시스템 시작 전 확인사항:
- [ ] 프로젝트 디렉토리: `/path/to/PMark3`
- [ ] 백엔드 가상환경: `backend/venv/`
- [ ] 환경 변수: `.env` (OpenAI API 키)
- [ ] 데이터베이스: `data/notifications.db`
- [ ] 벡터 DB: `data/vector_db/`

시스템 시작 후 확인사항:
- [ ] 백엔드 서버: 포트 8010 응답
- [ ] 프론트엔드 서버: 포트 3010 응답
- [ ] 웹 브라우저 접속 가능
- [ ] API 호출 정상 작동
- [ ] 세션 관리 정상 작동
- [ ] 자동완성 기능 정상 작동

## 🆘 추가 도움말

- **개발 가이드**: [docs/DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- **API 문서**: [docs/API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **시스템 아키텍처**: [docs/SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)
- **노트북 예제**: [notebooks/](../notebooks/)

---

**PMark3 빠른 시작 가이드** - 세션 관리와 벡터 검색을 포함한 고급 AI 작업요청 생성 시스템을 5분 만에 실행하세요! 🚀 