# PMark3 Production 마이그레이션 가이드

## 📋 개요

이 문서는 PMark3 프로토타입을 Production 환경으로 마이그레이션하기 위한 종합적인 가이드입니다. LangGraph Agent 전환, Azure 인프라 구축, 로컬 LLM 서빙, 벡터 DB 구현, 성능 평가 시스템 등을 다룹니다.

## 🎯 Production 전환 목표

### 1. LangGraph Agent 기반 아키텍처
- 현재 개별 함수들을 LangGraph의 노드와 엣지로 재구성
- 상태 관리와 워크플로우 최적화
- 복잡한 작업 흐름의 시각화 및 관리

### 2. Azure 인프라 구성
- Azure SQL Database와 연동
- Azure Container Instances 또는 AKS 배포
- Azure Cognitive Services 통합

### 3. 로컬 LLM 서빙
- vLLM 기반 Mistral 7B Instruct 또는 Qwen3 14B 서빙
- GPU 최적화 및 배치 처리
- API 게이트웨이 구성

### 4. 벡터 임베딩 시스템
- 설비유형, 위치, 작업상세 벡터 DB 구축
- 실시간 임베딩 생성 및 검색
- 정규화 정확도 향상

### 5. 성능 평가 시스템
- 실시간 모니터링 및 메트릭 수집
- A/B 테스트 프레임워크
- 자동화된 품질 평가

---

## 🏗️ LangGraph Agent 아키텍처 설계

### 1. 현재 구조 분석

```python
# 현재 프로토타입 구조 (순차적)
user_input → InputParser → Normalizer → Recommender → ResponseGenerator → response

# LangGraph 구조 (그래프 기반)
user_input → [StateManager] → [ParsingNode] → [NormalizationNode] → [RecommendationNode] → [ResponseNode] → response
              ↑                    ↓                ↓                     ↓                   ↓
              └─── [SessionNode] ←──┴──── [VectorSearchNode] ←─────────────┴─── [EvaluationNode]
```

### 2. LangGraph 노드 설계

#### StateManager (상태 관리자)
```python
# 목적: 전체 워크플로우의 상태 관리
# 현재 대응: session_manager.py
# Production 개선사항:
# - 분산 상태 관리 (Redis/Azure Cache)
# - 상태 영속성 보장
# - 복구 메커니즘 구현

class WorkflowState(TypedDict):
    user_input: str
    session_id: str
    parsed_data: Optional[ParsedInput]
    normalized_data: Optional[Dict]
    recommendations: Optional[List[Recommendation]]
    response: Optional[str]
    context: Dict[str, Any]
    metrics: Dict[str, float]
```

#### ParsingNode (파싱 노드)
```python
# 목적: 사용자 입력 파싱 및 정보 추출
# 현재 대응: agents/parser.py
# Production 개선사항:
# - 로컬 LLM 연동
# - 배치 처리 최적화
# - 실시간 성능 모니터링

def parsing_node(state: WorkflowState) -> WorkflowState:
    """
    파싱 노드 - 사용자 입력을 구조화된 데이터로 변환
    
    개발팀 참고사항:
    - vLLM 엔드포인트와 연동
    - 시나리오별 분기 로직 구현
    - 에러 핸들링 및 재시도 메커니즘
    """
    # 성능 측정 시작
    start_time = time.time()
    
    # 파싱 로직 실행
    parser = ProductionInputParser(llm_endpoint=state["config"]["vllm_endpoint"])
    parsed_data = parser.parse_with_context(
        user_input=state["user_input"],
        session_context=state["context"]
    )
    
    # 성능 메트릭 수집
    state["metrics"]["parsing_time"] = time.time() - start_time
    state["metrics"]["parsing_confidence"] = parsed_data.confidence
    
    state["parsed_data"] = parsed_data
    return state
```

### 3. 워크플로우 그래프 정의

```python
# LangGraph 워크플로우 구성
from langgraph.graph import StateGraph, END

def create_production_workflow():
    """
    Production용 LangGraph 워크플로우 생성
    
    AI 연구원 참고사항:
    - 각 노드는 독립적으로 테스트 가능
    - 조건부 분기로 다양한 시나리오 처리
    - 실시간 모니터링 포인트 포함
    """
    workflow = StateGraph(WorkflowState)
    
    # 노드 추가
    workflow.add_node("parse", parsing_node)
    workflow.add_node("normalize", normalization_node)
    workflow.add_node("search_vector", vector_search_node)
    workflow.add_node("recommend", recommendation_node)
    workflow.add_node("generate_response", response_generation_node)
    workflow.add_node("evaluate", evaluation_node)
    
    # 엣지 추가 (조건부 분기 포함)
    workflow.add_edge("parse", "normalize")
    workflow.add_conditional_edges(
        "normalize",
        should_use_vector_search,
        {
            "vector": "search_vector",
            "traditional": "recommend"
        }
    )
    workflow.add_edge("search_vector", "recommend")
    workflow.add_edge("recommend", "generate_response")
    workflow.add_edge("generate_response", "evaluate")
    workflow.add_edge("evaluate", END)
    
    # 시작점 설정
    workflow.set_entry_point("parse")
    
    return workflow.compile()
```

---

## 🔧 Azure 인프라 연동 설계

### 1. 데이터베이스 마이그레이션 (SQLite → Azure SQL)

#### 현재 구조 분석
```python
# 현재: backend/app/database.py
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect("./data/notifications.db")
    
    def search_similar_notifications(self, ...):
        # SQLite 전용 쿼리
        query = "SELECT ... FROM notification_history WHERE ..."
```

#### Production 구조 설계
```python
# Production: 추상화 계층 도입
from abc import ABC, abstractmethod
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DatabaseInterface(ABC):
    """
    데이터베이스 인터페이스 - 다양한 DB 지원
    
    개발팀 참고사항:
    - SQLite, Azure SQL, PostgreSQL 지원
    - 연결 풀링 및 트랜잭션 관리
    - 자동 재연결 및 장애 복구
    """
    
    @abstractmethod
    def search_similar_notifications(self, filters: Dict) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_standard_terms(self, category: str) -> List[str]:
        pass

class AzureSQLManager(DatabaseInterface):
    """
    Azure SQL Database 매니저
    
    AI 연구원 참고사항:
    - 기존 SQLite 쿼리를 T-SQL로 자동 변환
    - 인덱스 힌트 및 쿼리 최적화
    - 연결 상태 모니터링
    """
    
    def __init__(self, connection_string: str):
        self.engine = create_engine(
            connection_string,
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.Session = sessionmaker(bind=self.engine)
    
    def search_similar_notifications(self, filters: Dict) -> List[Dict]:
        """
        Azure SQL 최적화된 유사 알림 검색
        
        개선사항:
        - 인덱스 기반 검색 최적화
        - 병렬 쿼리 실행
        - 캐시 레이어 통합
        """
        with self.Session() as session:
            # T-SQL 최적화 쿼리
            query = text("""
                SELECT 
                    itemno, process, location, equipType, statusCode, 
                    work_title, work_details, priority,
                    -- 유사도 점수 계산을 SQL 레벨에서 수행
                    (
                        CASE WHEN location LIKE :location THEN 35 ELSE 0 END +
                        CASE WHEN equipType LIKE :equipment THEN 35 ELSE 0 END +
                        CASE WHEN statusCode LIKE :status THEN 20 ELSE 0 END +
                        CASE WHEN priority LIKE :priority THEN 10 ELSE 0 END
                    ) / 100.0 as similarity_score
                FROM notification_history 
                WHERE 
                    (:location IS NULL OR location LIKE :location OR process LIKE :location)
                    AND (:equipment IS NULL OR equipType LIKE :equipment)
                    AND (:status IS NULL OR statusCode LIKE :status)
                    AND (:priority IS NULL OR priority LIKE :priority)
                ORDER BY similarity_score DESC, created_at DESC
                LIMIT :limit
            """)
            
            result = session.execute(query, filters)
            return [dict(row) for row in result.fetchall()]
```

