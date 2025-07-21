# PMark3 API 문서

## 📋 개요

PMark3 API는 설비관리 시스템을 위한 자연어 기반 AI 작업요청 생성 서비스입니다. 이 문서는 모든 API 엔드포인트와 사용법을 설명합니다.

## 🚀 기본 정보

- **Base URL**: `http://localhost:8010`
- **API 버전**: v1
- **인증**: 현재 없음 (개발 환경)
- **응답 형식**: JSON

## 📊 API 엔드포인트 목록

### 1. 헬스 체크
- **GET** `/health` - 서버 상태 확인

### 2. 채팅 API
- **POST** `/api/v1/chat` - 사용자 입력 분석 및 추천 (세션 관리 포함)

### 3. 작업상세 생성 API
- **POST** `/api/v1/generate-work-details` - 작업상세 생성

### 4. 자동완성 API
- **POST** `/api/v1/autocomplete` - 자동완성 기능

### 5. 세션 관리 API
- **GET** `/api/v1/session/{session_id}` - 세션 정보 조회
- **DELETE** `/api/v1/session/{session_id}` - 세션 삭제

## 🔍 상세 API 문서

### 1. 헬스 체크 API

#### GET /health

서버의 상태를 확인합니다.

**요청:**
```bash
curl http://localhost:8010/health
```

**응답:**
```json
{
  "status": "healthy",
  "message": "PMark3 AI Assistant API",
  "version": "3.0.0"
}
```

**응답 코드:**
- `200 OK`: 서버 정상 작동
- `500 Internal Server Error`: 서버 오류

---

### 2. 채팅 API

#### POST /api/v1/chat

사용자의 자연어 입력을 분석하고 유사한 작업을 추천합니다. 세션 관리를 통해 멀티턴 대화를 지원합니다.

**요청:**
```bash
curl -X POST "http://localhost:8010/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "No.1 PE 압력베젤 고장",
       "session_id": "optional_session_id",
       "conversation_history": []
     }'
```

**요청 스키마:**
```json
{
  "message": "string",           // 사용자 입력 메시지
  "session_id": "string",        // 세션 ID (선택사항)
  "conversation_history": []     // 대화 이력 (선택사항)
}
```

**응답 스키마:**
```json
{
  "message": "string",           // AI 응답 메시지
  "session_id": "string",        // 세션 ID
  "recommendations": [           // 추천 목록
    {
      "itemno": "string",        // ITEMNO
      "process": "string",       // 공정명
      "location": "string",      // 위치
      "equipType": "string",     // 설비유형
      "statusCode": "string",    // 현상코드
      "priority": "string",      // 우선순위
      "score": 0.95,            // 유사도 점수 (0.0-1.0)
      "work_title": "string",    // 작업명
      "work_details": "string"   // 작업상세
    }
  ],
  "parsed_input": {              // 파싱된 입력 정보
    "scenario": "string",        // 시나리오 (S1/S2)
    "location": "string",        // 추출된 위치
    "equipment_type": "string",  // 추출된 설비유형
    "status_code": "string",     // 추출된 현상코드
    "priority": "string",        // 추출된 우선순위
    "itemno": "string",          // 추출된 ITEMNO (S2)
    "confidence": 0.95          // 파싱 신뢰도
  },
  "session_info": {              // 세션 정보
    "session_id": "string",      // 세션 ID
    "created_at": "string",      // 생성 시간
    "message_count": 5,          // 메시지 수
    "context_summary": "string"  // 컨텍스트 요약
  }
}
```

**응답 코드:**
- `200 OK`: 성공
- `400 Bad Request`: 잘못된 요청
- `500 Internal Server Error`: 서버 오류

---

### 3. 작업상세 생성 API

#### POST /api/v1/generate-work-details

ITEMNO를 기반으로 작업상세를 생성합니다.

**요청:**
```bash
curl -X POST "http://localhost:8010/api/v1/generate-work-details" \
     -H "Content-Type: application/json" \
     -d '{
       "itemno": "ITEM001",
       "session_id": "optional_session_id"
     }'
```

**요청 스키마:**
```json
{
  "itemno": "string",           // ITEMNO
  "session_id": "string"        // 세션 ID (선택사항)
}
```

