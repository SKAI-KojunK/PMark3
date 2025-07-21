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
        SESSION_API[Session API<br/>/api/v1/session]
    end
    
    subgraph "Business Logic Layer"
        PARSER[Input Parser<br/>위치 우선 추출]
        NORM[LLM Normalizer<br/>동적 정규화]
        REC[Recommendation Engine<br/>개선된 유사도]
        SESSION[Session Manager<br/>세션 관리]
        RESPONSE[Response Generator<br/>응답 생성]
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
    API --> SESSION_API
    
    CHAT --> PARSER
    CHAT --> SESSION
    CHAT --> RESPONSE
    PARSER --> NORM
    NORM --> REC
    
    PARSER --> OPENAI
    NORM --> OPENAI
    REC --> OPENAI
    RESPONSE --> OPENAI
    
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
    style RESPONSE fill:#e0f2f1
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

## 🧠 상세 모듈 아키텍처

### 1. 파싱 로직 아키텍처

```mermaid
graph TD
    subgraph "Input Parser Architecture"
        A[사용자 입력] --> B{시나리오 판단}
        B -->|S1: 자연어| C[자연어 파싱]
        B -->|S2: ITEMNO| D[ITEMNO 파싱]
        B -->|S3: 세션 컨텍스트| E[컨텍스트 기반 파싱]
        
        C --> F[LLM 정보 추출]
        F --> G[위치 우선 추출]
        G --> H[설비유형 추출]
        H --> I[현상코드 추출]
        I --> J[우선순위 추출]
        
        D --> K[ITEMNO 검증]
        K --> L[작업 조회]
        
        E --> M[세션 히스토리 분석]
        M --> N[컨텍스트 통합]
        N --> F
        
        J --> O[용어 정규화]
        L --> P[작업 상세 반환]
        O --> Q[파싱 결과]
        
        style G fill:#e8f5e8
        style F fill:#e0f2f1
        style O fill:#fff3e0
    end
```

#### 1.1 파싱 로직 상세 흐름

```mermaid
sequenceDiagram
    participant P as Parser
    participant LLM as OpenAI
    participant N as Normalizer
    participant DB as Database
    participant S as Session Manager

    P->>P: 입력 분석 시작
    P->>S: 세션 컨텍스트 요청
    S-->>P: 세션 정보 반환
    
    P->>LLM: 위치 정보 추출 요청
    LLM-->>P: 위치 정보 반환
    
    P->>LLM: 설비유형 추출 요청
    LLM-->>P: 설비유형 반환
    
    P->>LLM: 현상코드 추출 요청
    LLM-->>P: 현상코드 반환
    
    P->>LLM: 우선순위 추출 요청
    LLM-->>P: 우선순위 반환
    
    P->>N: 용어 정규화 요청
    N->>DB: 표준 용어 조회
    DB-->>N: 용어 목록 반환
    N->>LLM: 정규화 요청
    LLM-->>N: 정규화된 용어 반환
    N-->>P: 정규화 완료
    
    P->>P: 신뢰도 계산
    P->>P: 파싱 결과 반환
```

### 2. 정규화 엔진 아키텍처

```mermaid
graph TD
    subgraph "LLM Normalizer Architecture"
        A[입력 용어] --> B{카테고리 확인}
        B -->|location| C[위치 정규화]
        B -->|equipment| D[설비유형 정규화]
        B -->|status| E[현상코드 정규화]
        B -->|priority| F[우선순위 정규화]
        
        C --> G[DB 용어 로딩]
        D --> G
        E --> G
        F --> G
        
        G --> H[LLM 프롬프트 생성]
        H --> I[OpenAI 호출]
        I --> J[응답 파싱]
        J --> K[신뢰도 검증]
        K --> L{신뢰도 임계값}
        L -->|통과| M[정규화 결과 반환]
        L -->|실패| N[원본 용어 반환]
        
        style G fill:#e8f5e8
        style I fill:#e0f2f1
        style M fill:#fff3e0
    end
```

#### 2.1 정규화 프로세스 상세