### 2. Azure 서비스 통합

```python
# Azure 서비스 연동 클래스
class AzureServiceIntegration:
    """
    Azure 클라우드 서비스 통합 관리자
    
    개발팀 참고사항:
    - Azure Key Vault를 통한 시크릿 관리
    - Azure Monitor를 통한 로깅 및 모니터링
    - Azure Service Bus를 통한 메시지 큐잉
    """
    
    def __init__(self, config: AzureConfig):
        self.key_vault_client = SecretClient(
            vault_url=config.key_vault_url,
            credential=DefaultAzureCredential()
        )
        self.monitor_client = MetricsQueryClient(DefaultAzureCredential())
        self.servicebus_client = ServiceBusClient.from_connection_string(
            config.servicebus_connection_string
        )
    
    async def get_secret(self, secret_name: str) -> str:
        """Azure Key Vault에서 시크릿 조회"""
        try:
            secret = await self.key_vault_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise
    
    async def send_metrics(self, metrics: Dict[str, float]):
        """Azure Monitor로 메트릭 전송"""
        # 성능 지표를 Azure Monitor로 전송
        pass
```

---

## 🤖 로컬 LLM 서빙 아키텍처

### 1. vLLM 서버 구성

```python
# vLLM 서버 설정 클래스
class vLLMServerConfig:
    """
    vLLM 서버 설정 관리
    
    AI 연구원 참고사항:
    - GPU 메모리 최적화 설정
    - 배치 크기 동적 조절
    - 모델별 최적 파라미터 관리
    """
    
    def __init__(self):
        self.models = {
            "mistral-7b": {
                "model_path": "/models/mistral-7b-instruct",
                "tensor_parallel_size": 1,
                "max_model_len": 4096,
                "gpu_memory_utilization": 0.9,
                "enforce_eager": False
            },
            "qwen3-14b": {
                "model_path": "/models/qwen3-14b-instruct", 
                "tensor_parallel_size": 2,
                "max_model_len": 8192,
                "gpu_memory_utilization": 0.85,
                "enforce_eager": True
            }
        }
    
    def get_optimal_config(self, model_name: str, available_gpus: int) -> Dict:
        """
        하드웨어 리소스에 따른 최적 설정 반환
        
        개발팀 참고사항:
        - GPU 수에 따른 병렬 처리 설정
        - 메모리 사용량 모니터링 및 조절
        - 동적 배치 크기 조절
        """
        base_config = self.models.get(model_name, self.models["mistral-7b"])
        
        # GPU 수에 따른 병렬 처리 조절
        if available_gpus >= base_config["tensor_parallel_size"]:
            return base_config
        else:
            # GPU가 부족한 경우 단일 GPU 설정으로 폴백
            return {**base_config, "tensor_parallel_size": 1}

class LocalLLMClient:
    """
    로컬 LLM 클라이언트 - vLLM 서버와 통신
    
    현재 대응: OpenAI 클라이언트 호출 부분
    Production 개선사항:
    - 연결 풀링 및 재사용
    - 자동 재연결 및 장애 조치
    - 배치 처리 최적화
    """
    
    def __init__(self, vllm_endpoint: str, model_name: str):
        self.endpoint = vllm_endpoint
        self.model_name = model_name
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=100)
        )
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """
        로컬 LLM을 통한 텍스트 생성
        
        AI 연구원 참고사항:
        - 프롬프트 템플릿 자동 적용
        - 토큰 수 제한 관리
        - 스트리밍 응답 지원
        """
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.1),
            "stream": kwargs.get("stream", False)
        }
        
        try:
            async with self.session.post(
                f"{self.endpoint}/v1/chat/completions",
                json=payload
            ) as response:
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"vLLM request failed: {e}")
            raise
```

### 2. LLM 호출 최적화

```python
class OptimizedLLMService:
    """
    최적화된 LLM 서비스 - 배치 처리 및 캐싱
    
    개발팀 참고사항:
    - 요청 배치 처리로 처리량 향상
    - 응답 캐싱으로 중복 요청 최적화
    - 우선순위 기반 큐 관리
    """
    
    def __init__(self, llm_client: LocalLLMClient):
        self.llm_client = llm_client
        self.request_queue = asyncio.Queue()
        self.response_cache = TTLCache(maxsize=1000, ttl=3600)
        self.batch_size = 8
        self.batch_timeout = 0.1
    
    async def process_batch_requests(self):
        """
        배치 요청 처리 - 처리량 최적화
        
        AI 연구원 참고사항:
        - 동일한 타입의 요청을 배치로 처리
        - GPU 활용률 최적화
        - 응답 시간과 처리량의 균형
        """
        while True:
            batch = []
            try:
                # 배치 수집 (타임아웃 또는 배치 크기 도달까지)
                batch.append(await asyncio.wait_for(
                    self.request_queue.get(), 
                    timeout=self.batch_timeout
                ))
                
                # 추가 요청 수집
                for _ in range(self.batch_size - 1):
                    try:
                        batch.append(await asyncio.wait_for(
                            self.request_queue.get(), 
                            timeout=0.01
                        ))
                    except asyncio.TimeoutError:
                        break
                
                # 배치 처리 실행
                await self._process_batch(batch)
                
            except asyncio.TimeoutError:
                if batch:
                    await self._process_batch(batch)
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
    
    async def _process_batch(self, batch: List[Tuple]):
        """배치 처리 실행"""
        # 병렬 LLM 호출
        tasks = [
            self.llm_client.generate(prompt, **kwargs) 
            for prompt, kwargs, future in batch
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 반환
        for (prompt, kwargs, future), result in zip(batch, results):
            if isinstance(result, Exception):
                future.set_exception(result)
            else:
                future.set_result(result)
                # 캐시 저장
                cache_key = hash(prompt + str(kwargs))
                self.response_cache[cache_key] = result
```

---

