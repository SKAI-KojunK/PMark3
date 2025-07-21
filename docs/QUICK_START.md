# PMark2 빠른 시작 가이드

## 🚀 5분 만에 PMark2 실행하기

이 가이드는 PMark2 AI Assistant를 빠르게 설치하고 실행하는 방법을 설명합니다.

## 📋 사전 요구사항

- **Python 3.8+** 설치됨
- **OpenAI API 키** 보유
- **터미널/명령 프롬프트** 접근 가능

## ⚡ 빠른 설치 및 실행

### 1단계: 프로젝트 다운로드

```bash
# 프로젝트 클론 (또는 다운로드)
git clone [repository-url]
cd PMark2-Dev
```

### 2단계: 백엔드 설정

```bash
# 백엔드 디렉토리로 이동
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp ../env.example .env
```

### 3단계: OpenAI API 키 설정

`.env` 파일을 편집하여 OpenAI API 키를 설정:

```env
OPENAI_API_KEY=your_openai_api_key_here
BACKEND_PORT=8001
DATABASE_URL=sqlite:///data/sample_notifications.db
LOG_LEVEL=INFO
```

### 4단계: 데이터베이스 초기화

```bash
# 샘플 데이터 로드
python -c "from app.database import db_manager; db_manager.load_sample_data()"
```

### 5단계: 백엔드 실행

```bash
# 백엔드 서버 시작
python run.py
```

**성공 메시지:**
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

### 6단계: 프론트엔드 실행

새 터미널을 열고:

```bash
# 프로젝트 루트로 이동
cd PMark2-Dev

# 프론트엔드 서버 시작
python start_frontend.py
```

**성공 메시지:**
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

### 7단계: 접속 및 테스트

브라우저에서 다음 URL로 접속:

- **메인 인터페이스**: http://localhost:3001
- **API 문서**: http://localhost:8001/docs

## 🧪 빠른 테스트

### 웹 인터페이스 테스트

1. http://localhost:3001 접속
2. 다음 테스트 메시지 입력:

```
No.1 PE 압력베젤 고장
```

**예상 결과:**
- 위치, 설비유형, 현상코드, 우선순위가 정확히 파싱됨
- 유사한 작업 3건이 추천됨
- 각 추천 항목에 유사도 점수 표시

### API 테스트

```bash
# 헬스 체크
curl http://localhost:8001/health

# 위치 기반 검색 테스트
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "석유제품배합/저장 탱크 누설"}'
```

## 🎯 주요 기능 체험

### 1. 위치 기반 검색

다양한 위치로 테스트해보세요:

```
No.1 PE 압력베젤 고장
석유제품배합/저장 탱크 누설
RFCC 펌프 작동불량 일반작업
```

### 2. 유사도 점수 확인

- **100% (녹색)**: 완벽한 매칭
- **80-99% (녹색)**: 매우 높은 유사도
- **60-79% (주황)**: 높은 유사도
- **20-59% (빨강)**: 낮은 유사도

### 3. ITEMNO 편집

추천 결과의 ITEMNO를 클릭하여 직접 수정할 수 있습니다.

### 4. ITEMNO 조회

```
ITEMNO PE-SE1304B
```

## 🛠️ 문제 해결

### 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8001
lsof -i :3001

# 프로세스 종료
kill -9 [PID]
```

### OpenAI API 오류

1. `.env` 파일에서 API 키 확인
2. OpenAI 계정에서 API 키 유효성 확인
3. API 사용량 한도 확인

### 가상환경 문제

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

## 📊 성능 확인

### 응답 시간

- **헬스 체크**: <100ms
- **채팅 API**: 2-8초 (LLM 호출 포함)
- **작업상세 생성**: 3-10초

### 정확도

- **위치 인식**: 95%+
- **설비유형 정규화**: 90%+
- **현상코드 정규화**: 85%+
- **우선순위 인식**: 90%+

## 🔄 시스템 재시작

### 전체 재시작

```bash
# 1. 모든 프로세스 종료
pkill -f "python run.py"
pkill -f "python start_frontend.py"

# 2. 백엔드 재시작
cd backend && source venv/bin/activate && python run.py

# 3. 프론트엔드 재시작 (새 터미널)
cd PMark2-Dev && python start_frontend.py
```

## 📞 지원

### 로그 확인

```bash
# 백엔드 로그
tail -f backend/logs/app.log

# 실시간 모니터링
htop
```

### API 문서

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### 연락처

- **기술 지원**: [이메일]
- **문서**: docs/ 디렉토리
- **이슈 리포트**: GitHub Issues

## 🎉 축하합니다!

PMark2 AI Assistant가 성공적으로 실행되었습니다!

**다음 단계:**
1. 다양한 테스트 케이스로 기능 체험
2. API 문서를 통한 개발자 도구 활용
3. 실제 업무 시나리오에 적용

---

**PMark2 빠른 시작 가이드** - 5분 만에 AI 기반 설비관리 시스템을 경험하세요! 