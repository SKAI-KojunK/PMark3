# PMark2 시스템 시작 가이드

## 📋 개요

이 문서는 PMark2 AI Assistant 시스템의 설치, 설정, 실행 방법을 단계별로 설명합니다.

## 🚀 빠른 시작

### 1. 시스템 요구사항

- **Python**: 3.8 이상
- **메모리**: 최소 4GB RAM
- **디스크**: 최소 2GB 여유 공간
- **네트워크**: 인터넷 연결 (OpenAI API 접근용)

### 2. 환경 설정

```bash
# 1. 프로젝트 클론
git clone [repository-url]
cd PMark2-Dev

# 2. 백엔드 가상환경 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp ../env.example .env
# .env 파일에서 OpenAI API 키 설정
```

### 3. 시스템 실행

```bash
# 1. 백엔드 실행 (새 터미널)
cd backend
source venv/bin/activate
python run.py

# 2. 프론트엔드 실행 (새 터미널)
cd PMark2-Dev
python start_frontend.py
```

### 4. 접속 확인

- **백엔드**: http://localhost:8001
- **프론트엔드**: http://localhost:3001
- **API 문서**: http://localhost:8001/docs

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
BACKEND_PORT=8001
DATABASE_URL=sqlite:///data/sample_notifications.db
LOG_LEVEL=INFO
```

#### 1.4 데이터베이스 초기화

```bash
python -c "from app.database import db_manager; db_manager.load_sample_data()"
```

#### 1.5 백엔드 실행

```bash
python run.py
```

**실행 확인 메시지:**
```
🚀 PMark2 Backend Server Starting...
🌐 Server running on:
   • Local:    http://localhost:8001
   • Network:  http://192.168.0.69:8001
📡 Other computers can access: http://192.168.0.69:8001
🛑 Press Ctrl+C to stop the server
INFO:     Uvicorn running on http://0.0.0.0:8001
🚀 PMark2 AI Assistant 시작 중...
✅ 데이터베이스 초기화 완료
INFO:     Application startup complete.
```

### 2. 프론트엔드 설정

#### 2.1 프론트엔드 실행

```bash
cd PMark2-Dev
python start_frontend.py
```

**실행 확인 메시지:**
```
🚀 PMark1 Frontend Server Starting...
📁 Current directory: /path/to/PMark2-Dev
🌐 Server running on:
   • Local:    http://localhost:3001
   • Network:  http://192.168.0.69:3001
📡 Other computers can access:
   • Chatbot:     http://192.168.0.69:3001/
   • Prototype:   http://192.168.0.69:3001/old
👥 Multi-user support: ✅ ENABLED
🛑 Press Ctrl+C to stop the server
✅ chatbot.html found
🔥 Server ready for multiple concurrent users!
```

## 🔍 시스템 상태 확인

### 1. 백엔드 상태 확인

```bash
curl http://localhost:8001/health
```

**예상 응답:**
```json
{"status":"healthy"}
```

### 2. API 문서 확인

브라우저에서 http://localhost:8001/docs 접속

### 3. 프론트엔드 확인

브라우저에서 http://localhost:3001 접속

## 🧪 기능 테스트

### 1. 기본 기능 테스트

```bash
# 위치 기반 검색 테스트
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "No.1 PE 압력베젤 고장"}'

# 다른 위치 테스트
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "석유제품배합/저장 탱크 누설"}'

# ITEMNO 조회 테스트
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "ITEMNO PE-SE1304B"}'
```

### 2. 웹 인터페이스 테스트

1. 브라우저에서 http://localhost:3001 접속
2. 다음 테스트 케이스 입력:
   - "No.1 PE 압력베젤 고장"
   - "RFCC 펌프 작동불량 일반작업"
   - "ITEMNO PE-SE1304B"

## 🛠️ 문제 해결

### 1. 포트 충돌 문제

**증상**: 포트가 이미 사용 중이라는 오류
**해결방법**:
```bash
# 사용 중인 포트 확인
lsof -i :8001
lsof -i :3001