## 🔍 벡터 임베딩 시스템 설계

### 1. 현재 구조와 비교

#### 현재 정규화 방식
```python
# 현재: backend/app/logic/normalizer.py
class LLMNormalizer:
    def normalize_term(self, term: str, category: str) -> Tuple[str, float]:
        """
        LLM 기반 용어 정규화
        
        한계점:
        - LLM 호출로 인한 지연 시간
        - 일관성 부족 (같은 입력에 다른 결과)
        - 표준 용어 DB에 의존적
        - 의미적 유사성 미반영
        """
        # DB에서 표준 용어 로드
        db_terms = self._get_db_terms(category)
        
        # LLM 프롬프트 생성 및 호출
        prompt = self._create_normalization_prompt(term, db_terms, category)
        result = self.client.chat.completions.create(...)
        
        return normalized_term, confidence
```

#### Production 벡터 기반 정규화
```python
class VectorBasedNormalizer:
    """
    벡터 임베딩 기반 정규화 엔진
    
    개선사항:
    - 실시간 의미적 유사성 계산
    - 일관된 정규화 결과
    - 새로운 용어 자동 학습
    - 다국어 지원 향상
    """
    
    def __init__(self, vector_db: VectorDatabase, embedding_model: str):
        self.vector_db = vector_db
        self.embedding_model = SentenceTransformer(embedding_model)
        self.similarity_threshold = 0.85
        
    async def normalize_term(self, term: str, category: str) -> Tuple[str, float]:
        """
        벡터 유사성 기반 용어 정규화
        
        AI 연구원 참고사항:
        - 임베딩 모델 교체 가능한 구조
        - 유사도 임계값 동적 조절
        - 실시간 학습 데이터 수집
        """
        # 입력 용어 임베딩 생성
        term_embedding = self.embedding_model.encode(term)
        
        # 벡터 DB에서 유사 용어 검색
        similar_terms = await self.vector_db.search(
            embedding=term_embedding,
            collection=f"standard_terms_{category}",
            top_k=5,
            threshold=self.similarity_threshold
        )
        
        if similar_terms:
            # 가장 유사한 표준 용어 반환
            best_match = similar_terms[0]
            confidence = best_match.similarity
            
            # 학습 데이터로 활용
            await self._log_normalization_result(term, best_match.text, confidence)
            
            return best_match.text, confidence
        else:
            # 표준 용어가 없는 경우 LLM 폴백
            return await self._llm_fallback_normalization(term, category)
    
    async def _log_normalization_result(self, original: str, normalized: str, confidence: float):
        """
        정규화 결과 로깅 - 지속적 학습용
        
        개발팀 참고사항:
        - 사용자 피드백 수집
        - 모델 재학습 데이터 축적
        - 성능 개선 지표 생성
        """
        log_entry = {
            "timestamp": datetime.utcnow(),
            "original_term": original,
            "normalized_term": normalized,
            "confidence": confidence,
            "model_version": self.embedding_model.get_model_name()
        }
        
        # 비동기 로깅 (성능 영향 최소화)
        await self.logger.log_async(log_entry)
```

### 2. 벡터 데이터베이스 구현

```python
class ProductionVectorDatabase:
    """
    Production용 벡터 데이터베이스
    
    AI 연구원 참고사항:
    - 다양한 벡터 DB 백엔드 지원 (FAISS, Qdrant, Weaviate)
    - 실시간 인덱싱 및 검색
    - 스케일링 및 샤딩 지원
    """
    
    def __init__(self, config: VectorDBConfig):
        self.config = config
        self.backend = self._initialize_backend()
        self.collections = {}
    
    def _initialize_backend(self):
        """벡터 DB 백엔드 초기화"""
        if self.config.backend == "qdrant":
            from qdrant_client import QdrantClient
            return QdrantClient(
                host=self.config.host,
                port=self.config.port,
                api_key=self.config.api_key
            )
        elif self.config.backend == "weaviate":
            import weaviate
            return weaviate.Client(
                url=self.config.url,
                auth_client_secret=weaviate.AuthApiKey(api_key=self.config.api_key)
            )
        else:  # FAISS 기본값
            import faiss
            return faiss.IndexFlatIP(self.config.dimension)
    
    async def create_collection(self, name: str, schema: Dict):
        """
        컬렉션 생성 - 카테고리별 벡터 저장소
        
        개발팀 참고사항:
        - 스키마 기반 데이터 검증
        - 인덱스 타입 최적화
        - 백업 및 복구 지원
        """
        if self.config.backend == "qdrant":
            await self.backend.recreate_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=self.config.dimension,
                    distance=models.Distance.COSINE
                )
            )
        
        self.collections[name] = schema
        logger.info(f"Created collection: {name}")
    
    async def upsert_vectors(self, collection: str, vectors: List[VectorData]):
        """
        벡터 데이터 삽입/업데이트
        
        AI 연구원 참고사항:
        - 배치 처리로 성능 최적화
        - 중복 데이터 처리
        - 메타데이터 인덱싱
        """
        if self.config.backend == "qdrant":
            points = [
                models.PointStruct(
                    id=vector.id,
                    vector=vector.embedding,
                    payload=vector.metadata
                )
                for vector in vectors
            ]
            
            await self.backend.upsert(
                collection_name=collection,
                points=points
            )
    
    async def search(self, 
                    embedding: List[float], 
                    collection: str, 
                    top_k: int = 10, 
                    threshold: float = 0.8,
                    filters: Optional[Dict] = None) -> List[SearchResult]:
        """
        벡터 유사성 검색
        
        성능 최적화:
        - 하이브리드 검색 (벡터 + 키워드)
        - 필터링 조건 최적화
        - 결과 캐싱
        """
        if self.config.backend == "qdrant":
            search_result = await self.backend.search(
                collection_name=collection,
                query_vector=embedding,
                limit=top_k,
                score_threshold=threshold,
                query_filter=self._convert_filters(filters) if filters else None
            )
            
            return [
                SearchResult(
                    id=hit.id,
                    text=hit.payload.get("text", ""),
                    similarity=hit.score,
                    metadata=hit.payload
                )
                for hit in search_result
                if hit.score >= threshold
            ]
```

### 3. 임베딩 서비스

