# PMark3 개발 가이드

## 📋 목차

1. [개발 환경 설정](#개발-환경-설정)
2. [코드 구조 및 아키텍처](#코드-구조-및-아키텍처)
3. [컴포넌트별 수정 가이드](#컴포넌트별-수정-가이드)
4. [API 개발 가이드](#api-개발-가이드)
5. [데이터베이스 관리](#데이터베이스-관리)
6. [LLM 프롬프트 개발](#llm-프롬프트-개발)
7. [세션 관리 개발](#세션-관리-개발)
8. [벡터 검색 개발](#벡터-검색-개발)
9. [테스트 및 품질 관리](#테스트-및-품질-관리)
10. [배포 및 운영](#배포-및-운영)

## 🛠️ 개발 환경 설정

### 필수 도구
- **Python 3.8+**: 백엔드 개발
- **Node.js 16+**: 프론트엔드 개발
- **Git**: 버전 관리
- **VS Code**: 권장 IDE
- **Postman/Insomnia**: API 테스트

### 개발 환경 설정

```bash
# 1. 저장소 클론
git clone [repository-url]
cd PMark3

# 2. 백엔드 환경 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경변수 설정
cp ../env.example .env
# .env 파일에서 OpenAI API 키 설정

# 4. 프론트엔드 환경 설정
cd ../frontend
npm install

# 5. 데이터베이스 초기화
cd ..
python scripts/init_database.py
```

### 개발 서버 실행

```bash
# 백엔드 (터미널 1)
python scripts/start_backend.py

# 프론트엔드 (터미널 2)
python scripts/start_frontend.py
```

## 🏗️ 코드 구조 및 아키텍처

### 디렉토리 구조
```
PMark3/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── models.py              # 데이터 모델
│   │   ├── config.py              # 설정 관리
│   │   ├── database.py            # 데이터베이스 관리
│   │   ├── session_manager.py     # 세션 관리
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   └── parser.py          # 입력 파서
│   │   ├── logic/
│   │   │   ├── __init__.py
│   │   │   ├── normalizer.py      # LLM 정규화 엔진
│   │   │   ├── recommender.py     # 추천 엔진
│   │   │   └── scenario_analyzer.py # 시나리오 분석
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── chat.py            # 채팅 API
│   │       ├── work_details.py    # 작업상세 API
│   │       └── autocomplete.py    # 자동완성 API
│   ├── data/                      # 데이터 파일
│   ├── main.py                    # FastAPI 앱
│   └── requirements.txt           # 의존성
├── frontend/
│   ├── server.js                  # Node.js 서버
│   ├── package.json               # 프론트엔드 의존성
│   └── package-lock.json
├── scripts/
│   ├── start_backend.py           # 백엔드 시작 스크립트
│   ├── start_frontend.py          # 프론트엔드 시작 스크립트
│   ├── setup_dev.py               # 개발 환경 설정
│   ├── stop_dev.py                # 개발 환경 종료
│   └── init_database.py           # 데이터베이스 초기화
├── docs/                          # 문서
├── notebooks/                     # 실험 노트북
├── data/                          # 공유 데이터
├── test_chatbot.html              # 메인 챗봇 인터페이스
└── env.example                    # 환경 변수 예시
```

### 데이터 흐름
```
사용자 입력 → Session Manager → Parser → Normalizer → Recommender → Vector DB → Response
     ↓
Autocomplete API → Vector Search → Suggestions
     ↓
Work Details API → LLM → Finalize API → Database
```

## 🔧 컴포넌트별 수정 가이드

### 1. 입력 파서 (InputParser)

**파일**: `backend/app/agents/parser.py`

```python
class InputParser:
    def parse_input_with_context(self, user_input: str, conversation_history: list = None, session_id: str = None) -> ParsedInput:
        """
        세션 컨텍스트를 포함한 입력 파싱 (PMark3 고급 기능)
        """
        # 세션 컨텍스트 활용
        # 위치 우선 추출
        # LLM 기반 정보 추출
```

**주요 수정 포인트:**
- 세션 컨텍스트 통합
- 위치 기반 우선순위
- LLM 프롬프트 최적화

### 2. 세션 관리자 (SessionManager)

**파일**: `backend/app/session_manager.py`

```python
class SessionManager:
    def create_session(self) -> str:
        """새 세션 생성"""
    
    def get_session(self, session_id: str) -> Session:
        """세션 정보 조회"""
    
    def update_session(self, session_id: str, message: str, context: dict):
        """세션 정보 업데이트"""
```

**주요 기능:**
- 세션 생성/조회/삭제
- 대화 컨텍스트 유지
- 세션별 설정 관리

### 3. 정규화 엔진 (LLM Normalizer)

**파일**: `backend/app/logic/normalizer.py`

```python
class LLMNormalizer:
    def normalize_term(self, term: str, category: str) -> NormalizedTerm:
        """
        동적 정규화 시스템
        """
        # DB 용어 로딩
        # LLM 기반 변환
        # 캐시 관리
```

### 4. 추천 엔진 (Recommendation Engine)

**파일**: `backend/app/logic/recommender.py`

```python
class RecommendationEngine:
    def get_recommendations(self, parsed_input: ParsedInput, session_id: str = None) -> List[Recommendation]:
        """
        벡터 검색 기반 추천
        """
        # 벡터 유사도 검색
        # 위치 기반 필터링
        # 점수 계산 및 정렬
```

### 5. 벡터 검색 (Vector Search)

**파일**: `backend/app/logic/recommender.py`

```python
def vector_search(self, query: str, top_k: int = 10) -> List[VectorResult]:
    """
    벡터 데이터베이스 검색
    """
    # 임베딩 생성
    # 벡터 유사도 계산
    # 결과 정렬
```

## 🔧 API 개발 가이드

### 1. 새로운 API 엔드포인트 추가

```python
# backend/app/api/new_api.py
from fastapi import APIRouter, HTTPException
from app.models import NewRequest, NewResponse

router = APIRouter(prefix="/api/v1", tags=["new"])

@router.post("/new-endpoint")
async def new_endpoint(request: NewRequest) -> NewResponse:
    """
    새로운 API 엔드포인트
    """
    try:
        # 비즈니스 로직
        result = process_request(request)
        return NewResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. 세션 관리 통합

```python
# API에서 세션 관리 사용
@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or session_manager.create_session()
    
    # 세션 컨텍스트 활용
    context = session_manager.get_session_context(session_id)
    
    # 처리 후 세션 업데이트
    session_manager.update_session(session_id, request.message, result)
```

### 3. 에러 처리

```python
from app.exceptions import PMarkException

@router.post("/api/v1/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        # API 로직
        pass
    except PMarkException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 🗄️ 데이터베이스 관리

### 1. 데이터베이스 스키마

```sql
-- notifications 테이블
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY,
    itemno TEXT,
    process TEXT,
    location TEXT,
    equipType TEXT,
    statusCode TEXT,
    priority TEXT,
    work_title TEXT,
    work_details TEXT,
    created_at TIMESTAMP
);

-- sessions 테이블
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    last_activity TIMESTAMP,
    message_count INTEGER,
    context_summary TEXT
);
```

### 2. 데이터베이스 초기화

```bash
# 데이터베이스 초기화
python scripts/init_database.py

# 수동 초기화
python -c "from app.database import db_manager; db_manager.load_sample_data()"
```

### 3. 벡터 데이터베이스 관리

```python
# 벡터 DB 초기화
from app.logic.recommender import vector_db_manager

# 임베딩 생성
vector_db_manager.create_embeddings()

# 벡터 검색
results = vector_db_manager.search("query", top_k=10)
```

## 🤖 LLM 프롬프트 개발

### 1. 프롬프트 템플릿

```python
# backend/app/agents/parser.py
LOCATION_EXTRACTION_PROMPT = """
다음 자연어에서 위치 정보를 추출해주세요:

입력: {input_text}

위치 정보만 추출하여 JSON 형식으로 응답하세요:
{{
    "location": "추출된 위치",
    "confidence": 0.95
}}
"""
```

### 2. 프롬프트 최적화

```python
def optimize_prompt(self, prompt: str, context: dict) -> str:
    """
    컨텍스트를 활용한 프롬프트 최적화
    """
    # 세션 컨텍스트 추가
    # 이전 대화 히스토리 활용
    # 동적 프롬프트 생성
```

## 🔄 세션 관리 개발

### 1. 세션 생성 및 관리

```python
class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.max_sessions = 1000
        self.session_timeout = 3600  # 1시간
    
    def create_session(self) -> str:
        """새 세션 생성"""
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        self.sessions[session_id] = Session(
            session_id=session_id,
            created_at=datetime.now(),
            messages=[],
            context={}
        )
        return session_id
```

### 2. 컨텍스트 관리

```python
def update_context(self, session_id: str, message: str, result: dict):
    """세션 컨텍스트 업데이트"""
    session = self.get_session(session_id)
    session.messages.append({
        "timestamp": datetime.now(),
        "message": message,
        "result": result
    })
    
    # 컨텍스트 요약 생성
    session.context_summary = self._generate_context_summary(session)
```

## 🔍 벡터 검색 개발

### 1. 임베딩 생성

```python
from sentence_transformers import SentenceTransformer

class VectorDBManager:
    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    def create_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """텍스트 임베딩 생성"""
        return self.model.encode(texts)
```

### 2. 유사도 검색

```python
def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
    """벡터 유사도 검색"""
    query_embedding = self.model.encode([query])[0]
    
    # 코사인 유사도 계산
    similarities = cosine_similarity([query_embedding], self.embeddings)[0]
    
    # 상위 k개 결과 반환
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    return [SearchResult(index=i, score=similarities[i]) for i in top_indices]
```

## 🧪 테스트 및 품질 관리

### 1. 단위 테스트

```python
# tests/test_parser.py
import pytest
from app.agents.parser import InputParser

def test_location_extraction():
    parser = InputParser()
    result = parser.parse_input_with_context("No.1 PE 압력베젤 고장")
    assert result.location == "No.1 PE"
    assert result.confidence > 0.8
```

### 2. 통합 테스트

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_chat_api():
    response = client.post("/api/v1/chat", json={
        "message": "No.1 PE 압력베젤 고장"
    })
    assert response.status_code == 200
    assert "recommendations" in response.json()
```

### 3. 성능 테스트

```python
# tests/test_performance.py
import time

def test_api_response_time():
    start_time = time.time()
    response = client.post("/api/v1/chat", json={"message": "test"})
    end_time = time.time()
    
    assert response.status_code == 200
    assert (end_time - start_time) < 5.0  # 5초 이내 응답
```

## 🚀 배포 및 운영

### 1. 프로덕션 환경 설정

```bash
# 환경 변수 설정
export PMARK_ENV=production
export OPENAI_API_KEY=your_production_key
export DATABASE_URL=postgresql://user:pass@host/db

# 의존성 설치
pip install -r requirements.txt
npm install --production
```

### 2. 서비스 실행

```bash
# 백엔드 서비스
uvicorn main:app --host 0.0.0.0 --port 8010 --workers 4

# 프론트엔드 서비스
node frontend/server.js
```

### 3. 모니터링

```python
# 로깅 설정
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

### 4. 헬스 체크

```python
@router.get("/health")
async def health_check():
    """시스템 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "services": {
            "database": check_database(),
            "vector_db": check_vector_db(),
            "llm": check_llm_service()
        }
    }
```

## 📚 추가 리소스

### 문서
- [시스템 아키텍처](SYSTEM_ARCHITECTURE.md)
- [API 문서](API_DOCUMENTATION.md)
- [빠른 시작 가이드](../QUICK_START.md)

### 예제 코드
- [테스트 스크립트](../test_autocomplete.py)
- [노트북 예제](../notebooks/)

### 도구
- [Swagger UI](http://localhost:8010/docs)
- [ReDoc](http://localhost:8010/redoc)

---

**PMark3 개발 가이드** - 세션 관리와 벡터 검색을 포함한 고급 AI 작업요청 생성 시스템을 개발하세요. 