# 프로세스 종료
kill -9 [PID]
```

### 2. OpenAI API 키 문제

**증상**: OpenAI API 관련 오류
**해결방법**:
1. `.env` 파일에서 API 키 확인
2. OpenAI 계정에서 API 키 유효성 확인
3. API 사용량 한도 확인

### 3. 데이터베이스 문제

**증상**: 데이터베이스 연결 오류
**해결방법**:
```bash
cd backend
python -c "from app.database import db_manager; db_manager._init_database()"
```

### 4. 가상환경 문제

**증상**: 패키지 import 오류
**해결방법**:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

## 🔄 시스템 재시작

### 1. 전체 시스템 재시작

```bash
# 1. 모든 프로세스 종료
pkill -f "python run.py"
pkill -f "python start_frontend.py"

# 2. 백엔드 재시작
cd backend
source venv/bin/activate
python run.py

# 3. 프론트엔드 재시작 (새 터미널)
cd PMark2-Dev
python start_frontend.py
```

### 2. 백엔드만 재시작

```bash
# 백엔드 프로세스 종료
pkill -f "python run.py"

# 백엔드 재시작
cd backend
source venv/bin/activate
python run.py
```

### 3. 프론트엔드만 재시작

```bash
# 프론트엔드 프로세스 종료
pkill -f "python start_frontend.py"

# 프론트엔드 재시작
cd PMark2-Dev
python start_frontend.py
```

## 📊 모니터링

### 1. 로그 확인

```bash
# 백엔드 로그 확인
tail -f backend/logs/app.log

# 시스템 로그 확인
journalctl -u pmark2-backend -f
```

### 2. 성능 모니터링

```bash
# CPU/메모리 사용량 확인
htop

# 네트워크 연결 확인
netstat -tulpn | grep :8001
netstat -tulpn | grep :3001
```

### 3. API 응답 시간 확인

```bash
# API 응답 시간 측정
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8001/health"
```

## 🔒 보안 설정

### 1. 방화벽 설정

```bash
# 필요한 포트만 열기
sudo ufw allow 8001
sudo ufw allow 3001
```

### 2. 환경변수 보안

```bash
# .env 파일 권한 설정
chmod 600 backend/.env
```

### 3. API 키 보안

- OpenAI API 키를 환경변수로 설정
- API 키를 코드에 하드코딩하지 않기
- 정기적으로 API 키 로테이션

## 📈 성능 최적화

### 1. 캐싱 설정

```bash
# Redis 캐시 서버 설치 (선택사항)
sudo apt-get install redis-server
```

### 2. 데이터베이스 최적화

```bash
# SQLite 인덱스 생성
sqlite3 backend/data/sample_notifications.db
CREATE INDEX idx_location ON notifications(location);
CREATE INDEX idx_equipType ON notifications(equipType);
```

### 3. 로그 레벨 조정

```env
# .env 파일에서 로그 레벨 조정
LOG_LEVEL=WARNING  # INFO, DEBUG, WARNING, ERROR
```

## 🚀 프로덕션 배포

### 1. 서비스 등록

```bash
# systemd 서비스 파일 생성
sudo nano /etc/systemd/system/pmark2-backend.service
sudo nano /etc/systemd/system/pmark2-frontend.service
```

### 2. 자동 시작 설정

```bash
# 서비스 활성화
sudo systemctl enable pmark2-backend
sudo systemctl enable pmark2-frontend

# 서비스 시작
sudo systemctl start pmark2-backend
sudo systemctl start pmark2-frontend
```

### 3. 로그 로테이션

```bash
# logrotate 설정
sudo nano /etc/logrotate.d/pmark2
```

## 📞 지원 및 문의

### 1. 로그 수집

```bash
# 문제 진단을 위한 로그 수집
tar -czf pmark2-logs-$(date +%Y%m%d).tar.gz backend/logs/
```

### 2. 시스템 정보 수집

```bash
# 시스템 정보 수집
systeminfo > system-info.txt
python --version >> system-info.txt
pip list >> system-info.txt
```

### 3. 연락처

- **기술 지원**: [이메일]
- **문서**: docs/ 디렉토리
- **이슈 리포트**: GitHub Issues

---

**PMark2 시스템 시작 가이드** - 시스템을 성공적으로 실행하고 관리하는 데 도움이 됩니다. 