```python
class EmbeddingService:
    """
    임베딩 생성 및 관리 서비스
    
    개발팀 참고사항:
    - 다중 모델 지원 (Sentence Transformers, OpenAI, Cohere)
    - 배치 처리 및 캐싱
    - 모델 버전 관리
    """
    
    def __init__(self, config: EmbeddingConfig):
        self.models = {}
        self.cache = EmbeddingCache(max_size=10000)
        self.load_models(config.models)
    
    def load_models(self, model_configs: List[ModelConfig]):
        """다중 임베딩 모델 로딩"""
        for config in model_configs:
            if config.provider == "sentence_transformers":
                model = SentenceTransformer(config.model_name)
                if config.gpu_device >= 0:
                    model = model.to(f"cuda:{config.gpu_device}")
                self.models[config.name] = model
            elif config.provider == "openai":
                self.models[config.name] = OpenAIEmbedding(config.api_key)
    
    async def encode_batch(self, 
                          texts: List[str], 
                          model_name: str = "default",
                          normalize: bool = True) -> List[List[float]]:
        """
        배치 임베딩 생성
        
        AI 연구원 참고사항:
        - GPU 메모리 최적화
        - 동적 배치 크기 조절
        - 실패 시 재시도 메커니즘
        """
        # 캐시 확인
        cache_keys = [f"{model_name}:{hash(text)}" for text in texts]
        cached_results = []
        uncached_texts = []
        uncached_indices = []
        
        for i, (text, cache_key) in enumerate(zip(texts, cache_keys)):
            cached_embedding = self.cache.get(cache_key)
            if cached_embedding is not None:
                cached_results.append((i, cached_embedding))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # 캐시되지 않은 텍스트만 처리
        if uncached_texts:
            model = self.models[model_name]
            embeddings = model.encode(
                uncached_texts,
                batch_size=32,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            
            # 캐시에 저장
            for text, embedding, cache_key in zip(uncached_texts, embeddings, 
                                                 [cache_keys[i] for i in uncached_indices]):
                self.cache.set(cache_key, embedding.tolist())
        
        # 결과 재조립
        results = [None] * len(texts)
        for i, embedding in cached_results:
            results[i] = embedding
        for i, embedding in zip(uncached_indices, embeddings):
            results[i] = embedding.tolist()
        
        return results
```

---

## 📊 성능 평가 시스템 설계

### 1. 파싱 로직 평가

```python
class ParsingEvaluator:
    """
    파싱 로직 성능 평가기
    
    AI 연구원 참고사항:
    - 정확도, 재현율, F1 스코어 계산
    - 시나리오별 성능 분석
    - 실시간 성능 모니터링
    """
    
    def __init__(self, ground_truth_dataset: str):
        self.ground_truth = self.load_ground_truth(ground_truth_dataset)
        self.metrics_collector = MetricsCollector()
    
    async def evaluate_parsing_accuracy(self, 
                                       parser: InputParser, 
                                       test_cases: List[TestCase]) -> EvaluationReport:
        """
        파싱 정확도 평가
        
        개발팀 참고사항:
        - A/B 테스트 지원
        - 실시간 평가 결과 수집
        - 자동 알림 시스템 연동
        """
        results = []
        total_time = 0
        
        for test_case in test_cases:
            start_time = time.time()
            
            # 파싱 실행
            parsed_result = await parser.parse_input_with_context(
                user_input=test_case.input,
                conversation_history=test_case.history,
                session_id=test_case.session_id
            )
            
            parsing_time = time.time() - start_time
            total_time += parsing_time
            
            # 정확도 계산
            accuracy_score = self._calculate_parsing_accuracy(
                parsed_result, test_case.expected_output
            )
            
            results.append(ParsingResult(
                test_case_id=test_case.id,
                accuracy=accuracy_score,
                parsing_time=parsing_time,
                confidence=parsed_result.confidence,
                scenario=parsed_result.scenario
            ))
        
        # 종합 평가 리포트 생성
        report = EvaluationReport(
            parser_version=parser.get_version(),
            test_cases_count=len(test_cases),
            average_accuracy=np.mean([r.accuracy for r in results]),
            average_parsing_time=total_time / len(test_cases),
            scenario_breakdown=self._analyze_by_scenario(results),
            timestamp=datetime.utcnow()
        )
        
        # 메트릭 수집
        await self.metrics_collector.record_evaluation(report)
        
        return report
    
    def _calculate_parsing_accuracy(self, 
                                   parsed: ParsedInput, 
                                   expected: ParsedInput) -> float:
        """
        파싱 결과 정확도 계산
        
        평가 기준:
        - 필드별 가중치 적용
        - 부분 매칭 점수 반영
        - 신뢰도 점수 조합
        """
        scores = []
        weights = {"location": 0.3, "equipment_type": 0.3, "status_code": 0.25, "priority": 0.15}
        
        for field, weight in weights.items():
            parsed_value = getattr(parsed, field, None)
            expected_value = getattr(expected, field, None)
            
            if parsed_value == expected_value:
                scores.append(1.0 * weight)
            elif parsed_value and expected_value:
                # 부분 매칭 점수
                similarity = SequenceMatcher(None, 
                                           str(parsed_value).lower(), 
                                           str(expected_value).lower()).ratio()
                scores.append(similarity * weight)
            else:
                scores.append(0.0)
        
        return sum(scores)
```

### 2. 추천 로직 평가

```python
class RecommendationEvaluator:
    """
    추천 로직 성능 평가기
    
    AI 연구원 참고사항:
    - 추천 정확도 (Precision@K, Recall@K)
    - 다양성 지표 (Diversity, Coverage)
    - 사용자 만족도 예측
    """
    
    def __init__(self, recommendation_engine: RecommendationEngine):
        self.engine = recommendation_engine
        self.evaluation_metrics = RecommendationMetrics()
    
    async def evaluate_recommendation_quality(self, 
                                            test_queries: List[QueryTestCase]) -> RecommendationReport:
        """
        추천 품질 평가
        
        개발팀 참고사항:
        - 다중 평가 지표 동시 계산
        - 시간대별 성능 변화 추적
        - 실사용자 피드백 반영
        """
        results = []
        
        for query_case in test_queries:
            start_time = time.time()
            
            # 추천 생성
            recommendations = await self.engine.get_recommendations(
                parsed_input=query_case.parsed_input,
                limit=10
            )
            
            recommendation_time = time.time() - start_time
            
            # 다중 지표 계산
            metrics = await self._calculate_recommendation_metrics(
                recommendations=recommendations,
                relevant_items=query_case.relevant_items,
                query_context=query_case.context
            )
            
            results.append(RecommendationResult(
                query_id=query_case.id,
                metrics=metrics,
                recommendation_time=recommendation_time,
                recommendation_count=len(recommendations)
            ))
        
        # 종합 리포트 생성
        report = RecommendationReport(
            engine_version=self.engine.get_version(),
            evaluation_timestamp=datetime.utcnow(),
            query_count=len(test_queries),
            average_precision_at_5=np.mean([r.metrics.precision_at_5 for r in results]),
            average_recall_at_5=np.mean([r.metrics.recall_at_5 for r in results]),
            average_recommendation_time=np.mean([r.recommendation_time for r in results]),
            diversity_score=np.mean([r.metrics.diversity for r in results])
        )
        
        return report
    
    async def _calculate_recommendation_metrics(self, 
                                              recommendations: List[Recommendation],
                                              relevant_items: List[str],
                                              query_context: Dict) -> RecommendationMetrics:
        """추천 지표 계산"""
        recommended_ids = [rec.itemno for rec in recommendations]
        
        # Precision@K 계산
        precision_at_5 = len(set(recommended_ids[:5]) & set(relevant_items)) / min(5, len(recommended_ids))
        precision_at_10 = len(set(recommended_ids[:10]) & set(relevant_items)) / min(10, len(recommended_ids))
        
        # Recall@K 계산
        recall_at_5 = len(set(recommended_ids[:5]) & set(relevant_items)) / len(relevant_items) if relevant_items else 0
        recall_at_10 = len(set(recommended_ids[:10]) & set(relevant_items)) / len(relevant_items) if relevant_items else 0
        
        # 다양성 점수 계산
        diversity = self._calculate_diversity(recommendations)
        
        return RecommendationMetrics(
            precision_at_5=precision_at_5,
            precision_at_10=precision_at_10,
            recall_at_5=recall_at_5,
            recall_at_10=recall_at_10,
            diversity=diversity,
            average_score=np.mean([rec.score for rec in recommendations])
        )
```

