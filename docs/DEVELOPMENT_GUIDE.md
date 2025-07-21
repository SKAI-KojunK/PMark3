# PMark2 개발 가이드

## 📋 목차

1. [개발 환경 설정](#개발-환경-설정)
2. [코드 구조 및 아키텍처](#코드-구조-및-아키텍처)
3. [컴포넌트별 수정 가이드](#컴포넌트별-수정-가이드)
4. [API 개발 가이드](#api-개발-가이드)
5. [데이터베이스 관리](#데이터베이스-관리)
6. [LLM 프롬프트 개발](#llm-프롬프트-개발)
7. [테스트 및 품질 관리](#테스트-및-품질-관리)
8. [배포 및 운영](#배포-및-운영)

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
cd PMark2-Dev

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
cd ../backend
python -c "from app.database import db_manager; db_manager.load_sample_data()"
```

### 개발 서버 실행

```bash
# 백엔드 (터미널 1)
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 프론트엔드 (터미널 2)
cd frontend
npm start
```

## 🏗️ 코드 구조 및 아키텍처

### 디렉토리 구조
```
backend/
├── app/
│   ├── __init__.py
│   ├── models.py              # 데이터 모델
│   ├── config.py              # 설정 관리
│   ├── database.py            # 데이터베이스 관리
│   ├── agents/
│   │   ├── __init__.py
│   │   └── parser.py          # 입력 파서
│   ├── logic/
│   │   ├── __init__.py
│   │   ├── normalizer.py      # LLM 정규화 엔진
│   │   └── recommender.py     # 추천 엔진
│   └── api/
│       ├── __init__.py
│       ├── chat.py            # 채팅 API
│       └── work_details.py    # 작업상세 API
├── data/                      # 데이터 파일
├── tests/                     # 테스트 코드
├── main.py                    # FastAPI 앱
└── requirements.txt           # 의존성
```

### 데이터 흐름
```
사용자 입력 → Parser → Normalizer → Recommender → Database → Response
     ↓
Work Details API → LLM → Finalize API → Database
```

## 🔧 컴포넌트별 수정 가이드

### 1. 입력 파서 (InputParser)

**파일**: `backend/app/agents/parser.py`

#### 주요 메서드
- `parse_input()`: 메인 파싱 로직
- `_determine_scenario()`: 시나리오 판단
- `_parse_scenario_1()`: 자연어 요청 파싱
- `_parse_scenario_2()`: ITEMNO 요청 파싱
- `_normalize_extracted_terms()`: 용어 정규화

#### 수정 시 주의사항
```python
# 새로운 시나리오 추가 시
def _determine_scenario(self, user_input: str) -> str:
    # 기존 로직...
    
    # 새로운 시나리오 조건 추가
    if new_condition:
        return "S3"
    
    return "default"

# 새로운 필드 추출 시
def _create_scenario_1_prompt(self, user_input: str) -> str:
    return f"""
    # 기존 필드...
    
    # 새로운 필드 추가
    5. new_field: 새로운 필드 설명
    
    # 응답 형식 업데이트
    ```json
    {{
        "location": "위치/공정",
        "equipment_type": "설비유형",
        "status_code": "현상코드",
        "priority": "우선순위",
        "new_field": "새로운 필드",  # 추가
        "confidence": 0.95
    }}
    ```
    """
```

#### 테스트 방법
```python
# 파서 테스트
from app.agents.parser import input_parser

# 시나리오 1 테스트
result = input_parser.parse_input("1PE 압력베젤 고장")
print(f"시나리오: {result.scenario}")
print(f"위치: {result.location}")
print(f"설비유형: {result.equipment_type}")

# 시나리오 2 테스트
result = input_parser.parse_input("ITEMNO 12345")
print(f"ITEMNO: {result.itemno}")
```

### 2. LLM 정규화 엔진 (LLMNormalizer)

**파일**: `backend/app/logic/normalizer.py`

#### 주요 메서드
- `normalize_term()`: 단일 용어 정규화
- `batch_normalize()`: 배치 정규화
- `get_similarity_score()`: 유사도 계산

#### 수정 시 주의사항
```python
# 새로운 카테고리 추가 시
class LLMNormalizer:
    def __init__(self):
        self.standard_terms = {
            "equipment": [...],
            "location": [...],
            "status": [...],
            "new_category": [  # 새로운 카테고리 추가
                "표준용어1",
                "표준용어2"
            ]
        }

# 정규화 품질 개선
def normalize_term(self, term: str, category: str) -> Tuple[str, float]:
    # 신뢰도 임계값 조정
    if confidence < 0.5:  # 0.3에서 0.5로 변경
        return term, confidence
```

#### 테스트 방법
```python
from app.logic.normalizer import normalizer

# 단일 용어 정규화 테스트
normalized, confidence = normalizer.normalize_term("압력베젤", "equipment")
print(f"정규화 결과: {normalized}, 신뢰도: {confidence}")

# 배치 정규화 테스트
terms = [("압력베젤", "equipment"), ("모터밸브", "equipment")]
results = normalizer.batch_normalize(terms)
```

### 3. 추천 엔진 (RecommendationEngine)

**파일**: `backend/app/logic/recommender.py`

#### 주요 메서드
- `get_recommendations()`: 추천 목록 생성
- `_generate_work_details()`: 작업상세 생성
- `get_recommendation_by_itemno()`: 특정 추천 조회

#### 수정 시 주의사항
```python
# 추천 알고리즘 개선
def get_recommendations(self, parsed_input: ParsedInput, limit: int = 5) -> List[Recommendation]:
    # 유사도 점수 임계값 조정
    if score > 0.5:  # 0.3에서 0.5로 변경
        recommendation = Recommendation(...)
        recommendations.append(recommendation)
    
    # 새로운 정렬 기준 추가
    recommendations.sort(key=lambda x: (x.score, x.priority), reverse=True)
```

#### 테스트 방법
```python
from app.logic.recommender import recommendation_engine
from app.models import ParsedInput

# 추천 생성 테스트
parsed_input = ParsedInput(
    scenario="S1",
    location="No.1 PE",
    equipment_type="Pressure Vessel",
    status_code="고장",
    priority="일반작업",
    confidence=0.9
)

recommendations = recommendation_engine.get_recommendations(parsed_input)
for rec in recommendations:
    print(f"ITEMNO: {rec.itemno}, 점수: {rec.score}")
```

### 4. 데이터베이스 관리 (DatabaseManager)

**파일**: `backend/app/database.py`

#### 주요 메서드
- `search_similar_notifications()`: 유사 알림 검색
- `calculate_similarity_score()`: 유사도 점수 계산
- `save_work_order()`: 작업요청 저장

#### 수정 시 주의사항
```python
# 새로운 검색 조건 추가
def search_similar_notifications(self, equip_type=None, location=None, 
                               status_code=None, process=None, 
                               new_field=None, limit=10):  # 새로운 필드 추가
    query = "SELECT * FROM notifications WHERE 1=1"
    params = []
    
    # 기존 조건...
    
    # 새로운 조건 추가
    if new_field:
        query += " AND new_field LIKE ?"
        params.append(f"%{new_field}%")
```

#### 테스트 방법
```python
from app.database import db_manager

# 검색 테스트
results = db_manager.search_similar_notifications(
    equip_type="Pressure Vessel",
    location="No.1 PE",
    status_code="고장"
)
print(f"검색 결과: {len(results)} 건")

# 유사도 계산 테스트
score = db_manager.calculate_similarity_score(
    "Pressure Vessel", "No.1 PE", "고장",
    "Pressure Vessel", "No.1 PE", "고장"
)
print(f"유사도 점수: {score}")
```

## 🔌 API 개발 가이드

### 1. 새로운 API 엔드포인트 추가

```python
# backend/app/api/new_api.py
from fastapi import APIRouter, HTTPException
from ..models import NewRequest, NewResponse
import logging

router = APIRouter(prefix="/api/v1", tags=["new-feature"])
logger = logging.getLogger(__name__)

@router.post("/new-endpoint", response_model=NewResponse)
async def new_endpoint(request: NewRequest):
    """
    새로운 API 엔드포인트
    
    Args:
        request: NewRequest - 요청 데이터
        
    Returns:
        NewResponse - 응답 데이터
        
    사용처:
    - frontend: 새로운 기능
    - 모바일 앱: 동일한 API 사용
        
    연계 파일:
    - models.py: NewRequest, NewResponse 모델 사용
    - logic/new_logic.py: 새로운 비즈니스 로직
    
    담당자 수정 가이드:
    - 에러 처리 로직 추가
    - 로깅 추가
    - 입력 검증 강화
    """
    try:
        logger.info(f"새로운 API 호출: {request}")
        
        # 비즈니스 로직 처리
        result = await process_new_logic(request)
        
        return NewResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"새로운 API 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류")
```

### 2. API 라우터 등록

```python
# backend/main.py
from app.api import chat, work_details, new_api  # 새로운 API 추가

app.include_router(chat.router)
app.include_router(work_details.router)
app.include_router(new_api.router)  # 새로운 라우터 등록
```

### 3. API 테스트

```python
# tests/test_new_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

class TestIntegration:
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_new_endpoint(self):
        response = self.client.post(
            "/api/v1/new-endpoint",
            json={"test_data": "test_value"}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
```

## 🗄️ 데이터베이스 관리

### 1. 스키마 변경

```python
# backend/app/database.py
def _init_database(self):
    """데이터베이스 초기화 및 테이블 생성"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            # 기존 테이블...
            
            # 새로운 테이블 추가
            conn.execute("""
                CREATE TABLE IF NOT EXISTS new_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 새로운 인덱스 추가
            conn.execute("CREATE INDEX IF NOT EXISTS idx_new_table_name ON new_table(name)")
            
    except Exception as e:
        self.logger.error(f"데이터베이스 초기화 오류: {e}")
        raise
```

### 2. 데이터 마이그레이션

```python
# backend/app/database.py
def migrate_data(self):
    """데이터 마이그레이션"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            # 기존 데이터 백업
            conn.execute("CREATE TABLE IF NOT EXISTS notifications_backup AS SELECT * FROM notifications")
            
            # 새로운 컬럼 추가
            conn.execute("ALTER TABLE notifications ADD COLUMN new_field TEXT")
            
            # 데이터 업데이트
            conn.execute("UPDATE notifications SET new_field = 'default_value' WHERE new_field IS NULL")
            
    except Exception as e:
        self.logger.error(f"데이터 마이그레이션 오류: {e}")
        raise
```

### 3. 성능 최적화

```python
# 인덱스 추가
conn.execute("CREATE INDEX IF NOT EXISTS idx_equipType_location ON notifications(equipType, location)")

# 쿼리 최적화
def optimized_search(self, equip_type=None, location=None):
    query = """
        SELECT * FROM notifications 
        WHERE (equipType = ? OR ? IS NULL)
        AND (location = ? OR ? IS NULL)
        ORDER BY created_at DESC
        LIMIT 10
    """
    params = [equip_type, equip_type, location, location]
```

## 🤖 LLM 프롬프트 개발

### 1. 프롬프트 작성 가이드

```python
def create_effective_prompt(self, context: str) -> str:
    """
    효과적인 프롬프트 작성
    
    구조:
    1. 역할 정의
    2. 컨텍스트 제공
    3. 구체적인 지시사항
    4. 예시 제공
    5. 응답 형식 명시
    6. 제약사항 명시
    """
    return f"""
당신은 설비관리 시스템의 전문가입니다.

**컨텍스트**:
{context}

**지시사항**:
1. 입력을 분석하여 구조화된 데이터로 변환
2. 표준 용어를 사용하여 정규화
3. 신뢰도 점수를 0.0~1.0 사이로 제공

**예시**:
입력: "압력베젤 고장"
출력: {{"equipment": "Pressure Vessel", "status": "고장", "confidence": 0.95}}

**응답 형식**:
```json
{{
    "field1": "value1",
    "field2": "value2",
    "confidence": 0.95
}}
```

**제약사항**:
- JSON 형식으로만 응답
- 신뢰도는 0.0~1.0 사이
- 표준 용어 사전만 사용
"""
```

### 2. 프롬프트 테스트

```python
def test_prompt(self, test_cases: List[Dict]) -> Dict:
    """프롬프트 테스트"""
    results = []
    
    for test_case in test_cases:
        prompt = self.create_prompt(test_case["input"])
        response = self.call_llm(prompt)
        parsed = self.parse_response(response)
        
        results.append({
            "input": test_case["input"],
            "expected": test_case["expected"],
            "actual": parsed,
            "match": parsed == test_case["expected"]
        })
    
    return {
        "total": len(results),
        "success": sum(1 for r in results if r["match"]),
        "results": results
    }
```

### 3. 프롬프트 버전 관리

```python
class PromptVersion:
    def __init__(self, version: str, prompt: str, performance: float):
        self.version = version
        self.prompt = prompt
        self.performance = performance
        self.created_at = datetime.now()

# 프롬프트 버전 관리
prompt_versions = {
    "v1.0": PromptVersion("v1.0", basic_prompt, 0.85),
    "v1.1": PromptVersion("v1.1", improved_prompt, 0.92),
    "v1.2": PromptVersion("v1.2", latest_prompt, 0.95)
}
```

## 🧪 테스트 및 품질 관리

### 1. 단위 테스트

```python
# tests/test_parser.py
import pytest
from app.agents.parser import InputParser

class TestInputParser:
    def setup_method(self):
        self.parser = InputParser()
    
    def test_scenario_1_parsing(self):
        """시나리오 1 파싱 테스트"""
        result = self.parser.parse_input("1PE 압력베젤 고장")
        
        assert result.scenario == "S1"
        assert result.location == "No.1 PE"
        assert result.equipment_type == "Pressure Vessel"
        assert result.status_code == "고장"
        assert result.confidence > 0.8
    
    def test_scenario_2_parsing(self):
        """시나리오 2 파싱 테스트"""
        result = self.parser.parse_input("ITEMNO 12345")
        
        assert result.scenario == "S2"
        assert result.itemno == "12345"
        assert result.confidence > 0.9
```

### 2. 통합 테스트

```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from main import app

class TestIntegration:
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        # 1. 채팅 요청
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "1PE 압력베젤 고장"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["recommendations"]) > 0
        
        # 2. 작업상세 생성
        recommendation = data["recommendations"][0]
        response = self.client.post(
            "/api/v1/generate-work-details",
            json={
                "selected_recommendation": recommendation,
                "user_message": "1PE 압력베젤 고장"
            }
        )
        assert response.status_code == 200
        
        # 3. 작업요청 완성
        work_details = response.json()
        response = self.client.post(
            "/api/v1/finalize-work-order",
            json={
                "work_title": work_details["work_title"],
                "work_details": work_details["work_details"],
                "selected_recommendation": recommendation,
                "user_message": "1PE 압력베젤 고장"
            }
        )
        assert response.status_code == 200
```

### 3. 성능 테스트

```python
# tests/test_performance.py
import time
import pytest
from app.logic.recommender import recommendation_engine

def test_recommendation_performance():
    """추천 성능 테스트"""
    start_time = time.time()
    
    # 대량의 추천 요청
    for i in range(100):
        parsed_input = ParsedInput(
            scenario="S1",
            location=f"Location {i}",
            equipment_type="Pressure Vessel",
            status_code="고장",
            confidence=0.9
        )
        recommendations = recommendation_engine.get_recommendations(parsed_input)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 성능 기준: 100개 요청이 10초 이내 완료
    assert total_time < 10.0
    print(f"100개 추천 요청 완료 시간: {total_time:.2f}초")
```

## 🚀 배포 및 운영

### 1. 환경별 설정

```python
# backend/app/config.py
import os
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Config:
    ENVIRONMENT = Environment(os.getenv("ENVIRONMENT", "development"))
    
    if ENVIRONMENT == Environment.DEVELOPMENT:
        DEBUG = True
        LOG_LEVEL = "DEBUG"
        DATABASE_URL = "sqlite:///./data/dev.db"
    elif ENVIRONMENT == Environment.STAGING:
        DEBUG = False
        LOG_LEVEL = "INFO"
        DATABASE_URL = os.getenv("STAGING_DATABASE_URL")
    else:  # PRODUCTION
        DEBUG = False
        LOG_LEVEL = "WARNING"
        DATABASE_URL = os.getenv("PRODUCTION_DATABASE_URL")
```

### 2. 로깅 설정

```python
# backend/app/logging_config.py
import logging
import logging.handlers
import os

def setup_logging():
    """로깅 설정"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 로그 포맷
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 파일 핸들러
    file_handler = logging.handlers.RotatingFileHandler(
        f"{log_dir}/app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
```

### 3. 모니터링

```python
# backend/app/monitoring.py
import time
import functools
from typing import Callable
import logging

logger = logging.getLogger(__name__)

def monitor_performance(func: Callable) -> Callable:
    """성능 모니터링 데코레이터"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(f"{func.__name__} 실행 시간: {execution_time:.3f}초")
            
            # 성능 임계값 체크
            if execution_time > 5.0:  # 5초 이상
                logger.warning(f"{func.__name__} 성능 저하 감지: {execution_time:.3f}초")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 오류 발생 ({execution_time:.3f}초): {e}")
            raise
    
    return wrapper

# 사용 예시
@monitor_performance
def slow_function():
    time.sleep(2)
    return "완료"
```

### 4. 헬스 체크

```python
# backend/app/api/health.py
from fastapi import APIRouter
from ..database import db_manager
import psutil
import os

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # 데이터베이스 연결 확인
        db_status = "healthy"
        try:
            db_manager.get_all_notifications(limit=1)
        except Exception as e:
            db_status = f"unhealthy: {e}"
        
        # 시스템 리소스 확인
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        return {
            "status": "healthy",
            "database": db_status,
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }
```

## 📚 추가 리소스

### 유용한 링크
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [OpenAI API 문서](https://platform.openai.com/docs)
- [SQLite 문서](https://www.sqlite.org/docs.html)
- [Pytest 문서](https://docs.pytest.org/)

### 개발 도구
- **API 테스트**: Postman, Insomnia
- **데이터베이스 관리**: DB Browser for SQLite
- **로깅 분석**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **모니터링**: Prometheus, Grafana

### 코드 품질 도구
- **린터**: flake8, black
- **타입 체크**: mypy
- **보안 검사**: bandit
- **테스트 커버리지**: coverage

---

이 가이드를 참고하여 PMark1 AI Assistant의 개발을 진행하시기 바랍니다. 추가 질문이나 개선 제안이 있으시면 개발팀에 연락해주세요. 