```mermaid
flowchart LR
    A[입력 용어] --> B[DB 표준 용어 로딩]
    B --> C[LLM 프롬프트 생성]
    C --> D[OpenAI API 호출]
    D --> E[응답 파싱]
    E --> F[신뢰도 계산]
    F --> G{신뢰도 > 0.7?}
    G -->|Yes| H[정규화된 용어 반환]
    G -->|No| I[원본 용어 반환]
    
    style B fill:#e8f5e8
    style D fill:#e0f2f1
    style H fill:#fff3e0
```

### 3. 유사도 계산 및 추천 로직 아키텍처

```mermaid
graph TD
    subgraph "Recommendation Engine Architecture"
        A[파싱된 입력] --> B[위치 기반 필터링]
        B --> C[벡터 유사도 검색]
        B --> D[DB 유사도 검색]
        
        C --> E[벡터 결과]
        D --> F[DB 결과]
        
        E --> G[결과 병합]
        F --> G
        
        G --> H[유사도 계산]
        H --> I[설비유형 유사도<br/>35%]
        H --> J[위치 유사도<br/>35%]
        H --> K[현상코드 유사도<br/>20%]
        H --> L[우선순위 유사도<br/>10%]
        
        I --> M[가중 평균 계산]
        J --> M
        K --> M
        L --> M
        
        M --> N{보너스 점수<br/>체크}
        N -->|모든 필드 높음| O[+0.1 보너스]
        N -->|기본 점수| P[기본 점수]
        
        O --> Q[임계값 필터링<br/>>0.2]
        P --> Q
        Q --> R[정렬 및 반환]
        
        style B fill:#e8f5e8
        style C fill:#e0f2f1
        style M fill:#fff3e0
    end
```

#### 3.1 유사도 계산 상세 프로세스

```mermaid
flowchart TD
    A[입력 데이터] --> B[Levenshtein 거리 계산]
    B --> C[가중치 적용]
    C --> D[위치 35%]
    C --> E[설비유형 35%]
    C --> F[현상코드 20%]
    C --> G[우선순위 10%]
    
    D --> H[가중 평균]
    E --> H
    F --> H
    G --> H
    
    H --> I{모든 필드 높은 매칭?}
    I -->|Yes| J[+0.1 보너스]
    I -->|No| K[기본 점수]
    
    J --> L[최종 유사도]
    K --> L
    
    L --> M{임계값 체크<br/>>0.2}
    M -->|통과| N[추천 목록에 추가]
    M -->|실패| O[제외]
    
    style D fill:#e8f5e8
    style H fill:#fff3e0
    style L fill:#fce4ec
```

### 4. 응답 생성 아키텍처

```mermaid
graph TD
    subgraph "Response Generator Architecture"
        A[파싱 결과] --> B[응답 템플릿 선택]
        B --> C{응답 유형}
        C -->|추천 결과| D[추천 응답 생성]
        C -->|오류 상황| E[오류 응답 생성]
        C -->|도움말 요청| F[도움말 응답 생성]
        
        D --> G[추천 목록 포맷팅]
        G --> H[유사도 점수 표시]
        H --> I[작업 상세 링크]
        
        E --> J[오류 메시지 생성]
        J --> K[해결 방법 제안]
        
        F --> L[도움말 내용 생성]
        L --> M[사용 예시 제공]
        
        I --> N[최종 응답]
        K --> N
        M --> N
        
        style G fill:#e8f5e8
        style H fill:#fff3e0
        style N fill:#fce4ec
    end
```

#### 4.1 응답 생성 프로세스

```mermaid
sequenceDiagram
    participant RG as Response Generator
    participant LLM as OpenAI
    participant DB as Database
    participant S as Session Manager

    RG->>RG: 응답 생성 시작
    RG->>S: 세션 컨텍스트 요청
    S-->>RG: 세션 정보 반환
    
    RG->>LLM: 응답 템플릿 생성 요청
    LLM-->>RG: 템플릿 반환
    
    RG->>DB: 추천 데이터 조회
    DB-->>RG: 추천 목록 반환
    
    RG->>RG: 응답 포맷팅
    RG->>RG: 유사도 점수 계산
    RG->>RG: 최종 응답 생성
    
    RG->>S: 세션 업데이트
    S-->>RG: 업데이트 완료
    
    RG->>RG: 응답 반환
```

