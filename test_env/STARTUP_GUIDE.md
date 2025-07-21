# PMark2.5 구동 가이드

## 프로젝트 구조
```
PMark2-Dev/                    # 프로젝트 루트
├── backend/                   # PMark2 (포트 8001/3001)
├── frontend/                  # PMark2 프론트엔드
└── test_env/                  # PMark2.5 (포트 8010/3010)
    ├── backend/               # PMark2.5 백엔드
    ├── frontend/              # PMark2.5 프론트엔드
    └── scripts/               # 구동 스크립트들
        ├── start_test_backend.py
        ├── start_test_frontend.py
        └── init_database.py
```

## PMark2.5 구동 방법

### 🔧 준비 단계

#### 1. 데이터베이스 초기화 (최초 1회만)
```bash
# 프로젝트 루트에서 test_env로 이동
cd test_env

# 데이터베이스 초기화 및 Excel 데이터 로드
python scripts/init_database.py
```

#### 2. 백엔드 구동
```bash
# test_env 디렉토리에서 실행
cd test_env

# 백엔드 서버 시작 (포트 8010)
# 주의: 스크립트가 자동으로 test_env/backend로 이동해서 uvicorn 실행
python scripts/start_test_backend.py
```

#### 3. 프론트엔드 구동 (새 터미널)
```bash
# 새 터미널에서 test_env로 이동
cd test_env

# 프론트엔드 서버 시작 (포트 3010)
python scripts/start_test_frontend.py
```

### 📊 서버 상태 확인
```bash
# 백엔드 서버 확인
curl http://localhost:8010/health

# API 문서 접속
open http://localhost:8010/docs

# 프론트엔드 접속
open http://localhost:3010
```

### 🛑 서버 중지
```bash
# 백엔드 서버 중지
pkill -f "python.*8010"

# 프론트엔드 서버 중지
pkill -f "python.*3010"

# 또는 각 터미널에서 Ctrl+C
```

## 🚀 백그라운드 실행 (선택사항)
```bash
# 백엔드 백그라운드 실행
cd test_env && python scripts/start_test_backend.py &

# 프론트엔드 백그라운드 실행  
cd test_env && python scripts/start_test_frontend.py &
```

## PMark2 vs PMark2.5 포트 구분

| 프로젝트 | 백엔드 포트 | 프론트엔드 포트 | 구동 위치 | 실행 명령 |
|---------|------------|---------------|----------|-----------|
| PMark2  | 8001       | 3001          | `backend/`, 프로젝트 루트 | `python main.py`, `python start_frontend.py` |
| PMark2.5| 8010       | 3010          | `test_env/` | `python scripts/start_test_backend.py` |

## ⚠️ 중요사항

### 구동 위치
- **PMark2.5는 반드시 `test_env` 디렉토리에서 구동**
- 스크립트가 자동으로 내부 디렉토리 이동 처리
- 절대 `test_env/backend`에서 직접 실행하지 말 것

### 파일 경로
- Excel 파일들은 프로젝트 루트에 위치
- 데이터베이스는 `test_env/data/` 에 생성
- 환경설정 파일(.env)은 각 프로젝트별 독립 관리

### 포트 충돌 방지
- PMark2와 PMark2.5는 동시 실행 가능
- 포트 8010이 사용 중이면 자동으로 8011~8030 범위에서 찾음

## 🧪 테스트 API 엔드포인트
```bash
# 채팅 테스트
curl -X POST "http://localhost:8010/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "압력베젤 고장", "conversation_history": []}'

# 자동완성 테스트  
curl -X POST "http://localhost:8010/api/v1/autocomplete" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "압력", "scenario_type": "scenario1"}'

# 시나리오 분석 테스트
curl -X POST "http://localhost:8010/api/v1/analyze-scenario" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Y-MV1035"}'
``` 