# PMark3 시스템 시작 가이드

## 📋 개요

이 문서는 PMark3 AI Assistant 시스템의 설치, 설정, 실행 방법을 단계별로 설명합니다.

## 🚀 빠른 시작

### 1. 시스템 요구사항

- **Python**: 3.8 이상
- **Node.js**: 16 이상
- **메모리**: 최소 4GB RAM
- **디스크**: 최소 2GB 여유 공간
- **네트워크**: 인터넷 연결 (OpenAI API 접근용)

### 2. 환경 설정

```bash
# 1. 프로젝트 클론
git clone [repository-url]
cd PMark3

# 2. 자동 설정 스크립트 실행
python scripts/setup_dev.py

# 3. 환경변수 설정
cp env.example .env
# .env 파일에서 OpenAI API 키 설정
```

### 3. 시스템 실행

```bash
# 1. 백엔드 실행 (새 터미널)
python scripts/start_backend.py

# 2. 프론트엔드 실행 (새 터미널)
python scripts/start_frontend.py
```

### 4. 접속 확인

- **백엔드**: http://localhost:8010
- **프론트엔드**: http://localhost:3010
- **API 문서**: http://localhost:8010/docs

## 🔧 상세 설치 가이드

### 1. 백엔드 설정

#### 1.1 가상환경 생성

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### 1.2 의존성 설치

```bash
pip install -r requirements.txt
```

#### 1.3 환경변수 설정

```bash
cp ../env.example .env
```

`.env` 파일 편집:
```env
OPENAI_API_KEY=your_openai_api_key_here
BACKEND_PORT=8010
FRONTEND_PORT=3010
DATABASE_URL=sqlite:///./data/notifications.db
VECTOR_DB_PATH=./data/vector_db
LOG_LEVEL=INFO
```

#### 1.4 데이터베이스 초기화

```bash
cd ..
python scripts/init_database.py
```

#### 1.5 백엔드 실행

```bash
python scripts/start_backend.py
```

**실행 확인 메시지:**
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

### 2. 프론트엔드 설정

#### 2.1 Node.js 의존성 설치

```bash
cd frontend
npm install
```

#### 2.2 프론트엔드 실행

```bash
cd ..
python scripts/start_frontend.py
```

**실행 확인 메시지:**
```
🚀 PMark3 Frontend Server Starting...
📁 Current directory: /path/to/PMark3
🌐 Server running on:
   • Local:    http://localhost:3010
   • Network:  http://192.168.0.69:3010
📡 Other computers can access:
   • Chatbot:     http://192.168.0.69:3010/
```

## 🔍 시스템 검증

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

### 3. 세션 관리 테스트

```bash
# 세션 생성 및 관리 테스트
curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "안녕하세요", "session_id": "test_session"}'
```

## 🛠️ 문제 해결

### 1. 포트 충돌 문제

```bash
# 포트 사용 확인
lsof -i :8010
lsof -i :3010

# 프로세스 종료
pkill -f "python.*start_backend.py"
pkill -f "python.*start_frontend.py"
```

### 2. 가상환경 문제

```bash
# 가상환경 재생성
cd backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 데이터베이스 문제

```bash
# 데이터베이스 재초기화
python scripts/init_database.py

# 수동 초기화
python -c "from backend.app.database import db_manager; db_manager.load_sample_data()"
```

### 4. OpenAI API 문제

```bash
# API 키 확인
echo $OPENAI_API_KEY

# .env 파일 확인
cat .env
```

## 📊 시스템 모니터링

### 1. 로그 확인

```bash
# 백엔드 로그
tail -f backend/logs/app.log

# 프론트엔드 로그
tail -f frontend/logs/server.log
```

### 2. 성능 모니터링

```bash
# 시스템 리소스 확인
top -p $(pgrep -f "python.*start_backend.py")

# 디스크 사용량
du -sh data/ backend/ frontend/
```

### 3. API 성능 테스트

```bash
# 응답 시간 테스트
time curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "No.1 PE 압력베젤 고장"}'
```

## 🔧 고급 설정

### 1. 환경별 설정

#### 개발 환경
```env
PMARK_ENV=development
LOG_LEVEL=DEBUG
DEBUG=True
```

#### 프로덕션 환경
```env
PMARK_ENV=production
LOG_LEVEL=INFO
DEBUG=False
```

### 2. 로깅 설정

```python
# backend/app/config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

### 3. 보안 설정

```env
# 프로덕션 환경 보안 설정
CORS_ORIGINS=http://localhost:3010,http://your-domain.com
RATE_LIMIT=100
MAX_SESSIONS=1000
```

## 🚨 긴급 상황 대응

### 1. 서버 다운 상황

```bash
# 모든 프로세스 종료
pkill -f "python.*start_backend.py"
pkill -f "python.*start_frontend.py"
pkill -f "uvicorn"
pkill -f "node.*server.js"

# 포트 해제
sudo kill -9 $(lsof -t -i:8010) 2>/dev/null || true
sudo kill -9 $(lsof -t -i:3010) 2>/dev/null || true

# 시스템 재시작
python scripts/start_backend.py &
python scripts/start_frontend.py &
```

### 2. 데이터베이스 손상

```bash
# 백업 생성
cp data/notifications.db data/notifications.db.backup

# 데이터베이스 재생성
rm data/notifications.db
python scripts/init_database.py
```

### 3. 환경 변수 문제

```bash
# 환경 변수 재설정
cp env.example .env
# .env 파일에서 OpenAI API 키 설정
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
- [ ] Python 3.8+ 설치됨
- [ ] Node.js 16+ 설치됨
- [ ] OpenAI API 키 보유
- [ ] 프로젝트 디렉토리 접근 가능
- [ ] 포트 8010, 3010 사용 가능

시스템 시작 후 확인사항:
- [ ] 백엔드 서버: 포트 8010 응답
- [ ] 프론트엔드 서버: 포트 3010 응답
- [ ] 웹 브라우저 접속 가능
- [ ] API 호출 정상 작동
- [ ] 세션 관리 정상 작동
- [ ] 자동완성 기능 정상 작동

## 🆘 추가 도움말

- **빠른 시작**: [QUICK_START.md](QUICK_START.md)
- **개발 가이드**: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- **API 문서**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **시스템 아키텍처**: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)
- **빠른 명령어**: [QUICK_COMMANDS.md](QUICK_COMMANDS.md)

---

**PMark3 시스템 시작 가이드** - 세션 관리와 벡터 검색을 포함한 고급 AI 작업요청 생성 시스템을 안정적으로 운영하세요! 🚀 