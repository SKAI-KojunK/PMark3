# PMark3 시스템 아키텍처

## 📋 개요

PMark3는 설비관리 시스템을 위한 자연어 기반 AI 작업요청 생성 어시스턴트입니다. 이 문서는 시스템의 전체 아키텍처, 모듈별 작동 흐름, 그리고 모듈 간 연계를 설명합니다.

## 🏗️ 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[test_chatbot.html<br/>포트 3010]
        NODE[Node.js Server<br/>포트 3010]
    end
    
    subgraph "Backend Layer"
        API[FastAPI<br/>포트 8010]
        CHAT[Chat API<br/>/api/v1/chat]
        WORK[Work Details API<br/>/api/v1/generate-work-details]
        AUTO[Autocomplete API<br/>/api/v1/autocomplete]
    end
    
    subgraph "Business Logic Layer"
        PARSER[Input Parser<br/>위치 우선 추출]
        NORM[LLM Normalizer<br/>동적 정규화]
        REC[Recommendation Engine<br/>개선된 유사도]
        SESSION[Session Manager<br/>세션 관리]
    end
    
    subgraph "Data Layer"
        DB[(SQLite DB<br/>notifications.db)]
        VECTOR[Vector DB<br/>vector_db]
        CACHE[Cache Layer<br/>용어 캐싱]
    end
    
    subgraph "External Services"
        OPENAI[OpenAI GPT-4o<br/>LLM 서비스]
    end
    
    UI -->|HTTP Request| NODE
    NODE -->|Proxy| API
    API --> CHAT
    API --> WORK
    API --> AUTO
    
    CHAT --> PARSER
    CHAT --> SESSION
    PARSER --> NORM
    NORM --> REC
    
    PARSER --> OPENAI
    NORM --> OPENAI
    REC --> OPENAI
    
    NORM --> DB
    REC --> DB
    REC --> VECTOR
    DB --> CACHE
    
    style UI fill:#e1f5fe
    style NODE fill:#e3f2fd
    style API fill:#f3e5f5
    style PARSER fill:#e8f5e8
    style NORM fill:#fff3e0
    style REC fill:#fce4ec
    style SESSION fill:#f1f8e9
    style DB fill:#f1f8e9
    style VECTOR fill:#e0f2f1
    style OPENAI fill:#e0f2f1
```

## 🔄 서비스 흐름 다이어그램

### 1. 사용자 입력 처리 흐름 (세션 관리 포함)

```mermaid
sequenceDiagram
    participant U as 사용자
    participant UI as Frontend (test_chatbot.html)
    participant NODE as Node.js Server
    participant API as Backend API
    participant S as Session Manager
    participant P as Input Parser
    participant N as LLM Normalizer
    participant R as Recommendation Engine
    participant D as Database
    participant V as Vector DB
    participant O as OpenAI

    U->>UI: 자연어 입력<br/>"No.1 PE 압력베젤 고장"
    UI->>NODE: POST /api/chat
    NODE->>API: POST /api/v1/chat
    API->>S: 세션 ID 생성/조회
    S-->>API: 세션 정보 반환
    API->>P: 입력 파싱 요청 (세션 컨텍스트 포함)
    P->>O: LLM 호출 (정보 추출)
    O-->>P: 구조화된 데이터 반환
    P->>N: 용어 정규화 요청
    N->>D: 표준 용어 로딩
    D-->>N: DB 용어 반환
    N->>O: LLM 호출 (정규화)
    O-->>N: 정규화된 용어 반환
    N-->>P: 정규화 완료
    P-->>API: 파싱 결과 반환
    API->>R: 추천 요청
    R->>D: 유사한 작업 검색
    R->>V: 벡터 유사도 검색
    D-->>R: 검색 결과 반환
    V-->>R: 벡터 검색 결과 반환
    R->>R: 유사도 계산 및 병합
    R-->>API: 추천 목록 반환
    API->>S: 세션 정보 업데이트
    API-->>NODE: 응답 (메시지 + 추천 + 세션)
    NODE-->>UI: 응답 전달
    UI-->>U: 결과 표시
```

### 2. 위치 기반 검색 흐름

```mermaid
flowchart TD
    A[사용자 입력] --> B{위치 정보 포함?}
    B -->|Yes| C[위치 우선 파싱]
    B -->|No| D[일반 파싱]
    C --> E[위치 기반 필터링]
    D --> F[전체 검색]
    E --> G[위치별 유사도 계산]
    F --> H[일반 유사도 계산]
    G --> I[결과 정렬 및 반환]
    H --> I
    I --> J[사용자에게 결과 전달]
