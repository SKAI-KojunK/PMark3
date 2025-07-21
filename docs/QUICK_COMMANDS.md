# PMark2 빠른 명령어 가이드

## 🚀 시스템 시작/종료

### 자동 스크립트 사용 (권장)
```bash
# 시스템 시작
./scripts/start_pmark2.sh

# 시스템 종료
./scripts/stop_pmark2.sh

# 시스템 상태 확인
./scripts/status_pmark2.sh
```

### 수동 명령어
```bash
# 백엔드 서버 시작
cd backend && source venv/bin/activate && python run.py

# 프론트엔드 서버 시작 (새 터미널)
python start_frontend.py

# 서버 종료
Ctrl + C (각 터미널에서)
```

## 🔍 상태 확인

### 포트 사용 확인
```bash
# 백엔드 포트 (8001)
lsof -i :8001

# 프론트엔드 포트 (3001)
lsof -i :3001
```

### API 테스트
```bash
# 백엔드 헬스체크
curl http://localhost:8001/health

# 프론트엔드 테스트
curl http://localhost:3001
```

## 🛠️ 문제 해결

### 프로세스 강제 종료
```bash
# 모든 PMark2 프로세스 종료
pkill -f "python run.py"
pkill -f "python start_frontend.py"
pkill -f "uvicorn"
```

### 데이터베이스 재초기화
```bash
cd backend
source venv/bin/activate
python -c "from app.database import db_manager; db_manager.load_excel_data()"
```

### 가상환경 재생성
```bash
cd backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📱 접속 정보

- **웹 브라우저**: http://localhost:3001
- **백엔드 API**: http://localhost:8001
- **API 문서**: http://localhost:8001/docs

## ⚡ 빠른 체크리스트

시스템 시작 전 확인사항:
- [ ] 프로젝트 디렉토리: `/Users/YMARX/Dropbox/2025_ECMiner/C_P02_SKAI/03_진행/PMark2-Dev`
- [ ] 백엔드 가상환경: `backend/venv/`
- [ ] 환경 변수: `backend/.env` (OpenAI API 키)
- [ ] 데이터베이스: `backend/data/sample_notifications.db`

시스템 시작 후 확인사항:
- [ ] 백엔드 서버: 포트 8001 응답
- [ ] 프론트엔드 서버: 포트 3001 응답
- [ ] 웹 브라우저 접속 가능
- [ ] API 호출 정상 작동 