### 3. 벡터 임베딩 평가

```python
class VectorEmbeddingEvaluator:
    """
    벡터 임베딩 시스템 평가기
    
    AI 연구원 참고사항:
    - 임베딩 품질 평가 (코사인 유사도, 군집화 성능)
    - 검색 성능 평가 (검색 속도, 정확도)
    - 모델 비교 평가
    """
    
    def __init__(self, vector_db: ProductionVectorDatabase, embedding_service: EmbeddingService):
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.benchmark_datasets = self.load_benchmark_datasets()
    
    async def evaluate_embedding_quality(self, 
                                        model_name: str, 
                                        test_datasets: List[EmbeddingTestSet]) -> EmbeddingReport:
        """
        임베딩 품질 종합 평가
        
        개발팀 참고사항:
        - 다중 평가 데이터셋 지원
        - 실시간 평가 결과 비교
        - 모델 교체 의사결정 지원
        """
        evaluation_results = []
        
        for dataset in test_datasets:
            # 임베딩 생성
            embeddings = await self.embedding_service.encode_batch(
                texts=dataset.texts,
                model_name=model_name
            )
            
            # 유사도 평가
            similarity_scores = self._evaluate_similarity_quality(
                embeddings=embeddings,
                similarity_pairs=dataset.similarity_pairs
            )
            
            # 검색 성능 평가
            search_performance = await self._evaluate_search_performance(
                embeddings=embeddings,
                queries=dataset.search_queries,
                model_name=model_name
            )
            
            # 군집화 성능 평가
            clustering_performance = self._evaluate_clustering_quality(
                embeddings=embeddings,
                true_labels=dataset.labels
            )
            
            evaluation_results.append(EmbeddingDatasetResult(
                dataset_name=dataset.name,
                similarity_correlation=similarity_scores.correlation,
                search_accuracy=search_performance.accuracy,
                clustering_score=clustering_performance.adjusted_rand_score,
                embedding_dimension=len(embeddings[0]) if embeddings else 0
            ))
        
        # 종합 점수 계산
        overall_score = self._calculate_overall_embedding_score(evaluation_results)
        
        return EmbeddingReport(
            model_name=model_name,
            evaluation_timestamp=datetime.utcnow(),
            dataset_results=evaluation_results,
            overall_score=overall_score,
            performance_summary=self._generate_performance_summary(evaluation_results)
        )
    
    async def _evaluate_search_performance(self, 
                                         embeddings: List[List[float]], 
                                         queries: List[SearchQuery],
                                         model_name: str) -> SearchPerformanceResult:
        """벡터 검색 성능 평가"""
        search_times = []
        accuracy_scores = []
        
        for query in queries:
            start_time = time.time()
            
            # 쿼리 임베딩 생성
            query_embedding = await self.embedding_service.encode_batch(
                texts=[query.text],
                model_name=model_name
            )
            
            # 벡터 검색 실행
            search_results = await self.vector_db.search(
                embedding=query_embedding[0],
                collection=query.collection,
                top_k=query.top_k,
                threshold=query.threshold
            )
            
            search_time = time.time() - start_time
            search_times.append(search_time)
            
            # 검색 정확도 계산
            relevant_ids = set(query.relevant_document_ids)
            retrieved_ids = set([result.id for result in search_results])
            
            precision = len(relevant_ids & retrieved_ids) / len(retrieved_ids) if retrieved_ids else 0
            recall = len(relevant_ids & retrieved_ids) / len(relevant_ids) if relevant_ids else 0
            f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            accuracy_scores.append(f1_score)
        
        return SearchPerformanceResult(
            average_search_time=np.mean(search_times),
            accuracy=np.mean(accuracy_scores),
            queries_per_second=1.0 / np.mean(search_times) if search_times else 0
        )
```

### 4. 전체 시스템 성능 모니터링