**응답 스키마:**
```json
{
  "itemno": "string",           // ITEMNO
  "work_title": "string",       // 작업명
  "work_details": "string",     // 상세 작업 내용
  "location": "string",         // 위치
  "equipment_type": "string",   // 설비유형
  "status_code": "string",      // 현상코드
  "priority": "string",         // 우선순위
  "estimated_time": "string",   // 예상 소요시간
  "required_tools": "string",   // 필요 도구
  "safety_notes": "string"      // 안전 주의사항
}
```

---

### 4. 자동완성 API

#### POST /api/v1/autocomplete

사용자 입력에 대한 자동완성 제안을 제공합니다.

**요청:**
```bash
curl -X POST "http://localhost:8010/api/v1/autocomplete" \
     -H "Content-Type: application/json" \
     -d '{
       "partial_input": "No.1 PE",
       "category": "location"
     }'
```

**요청 스키마:**
```json
{
  "partial_input": "string",    // 부분 입력
  "category": "string"          // 카테고리 (location, equipment, status, priority)
}
```

**응답 스키마:**
```json
{
  "suggestions": [              // 제안 목록
    {
      "text": "string",         // 제안 텍스트
      "score": 0.95,           // 관련성 점수
      "category": "string"      // 카테고리
    }
  ],
  "total_count": 10            // 총 제안 수
}
```

---

### 5. 세션 관리 API

#### GET /api/v1/session/{session_id}

특정 세션의 정보를 조회합니다.

**요청:**
```bash
curl "http://localhost:8010/api/v1/session/session_123"
```

**응답 스키마:**
```json
{
  "session_id": "string",       // 세션 ID
  "created_at": "string",       // 생성 시간
  "last_activity": "string",    // 마지막 활동 시간
  "message_count": 5,           // 메시지 수
  "context_summary": "string",  // 컨텍스트 요약
  "is_active": true             // 활성 상태
}
```

#### DELETE /api/v1/session/{session_id}

특정 세션을 삭제합니다.

**요청:**
```bash
curl -X DELETE "http://localhost:8010/api/v1/session/session_123"
```

**응답:**
```json
{
  "message": "Session deleted successfully",
  "session_id": "session_123"
}
```

## 🔧 에러 처리

### 에러 응답 형식

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "에러 메시지",
    "details": "상세 정보"
  }
}
```

### 주요 에러 코드

- `INVALID_INPUT`: 잘못된 입력 형식
- `SESSION_NOT_FOUND`: 세션을 찾을 수 없음
- `LLM_ERROR`: LLM 서비스 오류
- `DATABASE_ERROR`: 데이터베이스 오류
- `VECTOR_SEARCH_ERROR`: 벡터 검색 오류

## 📊 성능 지표

### 응답 시간
- **채팅 API**: 평균 2-3초
- **자동완성 API**: 평균 0.5초
- **세션 조회**: 평균 0.1초

### 처리량
- **동시 사용자**: 최대 100명
- **초당 요청**: 최대 50회
- **세션 수**: 최대 1000개

## 🔒 보안 고려사항

### 현재 상태 (개발 환경)
- 인증 없음
- 모든 origin 허용 (CORS)
- 디버그 모드 활성화

### 프로덕션 권장사항
- JWT 토큰 인증 추가
- CORS 정책 제한
- Rate limiting 구현
- HTTPS 강제
- 로그 보안 강화

## 📝 사용 예제

### 1. 기본 채팅

```javascript
// 프론트엔드에서 채팅 API 호출
const response = await fetch('http://localhost:8010/api/v1/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'No.1 PE 압력베젤 고장',
    session_id: 'user_session_123'
  })
});

const data = await response.json();
console.log(data.recommendations);
```

### 2. 세션 관리

```javascript
// 세션 정보 조회
const sessionResponse = await fetch('http://localhost:8010/api/v1/session/user_session_123');
const sessionData = await sessionResponse.json();

// 세션 삭제
await fetch('http://localhost:8010/api/v1/session/user_session_123', {
  method: 'DELETE'
});
```

### 3. 자동완성

```javascript
// 자동완성 요청
const autocompleteResponse = await fetch('http://localhost:8010/api/v1/autocomplete', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    partial_input: 'No.1 PE',
    category: 'location'
  })
});

const suggestions = await autocompleteResponse.json();
```

## 🚀 API 문서 접근

- **Swagger UI**: http://localhost:8010/docs
- **ReDoc**: http://localhost:8010/redoc
- **OpenAPI JSON**: http://localhost:8010/openapi.json 