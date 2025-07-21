# PMark3 빠른 명령어 가이드

## 🚀 시스템 시작/종료

### 자동 스크립트 사용 (권장)
```bash
# 시스템 시작
python scripts/start_backend.py    # 백엔드 시작
python scripts/start_frontend.py   # 프론트엔드 시작

# 시스템 종료
python scripts/stop_dev.py         # 모든 서비스 종료
```

### 수동 명령어
```bash
# 백엔드 서버 시작
cd backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8010

# 프론트엔드 서버 시작 (새 터미널)
cd frontend && node server.js

# 서버 종료
Ctrl + C (각 터미널에서)
```

## 🔍 상태 확인

### 포트 사용 확인
```bash
# 백엔드 포트 (8010)
lsof -i :8010

# 프론트엔드 포트 (3010)
lsof -i :3010
```

### API 테스트
```bash
# 백엔드 헬스체크
curl http://localhost:8010/health

# 프론트엔드 테스트
curl http://localhost:3010
```

### 세션 관리 테스트
```bash
# 세션 생성
curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "테스트 메시지"}'

# 세션 정보 조회
curl "http://localhost:8010/api/v1/session/{session_id}"

# 세션 삭제
curl -X DELETE "http://localhost:8010/api/v1/session/{session_id}"
```

## 🛠️ 문제 해결

### 프로세스 강제 종료
```bash
# 모든 PMark3 프로세스 종료
pkill -f "python.*start_backend.py"
pkill -f "python.*start_frontend.py"
pkill -f "uvicorn"
pkill -f "node.*server.js"
```

### 데이터베이스 재초기화
```bash
# 데이터베이스 초기화
python scripts/init_database.py

# 수동 초기화
python -c "from backend.app.database import db_manager; db_manager.load_sample_data()"
```

### 가상환경 재생성
```bash
cd backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 프론트엔드 의존성 재설치
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## 🔧 개발 도구

### 로그 확인
```bash
# 백엔드 로그
tail -f backend/logs/app.log

# 프론트엔드 로그
tail -f frontend/logs/server.log

# 실시간 로그 모니터링
watch -n 1 'tail -n 10 backend/logs/app.log'
```

### 환경 변수 확인
```bash
# 현재 환경 변수 확인
env | grep -E "(PMARK|OPENAI|BACKEND|FRONTEND)"

# .env 파일 확인
cat .env
```

### 데이터베이스 확인
```bash
# SQLite 데이터베이스 확인
sqlite3 data/notifications.db ".tables"

# 테이블 구조 확인
sqlite3 data/notifications.db ".schema notifications"

# 데이터 확인
sqlite3 data/notifications.db "SELECT COUNT(*) FROM notifications;"
```

## 📊 성능 모니터링

### 시스템 리소스 확인
```bash
# CPU 및 메모리 사용량
top -p $(pgrep -f "python.*start_backend.py")

# 디스크 사용량
du -sh data/ backend/ frontend/

# 네트워크 연결 확인
netstat -tulpn | grep -E "(8010|3010)"
```

### API 성능 테스트
```bash
# 응답 시간 테스트
time curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "No.1 PE 압력베젤 고장"}'

# 부하 테스트 (10개 동시 요청)
for i in {1..10}; do
  curl -X POST "http://localhost:8010/api/v1/chat" \
       -H "Content-Type: application/json" \
       -d '{"message": "테스트 메시지 '$i'"}' &
done
wait
```

## 🔍 디버깅

### 백엔드 디버깅
```bash
# 상세 로그로 백엔드 시작
cd backend
source venv/bin/activate
LOG_LEVEL=DEBUG uvicorn main:app --host 0.0.0.0 --port 8010 --reload

# 특정 모듈 디버깅
python -c "from app.agents.parser import input_parser; print(input_parser.parse_input('테스트'))"
```

### 프론트엔드 디버깅
```bash
# Node.js 디버그 모드
cd frontend
DEBUG=* node server.js

# 브라우저 개발자 도구
# F12 → Console 탭에서 에러 확인
```

### 데이터베이스 디버깅
```bash
# 데이터베이스 직접 확인
sqlite3 data/notifications.db

# 세션 데이터 확인
sqlite3 data/notifications.db "SELECT * FROM sessions LIMIT 5;"

# 벡터 DB 확인
ls -la data/vector_db/
```

## 🧪 테스트 명령어

### API 테스트
```bash
# 기본 API 테스트
curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "No.1 PE 압력베젤 고장"}'

# 자동완성 테스트
curl -X POST "http://localhost:8010/api/v1/autocomplete" \
     -H "Content-Type: application/json" \
     -d '{"partial_input": "No.1 PE", "category": "location"}'

# 작업상세 생성 테스트
curl -X POST "http://localhost:8010/api/v1/generate-work-details" \
     -H "Content-Type: application/json" \
     -d '{"itemno": "PE-SE1304B"}'
```

### 통합 테스트
```bash
# 전체 워크플로우 테스트
python test_autocomplete.py

# 성능 테스트
python test_priority.py
```

## 📱 접속 정보

- **웹 브라우저**: http://localhost:3010
- **백엔드 API**: http://localhost:8010
- **API 문서**: http://localhost:8010/docs
- **ReDoc 문서**: http://localhost:8010/redoc

## ⚡ 빠른 체크리스트

시스템 시작 전 확인사항:
- [ ] 프로젝트 디렉토리: `/Users/YMARX/Dropbox/2025_ECMiner/C_P02_SKAI/03_진행/PMark3`
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

## 🆘 긴급 상황 대응

### 서버가 응답하지 않는 경우
```bash
# 모든 프로세스 종료
pkill -f "python.*start_backend.py"
pkill -f "python.*start_frontend.py"
pkill -f "uvicorn"
pkill -f "node.*server.js"

# 포트 확인 및 해제
sudo lsof -i :8010 -i :3010
sudo kill -9 $(lsof -t -i:8010) 2>/dev/null || true
sudo kill -9 $(lsof -t -i:3010) 2>/dev/null || true

# 시스템 재시작
python scripts/start_backend.py &
python scripts/start_frontend.py &
```

### 데이터베이스 손상 시
```bash
# 백업 생성
cp data/notifications.db data/notifications.db.backup

# 데이터베이스 재생성
rm data/notifications.db
python scripts/init_database.py
```

### 환경 변수 문제 시
```bash
# 환경 변수 재설정
cp env.example .env
# .env 파일에서 OpenAI API 키 설정
```

---

**PMark3 빠른 명령어 가이드** - 모든 PMark3 관련 명령어를 한 곳에서 확인하세요! 🚀 