```python
class SystemPerformanceMonitor:
    """
    전체 시스템 성능 모니터링
    
    개발팀 참고사항:
    - 실시간 성능 지표 수집
    - 알람 및 자동 스케일링 연동
    - 성능 병목 지점 자동 탐지
    """
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.metrics_collector = MetricsCollector()
        self.alerting_system = AlertingSystem(config.alert_config)
        self.performance_baseline = self.load_baseline_metrics()
    
    async def monitor_request_pipeline(self, 
                                     user_input: str, 
                                     session_id: str) -> PipelineMetrics:
        """
        요청 파이프라인 전체 성능 모니터링
        
        AI 연구원 참고사항:
        - 각 단계별 성능 측정
        - 메모리 사용량 추적
        - 에러율 및 재시도 횟수 기록
        """
        pipeline_start = time.time()
        metrics = PipelineMetrics(request_id=str(uuid.uuid4()))
        
        try:
            # 1. 파싱 단계
            parsing_start = time.time()
            parsed_input = await self._monitor_parsing_stage(user_input, session_id)
            metrics.parsing_time = time.time() - parsing_start
            
            # 2. 정규화 단계
            normalization_start = time.time()
            normalized_data = await self._monitor_normalization_stage(parsed_input)
            metrics.normalization_time = time.time() - normalization_start
            
            # 3. 벡터 검색 단계 (활성화된 경우)
            if self.config.vector_search_enabled:
                vector_search_start = time.time()
                vector_results = await self._monitor_vector_search_stage(normalized_data)
                metrics.vector_search_time = time.time() - vector_search_start
            
            # 4. 추천 단계
            recommendation_start = time.time()
            recommendations = await self._monitor_recommendation_stage(normalized_data)
            metrics.recommendation_time = time.time() - recommendation_start
            
            # 5. 응답 생성 단계
            response_start = time.time()
            response = await self._monitor_response_generation_stage(recommendations)
            metrics.response_generation_time = time.time() - response_start
            
            # 전체 파이프라인 시간
            metrics.total_pipeline_time = time.time() - pipeline_start
            
            # 메모리 사용량 수집
            metrics.memory_usage = self._get_current_memory_usage()
            
            # 성능 기준선과 비교
            performance_status = self._compare_with_baseline(metrics)
            
            # 알람 체크
            if performance_status.requires_alert:
                await self.alerting_system.send_performance_alert(metrics, performance_status)
            
            # 메트릭 저장
            await self.metrics_collector.store_pipeline_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            metrics.error_occurred = True
            metrics.error_message = str(e)
            metrics.total_pipeline_time = time.time() - pipeline_start
            
            await self.alerting_system.send_error_alert(metrics, e)
            raise
    
    async def _monitor_parsing_stage(self, user_input: str, session_id: str) -> ParsedInput:
        """파싱 단계 모니터링"""
        with self.metrics_collector.timer("parsing_stage"):
            parser = InputParser()
            return await parser.parse_input_with_context(user_input, [], session_id)
    
    def _compare_with_baseline(self, metrics: PipelineMetrics) -> PerformanceStatus:
        """성능 기준선과 비교"""
        status = PerformanceStatus()
        
        # 파싱 시간 체크
        if metrics.parsing_time > self.performance_baseline.parsing_time * 1.5:
            status.parsing_slow = True
            status.requires_alert = True
        
        # 전체 응답 시간 체크
        if metrics.total_pipeline_time > self.performance_baseline.total_time * 2.0:
            status.overall_slow = True
            status.requires_alert = True
        
        # 메모리 사용량 체크
        if metrics.memory_usage > self.performance_baseline.memory_usage * 1.8:
            status.memory_high = True
            status.requires_alert = True
        
        return status
    
    async def generate_performance_report(self, 
                                        time_range: TimeRange) -> PerformanceReport:
        """
        성능 분석 리포트 생성
        
        개발팀 참고사항:
        - 시간대별 성능 트렌드 분석
        - 병목 지점 자동 식별
        - 최적화 권장사항 생성
        """
        metrics_data = await self.metrics_collector.get_metrics_in_range(time_range)
        
        # 평균 성능 지표 계산
        avg_metrics = self._calculate_average_metrics(metrics_data)
        
        # 성능 트렌드 분석
        trends = self._analyze_performance_trends(metrics_data)
        
        # 병목 지점 식별
        bottlenecks = self._identify_bottlenecks(metrics_data)
        
        # 권장사항 생성
        recommendations = self._generate_optimization_recommendations(
            avg_metrics, trends, bottlenecks
        )
        
        return PerformanceReport(
            time_range=time_range,
            total_requests=len(metrics_data),
            average_metrics=avg_metrics,
            performance_trends=trends,
            identified_bottlenecks=bottlenecks,
            optimization_recommendations=recommendations,
            generated_at=datetime.utcnow()
        )
```

---

## 👥 역할별 개발 가이드

### AI 연구원 (프로젝트팀) 가이드

#### 1. 파일 및 클래스 연계 관계

```python
"""
AI 연구원을 위한 코드 구조 가이드

=== 핵심 파일 구조 ===
backend/app/
├── agents/
│   └── parser.py          # 사용자 입력 파싱 (시나리오 1, 2 분기)
├── logic/
│   ├── normalizer.py      # 용어 정규화 (LLM 기반 → 벡터 기반 전환 예정)
│   └── recommender.py     # 추천 엔진 (유사도 계산 및 추천 생성)
├── database.py            # 데이터베이스 연동 (SQLite → Azure SQL 전환 예정)
├── session_manager.py     # 세션 관리 (대화 컨텍스트 유지)
└── models.py             # 데이터 모델 정의

=== 연계 관계 ===
1. 사용자 입력 → parser.py → normalizer.py → recommender.py → 응답
2. 세션 관리: session_manager.py가 모든 단계에서 컨텍스트 제공
3. 데이터 접근: database.py가 모든 모듈에서 공통 사용
"""

# 예시: 파싱 로직 실험 및 개선
class ParsingExperiment:
    """
    AI 연구원을 위한 파싱 로직 실험 클래스
    
    실험 가능한 영역:
    1. 프롬프트 엔지니어링 개선
    2. LLM 모델 교체 테스트
    3. 시나리오 분기 로직 개선
    4. 성능 벤치마킹
    """
    
    def __init__(self):
        # 현재 프로덕션 파서 로드
        self.production_parser = InputParser()
        
        # 실험용 파서 설정
        self.experimental_parsers = {
            "gpt4": self._create_gpt4_parser(),
            "local_mistral": self._create_local_llm_parser("mistral-7b"),
            "local_qwen": self._create_local_llm_parser("qwen3-14b")
        }
    
    def compare_parsing_models(self, test_inputs: List[str]) -> ComparisonReport:
        """
        다양한 파싱 모델 성능 비교
        
        사용법:
        1. test_inputs에 다양한 사용자 입력 준비
        2. 각 모델별 파싱 결과 및 성능 비교
        3. 결과 분석 및 최적 모델 선택
        
        주의사항:
        - 실제 프로덕션 코드 수정 없이 실험만 진행
        - 결과가 우수한 경우 개발팀과 협의 후 적용
        """
        results = {}
        
        for model_name, parser in self.experimental_parsers.items():
            model_results = []
            
            for user_input in test_inputs:
                start_time = time.time()
                parsed_result = parser.parse_input(user_input)
                parsing_time = time.time() - start_time
                
                model_results.append({
                    "input": user_input,
                    "parsed_result": parsed_result,
                    "parsing_time": parsing_time,
                    "confidence": parsed_result.confidence
                })
            
            results[model_name] = model_results
        
        return self._generate_comparison_report(results)
```

#### 2. 실험 워크플로우 가이드

```python
"""
AI 연구원 실험 워크플로우

=== 단계별 실험 가이드 ===

1. 데이터 준비 단계
   - notebooks/에서 실험용 데이터셋 준비
   - 실제 사용자 입력 샘플 수집
   - Ground Truth 데이터 생성

2. 모델 실험 단계
   - 노트북에서 개별 모듈 테스트
   - 성능 지표 수집 및 분석
   - 하이퍼파라미터 튜닝

3. 통합 테스트 단계
   - 전체 파이프라인 성능 테스트
   - A/B 테스트 설계 및 실행
   - 사용자 피드백 수집

4. 프로덕션 반영 단계
   - 개발팀과 결과 공유
   - 코드 리뷰 및 통합 계획 수립
   - 점진적 배포 전략 수립
"""

class ExperimentTracker:
    """
    실험 추적 및 관리 클래스
    
    목적: AI 연구원의 실험 결과를 체계적으로 관리
    """
    
    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.results = []
        self.metadata = {
            "created_at": datetime.utcnow(),
            "researcher": os.getenv("USER", "unknown"),
            "version": self._get_current_version()
        }
    
    def log_experiment(self, 
                      module: str, 
                      configuration: Dict, 
                      metrics: Dict,
                      notes: str = ""):
        """
        실험 결과 로깅
        
        사용법:
        tracker.log_experiment(
            module="parser",
            configuration={"model": "gpt-4", "temperature": 0.1},
            metrics={"accuracy": 0.95, "speed": 1.2},
            notes="프롬프트 최적화 후 정확도 5% 향상"
        )
        """
        experiment_result = {
            "timestamp": datetime.utcnow(),
            "module": module,
            "configuration": configuration,
            "metrics": metrics,
            "notes": notes
        }
        
        self.results.append(experiment_result)
        
        # 자동 저장 (실험 결과 손실 방지)
        self._save_to_file()
    
    def compare_experiments(self, metric_name: str) -> DataFrame:
        """실험 결과 비교 분석"""
        df = pd.DataFrame(self.results)
        return df.groupby('module')[f'metrics.{metric_name}'].describe()
    
    def _save_to_file(self):
        """실험 결과를 JSON 파일로 저장"""
        filename = f"experiments/{self.experiment_name}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump({
                "metadata": self.metadata,
                "results": self.results
            }, f, indent=2, default=str)
```