### 5. 세션 관리 아키텍처

```mermaid
graph TD
    subgraph "Session Manager Architecture"
        A[세션 요청] --> B{세션 존재?}
        B -->|Yes| C[기존 세션 조회]
        B -->|No| D[새 세션 생성]
        
        C --> E[세션 정보 로드]
        D --> F[세션 ID 생성]
        F --> G[초기 컨텍스트 설정]
        
        E --> H[컨텍스트 분석]
        G --> H
        
        H --> I[대화 히스토리 관리]
        I --> J[컨텍스트 요약 생성]
        J --> K[세션 정보 반환]
        
        L[메시지 수신] --> M[세션 업데이트]
        M --> N[대화 히스토리 추가]
        N --> O[컨텍스트 요약 업데이트]
        O --> P[세션 저장]
        
        Q[세션 정리] --> R[오래된 세션 삭제]
        R --> S[메모리 정리]
        
        style C fill:#e8f5e8
        style H fill:#e0f2f1
        style K fill:#fff3e0
    end
```

#### 5.1 세션 관리 프로세스

```mermaid
sequenceDiagram
    participant SM as Session Manager
    participant DB as Database
    participant LLM as OpenAI
    participant C as Cache

    SM->>SM: 세션 요청 수신
    SM->>DB: 세션 조회
    alt 세션 존재
        DB-->>SM: 세션 정보 반환
        SM->>C: 캐시 확인
        C-->>SM: 캐시된 컨텍스트
    else 새 세션
        SM->>SM: 세션 ID 생성
        SM->>DB: 새 세션 저장
        SM->>C: 초기 컨텍스트 캐시
    end
    
    SM->>LLM: 컨텍스트 요약 생성
    LLM-->>SM: 요약 반환
    
    SM->>DB: 세션 업데이트
    SM->>C: 컨텍스트 캐시 업데이트
    
    SM-->>SM: 세션 정보 반환
```

### 6. 자동완성 아키텍처

```mermaid
graph TD
    subgraph "Autocomplete Architecture"
        A[부분 입력] --> B[카테고리 분류]
        B --> C{카테고리 타입}
        C -->|location| D[위치 자동완성]
        C -->|equipment| E[설비유형 자동완성]
        C -->|status| F[현상코드 자동완성]
        C -->|priority| G[우선순위 자동완성]
        
        D --> H[벡터 검색]
        E --> H
        F --> H
        G --> H
        
        H --> I[유사도 계산]
        I --> J[결과 정렬]
        J --> K[상위 N개 선택]
        K --> L[자동완성 제안]
        
        style H fill:#e8f5e8
        style I fill:#e0f2f1
        style L fill:#fff3e0
    end
```

### 7. 벡터 검색 아키텍처

```mermaid
graph TD
    subgraph "Vector Search Architecture"
        A[검색 쿼리] --> B[임베딩 생성]
        B --> C[벡터 DB 검색]
        C --> D[코사인 유사도 계산]
        D --> E[결과 정렬]
        E --> F[상위 K개 선택]
        F --> G[결과 반환]
        
        H[문서 추가] --> I[문서 임베딩 생성]
        I --> J[벡터 DB 저장]
        J --> K[인덱스 업데이트]
        
        style B fill:#e8f5e8
        style C fill:#e0f2f1
        style G fill:#fff3e0
    end
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

#### 2.6 응답 생성기 (`backend/app/logic/response_generator.py`)
- **역할**: 응답 메시지 생성
- **기능**:
  - 템플릿 기반 응답 생성
  - 컨텍스트 기반 응답
  - 다국어 지원

### 3. 데이터 레이어

#### 3.1 SQLite 데이터베이스 (`data/notifications.db`)
- **역할**: 메인 데이터 저장소
- **테이블**:
  - `notifications`: 작업 이력
  - `equipment_types`: 설비유형
  - `status_codes`: 현상코드
  - `sessions`: 세션 정보

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

## 📊 데이터 흐름 분석

### 1. 입력 처리 데이터 흐름

```mermaid
flowchart LR
    A[사용자 입력] --> B[파싱 엔진]
    B --> C[정규화 엔진]
    C --> D[추천 엔진]
    D --> E[응답 생성기]
    E --> F[사용자 응답]
    
    B --> G[세션 관리자]
    G --> H[세션 저장소]
    
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#fce4ec
```

### 2. 벡터 검색 데이터 흐름

```mermaid
flowchart TD
    A[검색 쿼리] --> B[임베딩 생성]
    B --> C[벡터 DB 검색]
    C --> D[유사도 계산]
    D --> E[결과 정렬]
    E --> F[추천 목록]
    
    G[새 문서] --> H[문서 임베딩]
    H --> I[벡터 DB 저장]
    
    style B fill:#e8f5e8
    style C fill:#e0f2f1
    style F fill:#fff3e0
