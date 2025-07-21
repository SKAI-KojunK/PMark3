# PMark2.5 테스트 환경 빠른 시작 가이드

## 🚀 1분 만에 테스트 환경 시작하기

### 1단계: 테스트 환경 초기 설정
```bash
# 프로젝트 루트 디렉토리에서
python test_env/scripts/setup_test_env.py
```

### 2단계: 테스트 환경 시작
```bash
# 터미널 1: 백엔드 시작 (포트 8010)
cd test_env
python scripts/start_test_backend.py

# 터미널 2: 프론트엔드 시작 (포트 3010)
cd test_env
python scripts/start_test_frontend.py
```

### 3단계: 접속 확인
- **테스트 환경**: http://localhost:3010 (기본값, 충돌 시 자동 변경)
- **기존 환경**: http://localhost:3001 (그대로 유지)

## 🔧 포트 설정
- **기존 프로젝트**: Backend 8001, Frontend 3001
- **테스트 환경**: Backend 8010, Frontend 3010 (기본값)
- **동적 포트 범위**: 
  - Backend: 8010~8030 (충돌 시 자동 선택)
  - Frontend: 3010~3030 (충돌 시 자동 선택)

## 📁 디렉토리 구조
```
test_env/
├── backend/              # 테스트용 백엔드
├── frontend/             # 테스트용 프론트엔드
├── data/                 # 테스트용 데이터
├── scripts/              # 실행 스크립트
├── test_chatbot.html     # 테스트용 챗봇 인터페이스
└── .env                  # 테스트 환경 설정
```

## 🛑 테스트 환경 종료
```bash
# 방법 1: 각 터미널에서 Ctrl+C
# 방법 2: 스크립트 사용
python test_env/scripts/stop_test_env.py
```

## 🔍 문제 해결

### 포트 충돌 시
- 스크립트가 자동으로 다른 포트를 찾아 사용합니다
- 로그를 확인하여 실제 사용 중인 포트를 확인하세요

### 파일을 찾을 수 없을 때
```bash
# 테스트 환경 재설정
python test_env/scripts/setup_test_env.py
```

### 데이터베이스 오류 시
```bash
# 테스트 데이터베이스 초기화
rm -rf test_env/data/*
python test_env/scripts/setup_test_env.py
```

## 📊 모니터링
- **백엔드 상태**: http://localhost:8010/health (실제 포트 확인 필요)
- **테스트 정보**: http://localhost:8010/test-info (실제 포트 확인 필요)
- **API 문서**: http://localhost:8010/docs (실제 포트 확인 필요)

## 💡 팁
- 테스트 환경은 기존 프로젝트와 완전히 독립적입니다
- 새로운 기능을 안전하게 테스트할 수 있습니다
- 기존 환경은 그대로 유지되므로 안심하고 테스트하세요 