### 개발팀 가이드

#### 1. LangGraph 아키텍처 구현 가이드

```python
"""
개발팀을 위한 LangGraph 마이그레이션 가이드

=== 아키텍처 설계 원칙 ===
1. 현재 함수 기반 → 그래프 노드 기반 전환
2. 상태 관리 중앙화 (StateManager)
3. 조건부 분기를 통한 다양한 시나리오 처리
4. 실시간 모니터링 및 메트릭 수집

=== 주요 구현 포인트 ===
"""

class ProductionWorkflowBuilder:
    """
    Production용 LangGraph 워크플로우 빌더
    
    개발팀 주의사항:
    1. 각 노드는 독립적으로 스케일 가능해야 함
    2. 상태는 Redis/Azure Cache에 저장하여 분산 처리 지원
    3. 에러 발생 시 재시도 및 복구 메커니즘 필수
    4. 모든 노드에서 메트릭 수집 및 로깅
    """
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        self.state_store = self._initialize_state_store()
        self.metrics_collector = MetricsCollector()
        self.logger = self._setup_logging()
    
    def create_production_workflow(self) -> CompiledGraph:
        """
        Production용 워크플로우 생성
        
        구현 고려사항:
        1. 노드 간 비동기 통신
        2. 백프레셔 처리 (과부하 시 요청 제한)
        3. 서킷 브레이커 패턴 적용
        4. 헬스체크 및 모니터링 엔드포인트
        """
        workflow = StateGraph(ProductionWorkflowState)
        
        # 노드 정의 및 추가
        nodes = {
            "input_validation": self._create_input_validation_node(),
            "parsing": self._create_parsing_node(),
            "normalization": self._create_normalization_node(),
            "vector_search": self._create_vector_search_node(),
            "recommendation": self._create_recommendation_node(),
            "response_generation": self._create_response_generation_node(),
            "quality_check": self._create_quality_check_node(),
            "error_handler": self._create_error_handler_node()
        }
        
        for name, node_func in nodes.items():
            workflow.add_node(name, node_func)
        
        # 엣지 정의 (조건부 분기 포함)
        self._define_workflow_edges(workflow)
        
        # 미들웨어 추가
        workflow = self._add_middleware(workflow)
        
        return workflow.compile()
    
    def _create_parsing_node(self) -> Callable:
        """
        파싱 노드 생성
        
        구현 세부사항:
        1. 로컬 LLM 엔드포인트 연동
        2. 배치 처리 지원
        3. 타임아웃 및 재시도 로직
        4. 결과 캐싱
        """
        async def parsing_node(state: ProductionWorkflowState) -> ProductionWorkflowState:
            try:
                # 메트릭 수집 시작
                with self.metrics_collector.timer("parsing_node"):
                    # 로컬 LLM 클라이언트 초기화
                    llm_client = LocalLLMClient(
                        endpoint=self.config.vllm_endpoint,
                        model=self.config.primary_model
                    )
                    
                    # 파싱 실행
                    parser = ProductionInputParser(llm_client)
                    parsed_result = await parser.parse_with_retry(
                        user_input=state["user_input"],
                        context=state["session_context"],
                        max_retries=3
                    )
                    
                    # 상태 업데이트
                    state["parsed_data"] = parsed_result
                    state["current_step"] = "parsing_completed"
                    state["metrics"]["parsing_confidence"] = parsed_result.confidence
                    
                    # 품질 검증
                    if parsed_result.confidence < self.config.min_confidence_threshold:
                        state["quality_issues"].append("low_parsing_confidence")
                    
                    return state
                    
            except Exception as e:
                # 에러 처리
                state["errors"].append({
                    "step": "parsing",
                    "error": str(e),
                    "timestamp": datetime.utcnow()
                })
                state["current_step"] = "error_occurred"
                
                # 에러 메트릭 수집
                self.metrics_collector.increment("parsing_errors")
                self.logger.error(f"Parsing node error: {e}")
                
                return state
        
        return parsing_node
    
    def _define_workflow_edges(self, workflow: StateGraph):
        """
        워크플로우 엣지 정의
        
        분기 로직:
        1. 입력 검증 실패 → 에러 핸들러
        2. 파싱 성공 → 정규화
        3. 벡터 검색 활성화 여부에 따른 분기
        4. 품질 검증 실패 → 재처리 또는 에러 처리
        """
        # 순차적 엣지
        workflow.add_edge("input_validation", "parsing")
        workflow.add_edge("parsing", "normalization")
        
        # 조건부 엣지 - 벡터 검색 사용 여부
        workflow.add_conditional_edges(
            "normalization",
            self._should_use_vector_search,
            {
                "use_vector": "vector_search",
                "skip_vector": "recommendation"
            }
        )
        
        workflow.add_edge("vector_search", "recommendation")
        workflow.add_edge("recommendation", "response_generation")
        workflow.add_edge("response_generation", "quality_check")
        
        # 품질 검증 후 분기
        workflow.add_conditional_edges(
            "quality_check",
            self._quality_check_decision,
            {
                "approved": END,
                "needs_improvement": "parsing",  # 재처리
                "critical_error": "error_handler"
            }
        )
        
        # 에러 처리
        workflow.add_edge("error_handler", END)
    
    def _should_use_vector_search(self, state: ProductionWorkflowState) -> str:
        """벡터 검색 사용 여부 결정"""
        # 벡터 검색 활성화 조건
        conditions = [
            self.config.vector_search_enabled,
            state["parsed_data"].confidence > 0.7,
            len(state.get("session_context", {}).get("history", [])) > 0
        ]
        
        return "use_vector" if all(conditions) else "skip_vector"
    
    def _add_middleware(self, workflow: StateGraph) -> StateGraph:
        """
        미들웨어 추가
        
        포함 기능:
        1. 요청 로깅
        2. 메트릭 수집
        3. 인증 및 권한 검증
        4. 레이트 리미팅
        """
        # 로깅 미들웨어
        workflow = self._add_logging_middleware(workflow)
        
        # 메트릭 수집 미들웨어
        workflow = self._add_metrics_middleware(workflow)
        
        # 보안 미들웨어
        workflow = self._add_security_middleware(workflow)
        
        return workflow
```