```

## 🏛️ 모듈별 상세 아키텍처

### 1. 프론트엔드 모듈

#### 1.1 Node.js 서버 (`frontend/server.js`)
- **역할**: 프론트엔드 프록시 서버
- **포트**: 3010
- **기능**:
  - 정적 파일 서빙
  - 백엔드 API 프록시
  - CORS 처리
  - 세션 정보 관리

#### 1.2 챗봇 인터페이스 (`test_chatbot.html`)
- **역할**: 사용자 인터페이스
- **기능**:
  - 실시간 채팅 인터페이스
  - 세션 상태 표시
  - 추천 목록 표시
  - 자동완성 기능

### 2. 백엔드 모듈

#### 2.1 FastAPI 서버 (`backend/main.py`)
- **역할**: 메인 API 서버
- **포트**: 8010
- **기능**:
  - RESTful API 제공
  - 자동 문서 생성
  - 미들웨어 처리

#### 2.2 세션 관리자 (`backend/app/session_manager.py`)
- **역할**: 세션 상태 관리
- **기능**:
  - 세션 생성/조회
  - 대화 컨텍스트 유지
  - 세션별 설정 관리

#### 2.3 입력 파서 (`backend/app/agents/parser.py`)
- **역할**: 자연어 입력 분석
- **기능**:
  - 위치 정보 추출
  - 설비유형 식별
  - 현상코드 매핑
  - 우선순위 결정

#### 2.4 정규화 엔진 (`backend/app/logic/normalizer.py`)
- **역할**: 용어 표준화
- **기능**:
  - 동적 정규화
  - LLM 기반 변환
  - 캐시 관리

#### 2.5 추천 엔진 (`backend/app/logic/recommender.py`)
- **역할**: 유사 작업 추천
- **기능**:
  - 벡터 유사도 검색
  - 위치 기반 필터링
  - 점수 계산 및 정렬

### 3. 데이터 레이어

#### 3.1 SQLite 데이터베이스 (`data/notifications.db`)
- **역할**: 메인 데이터 저장소
- **테이블**:
  - `notifications`: 작업 이력
  - `equipment_types`: 설비유형
  - `status_codes`: 현상코드

#### 3.2 벡터 데이터베이스 (`data/vector_db`)
- **역할**: 임베딩 벡터 저장
- **기능**:
  - 문장 임베딩 저장
  - 유사도 검색
  - 실시간 업데이트

## 🔧 설정 및 환경

### 포트 구성
- **백엔드**: 8010 (FastAPI)
- **프론트엔드**: 3010 (Node.js)
- **API 문서**: http://localhost:8010/docs

### 환경 변수
```env
BACKEND_PORT=8010
FRONTEND_PORT=3010
DATABASE_URL=sqlite:///./data/notifications.db
VECTOR_DB_PATH=./data/vector_db
OPENAI_API_KEY=your_openai_api_key_here
```

### 데이터 파일
- `[Noti이력].xlsx`: 작업 이력 데이터
- `[현상코드].xlsx`: 현상코드 매핑
- `설비유형 자료_20250522.xlsx`: 설비유형 정보

## 🚀 성능 최적화

### 1. 캐싱 전략
- **용어 캐싱**: 정규화된 용어를 메모리에 캐시
- **세션 캐싱**: 활성 세션 정보를 메모리에 유지
- **벡터 캐싱**: 자주 사용되는 임베딩 벡터 캐시

### 2. 병렬 처리
- **비동기 API**: FastAPI의 비동기 처리 활용
- **벡터 검색**: 병렬 유사도 계산
- **LLM 호출**: 동시 요청 처리

### 3. 확장성 고려사항
- **마이크로서비스**: 모듈별 독립적 배포 가능
- **데이터베이스**: PostgreSQL 마이그레이션 준비
- **캐시**: Redis 도입 고려

## 🔍 모니터링 및 로깅

### 로그 레벨
- **DEBUG**: 개발 환경 상세 로그
- **INFO**: 일반 운영 로그
- **WARNING**: 경고 메시지
- **ERROR**: 오류 메시지

### 모니터링 지표
- API 응답 시간
- 세션 활성 수
- LLM 호출 빈도
- 데이터베이스 성능
- 벡터 검색 정확도 