```

## 🔧 기술 스택 상세

### 백엔드 기술 스택
```mermaid
graph TB
    subgraph "Backend Stack"
        FASTAPI[FastAPI]
        PYTHON[Python 3.9+]
        UVICORN[Uvicorn]
        SQLITE[SQLite]
        OPENAI[OpenAI API]
        SENTENCE_TRANSFORMERS[Sentence Transformers]
        NUMPY[NumPy]
        PANDAS[Pandas]
    end
    
    FASTAPI --> PYTHON
    PYTHON --> UVICORN
    PYTHON --> SQLITE
    PYTHON --> OPENAI
    PYTHON --> SENTENCE_TRANSFORMERS
    PYTHON --> NUMPY
    PYTHON --> PANDAS
    
    style FASTAPI fill:#f3e5f5
    style OPENAI fill:#e0f2f1
    style SENTENCE_TRANSFORMERS fill:#e8f5e8
```

### 프론트엔드 기술 스택
```mermaid
graph TB
    subgraph "Frontend Stack"
        NODEJS[Node.js]
        EXPRESS[Express.js]
        HTML5[HTML5]
        CSS3[CSS3]
        JAVASCRIPT[JavaScript ES6+]
        WEBSOCKET[WebSocket]
    end
    
    NODEJS --> EXPRESS
    EXPRESS --> HTML5
    EXPRESS --> CSS3
    EXPRESS --> JAVASCRIPT
    EXPRESS --> WEBSOCKET
    
    style NODEJS fill:#e3f2fd
    style EXPRESS fill:#e1f5fe
    style JAVASCRIPT fill:#fff3e0
```

## 🎯 핵심 성능 지표

### 1. 응답 시간 목표
- **파싱**: < 2초
- **정규화**: < 1초
- **추천 생성**: < 3초
- **전체 응답**: < 5초

### 2. 정확도 목표
- **위치 인식**: > 95%
- **설비유형 정규화**: > 90%
- **현상코드 정규화**: > 85%
- **추천 정확도**: > 80%

### 3. 처리량 목표
- **동시 사용자**: 100명
- **초당 요청**: 50회
- **세션 수**: 1000개

## 🔒 보안 아키텍처

### 1. 현재 보안 상태
```mermaid
graph TD
    A[사용자 요청] --> B[인증 없음]
    B --> C[CORS 허용]
    C --> D[API 접근]
    D --> E[데이터 처리]
    
    style B fill:#ffebee
    style C fill:#ffebee
```

### 2. 향후 보안 강화 계획
```mermaid
graph TD
    A[사용자 요청] --> B[JWT 토큰 인증]
    B --> C[Rate Limiting]
    C --> D[CORS 제한]
    D --> E[API 접근]
    E --> F[데이터 암호화]
    
    style B fill:#e8f5e8
    style C fill:#e8f5e8
    style F fill:#e8f5e8
```

---

**PMark3 시스템 아키텍처** - 세션 관리와 벡터 검색을 포함한 고급 AI 작업요청 생성 시스템의 완전한 아키텍처를 이해하세요! 🚀 