#### 2. Azure 통합 구현 가이드

```python
class AzureProductionDeployment:
    """
    Azure 환경 배포 및 관리
    
    개발팀 구현 가이드:
    1. Infrastructure as Code (Terraform/ARM 템플릿)
    2. CI/CD 파이프라인 구성
    3. 모니터링 및 로깅 설정
    4. 보안 및 네트워킹 구성
    """
    
    def __init__(self, config: AzureDeploymentConfig):
        self.config = config
        self.resource_manager = AzureResourceManager(config)
        self.deployment_manager = DeploymentManager(config)
    
    async def deploy_production_stack(self) -> DeploymentResult:
        """
        전체 스택 배포
        
        배포 순서:
        1. Azure SQL Database
        2. Azure Container Registry
        3. AKS 클러스터
        4. vLLM 서비스
        5. API Gateway
        6. 모니터링 스택
        """
        deployment_steps = [
            ("database", self._deploy_azure_sql),
            ("container_registry", self._deploy_acr),
            ("kubernetes", self._deploy_aks),
            ("vllm_service", self._deploy_vllm),
            ("api_gateway", self._deploy_api_gateway),
            ("monitoring", self._deploy_monitoring)
        ]
        
        results = {}
        for step_name, deploy_func in deployment_steps:
            try:
                self.logger.info(f"Deploying {step_name}...")
                result = await deploy_func()
                results[step_name] = result
                self.logger.info(f"Successfully deployed {step_name}")
            except Exception as e:
                self.logger.error(f"Failed to deploy {step_name}: {e}")
                # 롤백 로직
                await self._rollback_deployment(step_name, results)
                raise
        
        return DeploymentResult(
            deployment_id=str(uuid.uuid4()),
            status="success",
            components=results,
            deployed_at=datetime.utcnow()
        )
    
    async def _deploy_azure_sql(self) -> Dict:
        """Azure SQL Database 배포"""
        sql_config = {
            "server_name": f"{self.config.project_name}-sql-server",
            "database_name": f"{self.config.project_name}-db",
            "tier": "Standard",
            "size": "S2",
            "backup_retention": 30,
            "geo_redundancy": True
        }
        
        # ARM 템플릿을 통한 배포
        template_path = "infrastructure/azure-sql-template.json"
        deployment_result = await self.resource_manager.deploy_template(
            template_path=template_path,
            parameters=sql_config
        )
        
        # 연결 문자열 생성 및 Key Vault 저장
        connection_string = self._build_connection_string(sql_config)
        await self._store_secret("sql-connection-string", connection_string)
        
        return {
            "server_fqdn": deployment_result["outputs"]["serverFqdn"],
            "database_name": sql_config["database_name"],
            "connection_secret_name": "sql-connection-string"
        }
    
    async def _deploy_vllm(self) -> Dict:
        """vLLM 서비스 배포"""
        vllm_config = {
            "model_name": self.config.llm_model,
            "gpu_type": "Standard_NC6s_v3",  # V100 GPU
            "replica_count": 2,
            "max_model_len": 4096,
            "tensor_parallel_size": 1
        }
        
        # Kubernetes 배포 매니페스트 생성
        k8s_manifest = self._generate_vllm_manifest(vllm_config)
        
        # AKS에 배포
        deployment_result = await self.deployment_manager.deploy_to_aks(
            namespace="vllm",
            manifest=k8s_manifest
        )
        
        return {
            "service_endpoint": deployment_result["service_url"],
            "replica_count": vllm_config["replica_count"],
            "model_name": vllm_config["model_name"]
        }
```

---

## 📚 문서 구조 및 참조 가이드

### 1. 문서 계층 구조

```
docs/
├── PRODUCTION_MIGRATION_GUIDE.md     # 이 문서 (전체 가이드)
├── AI_RESEARCHER_GUIDE.md            # AI 연구원 전용 가이드
├── DEVELOPER_GUIDE.md                # 개발팀 전용 가이드
├── PERFORMANCE_EVALUATION_GUIDE.md   # 성능 평가 가이드
└── DEPLOYMENT_GUIDE.md               # 배포 및 운영 가이드
```

### 2. 코드 주석 규약

```python
"""
코드 주석 작성 규약

=== AI 연구원용 주석 ===
- 목적: 각 함수/클래스의 역할과 실험 포인트 설명
- 형식: 상세한 설명 + 실험 가이드
- 예시:

def normalize_term(self, term: str, category: str) -> Tuple[str, float]:
    '''
    용어 정규화 함수
    
    AI 연구원 참고사항:
    - 이 함수는 현재 LLM 기반으로 동작
    - 벡터 임베딩 기반으로 교체 시 성능 향상 예상
    - 실험 포인트: 다양한 임베딩 모델 비교 (notebooks/02_normalizer_experiment.ipynb 참조)
    '''

=== 개발팀용 주석 ===
- 목적: 아키텍처 설계 의도와 Production 고려사항 설명
- 형식: 설계 원칙 + 구현 가이드
- 예시:

class DatabaseManager:
    '''
    데이터베이스 매니저
    
    개발팀 참고사항:
    - 현재: SQLite 사용 (프로토타입)
    - Production: Azure SQL Database 연동 필요
    - 구현 시 고려사항:
      1. 연결 풀링 및 트랜잭션 관리
      2. 쿼리 최적화 및 인덱싱
      3. 장애 복구 및 자동 재연결
    '''
"""
```

### 3. 실험 노트북 활용 가이드

```python
"""
실험 노트북 활용 가이드

=== 노트북별 역할 ===
1. 01_parser_experiment.ipynb: 파싱 로직 실험
2. 02_normalizer_experiment.ipynb: 정규화 로직 실험
3. 03_recommender_experiment.ipynb: 추천 엔진 실험
4. 04_database_experiment.ipynb: 데이터베이스 최적화 실험
5. 05_vector_embedding_experiment.ipynb: 벡터 임베딩 실험
6. 06_langgraph_experiment.ipynb: LangGraph 워크플로우 실험 (신규)
7. 07_performance_evaluation.ipynb: 성능 평가 실험 (신규)

=== 노트북 작성 원칙 ===
1. 자기완결성: 노트북 단독으로 실행 가능
2. 재현성: 동일한 환경에서 동일한 결과 보장
3. 문서화: 실험 목적, 방법, 결과 명확히 기록
4. 버전 관리: 실험 결과를 Git으로 추적
"""
```

---

이 가이드는 PMark3 프로토타입을 Production 환경으로 성공적으로 전환하기 위한 로드맵을 제공합니다. AI 연구원과 개발팀이 각자의 역할에 맞게 활용할 수 있도록 구성되었으며, 실제 구현 시에는 단계적 접근을 통해 점진적으로 개선해 나가시기 바랍니다. 