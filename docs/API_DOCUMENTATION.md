# PMark2 API 문서

## 📋 개요

PMark2 API는 설비관리 시스템을 위한 자연어 기반 AI 작업요청 생성 서비스입니다. 이 문서는 모든 API 엔드포인트와 사용법을 설명합니다.

## 🚀 기본 정보

- **Base URL**: `http://localhost:8001`
- **API 버전**: v1
- **인증**: 현재 없음 (개발 환경)
- **응답 형식**: JSON

## 📊 API 엔드포인트 목록

### 1. 헬스 체크
- **GET** `/health` - 서버 상태 확인

### 2. 채팅 API
- **POST** `/api/v1/chat` - 사용자 입력 분석 및 추천

### 3. 작업상세 생성 API
- **POST** `/api/v1/generate-work-details` - 작업상세 생성

## 🔍 상세 API 문서

### 1. 헬스 체크 API

#### GET /health

서버의 상태를 확인합니다.

**요청:**
```bash
curl http://localhost:8001/health
```

**응답:**
```json
{
  "status": "healthy"
}
```

**응답 코드:**
- `200 OK`: 서버 정상 작동
- `500 Internal Server Error`: 서버 오류

---

### 2. 채팅 API

#### POST /api/v1/chat

사용자의 자연어 입력을 분석하고 유사한 작업을 추천합니다.

**요청:**
```bash
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "No.1 PE 압력베젤 고장",
       "conversation_history": []
     }'
```

**요청 스키마:**
```json
{
  "message": "string",           // 사용자 입력 메시지
  "conversation_history": []     // 대화 이력 (선택사항)
}
```

**응답 스키마:**
```json
{
  "message": "string",           // AI 응답 메시지
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
  "needs_additional_input": false, // 추가 입력 필요 여부
  "missing_fields": []           // 누락된 필드 목록
}
```

**예시 요청:**

1. **위치 기반 검색:**
```bash
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "No.1 PE 압력베젤 고장"}'
```

2. **다른 위치 검색:**
```bash
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "석유제품배합/저장 탱크 누설"}'
```

3. **우선순위 포함 검색:**
```bash
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "RFCC 펌프 작동불량 일반작업"}'
```

4. **ITEMNO 조회:**
```bash
curl -X POST "http://localhost:8001/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "ITEMNO PE-SE1304B"}'
```

**예시 응답:**

```json
{
  "message": "입력하신 내용을 분석했습니다:\n\n• 위치/공정: No.1 PE\n• 설비유형: [VEDR]Pressure Vessel/ Drum\n• 현상코드: 고장.결함.수명소진\n• 우선순위: 긴급작업(최우선순위)\n\n분석 신뢰도: 95.0%\n\n유사한 작업 3건을 찾았습니다:\n1. [VEDR]Pressure Vessel/ Drum (No.1 PE) - 유사도 100.0%\n2. [VEDR]Pressure Vessel/ Drum (No.1 PE) - 유사도 100.0%\n3. [VEDR]Pressure Vessel/ Drum (No.1 PE) - 유사도 100.0%\n\n원하는 작업을 선택하시면 상세 정보를 제공해드립니다.",
  "recommendations": [
    {
      "itemno": "PE-SE1304B",
      "process": "SKGC-설비관리",
      "location": "No.1 PE",
      "equipType": "[VEDR]Pressure Vessel/ Drum",
      "statusCode": "고장.결함.수명소진",
      "priority": "긴급작업(최우선순위)",
      "score": 1.0,
      "work_title": "[긴급]_PE-SE1304\"B\" BTM Plate Clamp 점검작업",
      "work_details": "[긴급]_PE-SE1304\"B\" BTM Plate Clamp 점검작업"
    }
  ],
  "parsed_input": {
    "scenario": "S1",
    "location": "No.1 PE",
    "equipment_type": "[VEDR]Pressure Vessel/ Drum",
    "status_code": "고장.결함.수명소진",
    "priority": "긴급작업(최우선순위)",
    "itemno": null,
    "confidence": 0.95
  },
  "needs_additional_input": false,
  "missing_fields": []
}
```

**응답 코드:**
- `200 OK`: 성공
- `400 Bad Request`: 잘못된 요청
- `422 Unprocessable Entity`: 유효성 검사 실패
- `500 Internal Server Error`: 서버 오류

---

### 3. 작업상세 생성 API

#### POST /api/v1/generate-work-details

선택된 추천 항목에 대한 작업상세를 생성합니다.

**요청:**
```bash
curl -X POST "http://localhost:8001/api/v1/generate-work-details" \
     -H "Content-Type: application/json" \
     -d '{
       "selected_recommendation": {
         "itemno": "PE-SE1304B",
         "location": "No.1 PE",
         "equipType": "[VEDR]Pressure Vessel/ Drum",
         "statusCode": "고장.결함.수명소진",
         "priority": "긴급작업(최우선순위)"
       },
       "user_message": "No.1 PE 압력베젤 고장"
     }'
```

**요청 스키마:**
```json
{
  "selected_recommendation": {   // 선택된 추천 항목
    "itemno": "string",
    "location": "string",
    "equipType": "string",
    "statusCode": "string",
    "priority": "string"
  },
  "user_message": "string"       // 사용자 원본 메시지
}
```

**응답 스키마:**
```json
{
  "work_title": "string",        // 생성된 작업명
  "work_details": "string",      // 생성된 작업상세
  "confidence": 0.95            // 생성 신뢰도
}
```

**예시 응답:**
```json
{
  "work_title": "[긴급] No.1 PE 압력베젤 고장 수리작업",
  "work_details": "No.1 PE 공정의 압력베젤에서 고장이 발생하여 긴급 수리가 필요합니다. 안전을 위해 즉시 작업을 진행해야 합니다.",
  "confidence": 0.92
}
```

**응답 코드:**
- `200 OK`: 성공
- `400 Bad Request`: 잘못된 요청
- `422 Unprocessable Entity`: 유효성 검사 실패
- `500 Internal Server Error`: 서버 오류

---

## 🔧 API 사용 가이드

### 1. 위치 기반 검색 활용

PMark2는 위치 정보를 우선적으로 활용하여 정확한 추천을 제공합니다.

**권장 입력 형식:**
```
"[위치] [설비유형] [현상코드] [우선순위]"
```

**예시:**
- "No.1 PE 압력베젤 고장"
- "석유제품배합/저장 탱크 누설"
- "RFCC 펌프 작동불량 일반작업"

### 2. 유사도 점수 해석

- **1.0 (100%)**: 완벽한 매칭
- **0.8-0.99 (80-99%)**: 매우 높은 유사도 (녹색)
- **0.6-0.79 (60-79%)**: 높은 유사도 (주황)
- **0.2-0.59 (20-59%)**: 낮은 유사도 (빨강)
- **<0.2**: 추천 제외

### 3. 시나리오별 처리

#### S1: 자연어 요청
- 위치, 설비유형, 현상코드, 우선순위 추출
- LLM 기반 정규화
- 유사한 작업 검색 및 추천

#### S2: ITEMNO 조회
- ITEMNO 파싱
- 해당 작업의 상세 정보 제공

### 4. 에러 처리

**일반적인 에러 응답:**
```json
{
  "detail": "에러 메시지"
}
```

**에러 코드:**
- `400`: 잘못된 요청 형식
- `422`: 입력 데이터 유효성 검사 실패
- `500`: 서버 내부 오류

---

## 🧪 API 테스트

### 1. Swagger UI

브라우저에서 http://localhost:8001/docs 접속하여 대화형 API 문서를 확인할 수 있습니다.

### 2. curl 테스트 스크립트

```bash
#!/bin/bash

# API 테스트 스크립트
BASE_URL="http://localhost:8001"

echo "🔍 PMark2 API 테스트 시작..."

# 1. 헬스 체크
echo "1. 헬스 체크 테스트"
curl -s "$BASE_URL/health" | jq .

# 2. 위치 기반 검색 테스트
echo -e "\n2. 위치 기반 검색 테스트"
curl -s -X POST "$BASE_URL/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "No.1 PE 압력베젤 고장"}' | jq .

# 3. 다른 위치 검색 테스트
echo -e "\n3. 다른 위치 검색 테스트"
curl -s -X POST "$BASE_URL/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "석유제품배합/저장 탱크 누설"}' | jq .

# 4. ITEMNO 조회 테스트
echo -e "\n4. ITEMNO 조회 테스트"
curl -s -X POST "$BASE_URL/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "ITEMNO PE-SE1304B"}' | jq .

echo -e "\n✅ API 테스트 완료"
```

### 3. Python 테스트 스크립트

```python
import requests
import json

BASE_URL = "http://localhost:8001"

def test_health():
    """헬스 체크 테스트"""
    response = requests.get(f"{BASE_URL}/health")
    print("헬스 체크:", response.json())
    return response.status_code == 200

def test_chat(message):
    """채팅 API 테스트"""
    data = {"message": message}
    response = requests.post(f"{BASE_URL}/api/v1/chat", json=data)
    print(f"채팅 테스트 ({message}):", response.json())
    return response.status_code == 200

def test_work_details():
    """작업상세 생성 테스트"""
    data = {
        "selected_recommendation": {
            "itemno": "PE-SE1304B",
            "location": "No.1 PE",
            "equipType": "[VEDR]Pressure Vessel/ Drum",
            "statusCode": "고장.결함.수명소진",
            "priority": "긴급작업(최우선순위)"
        },
        "user_message": "No.1 PE 압력베젤 고장"
    }
    response = requests.post(f"{BASE_URL}/api/v1/generate-work-details", json=data)
    print("작업상세 생성:", response.json())
    return response.status_code == 200

if __name__ == "__main__":
    print("🔍 PMark2 API 테스트 시작...")
    
    # 테스트 실행
    test_health()
    test_chat("No.1 PE 압력베젤 고장")
    test_chat("석유제품배합/저장 탱크 누설")
    test_chat("ITEMNO PE-SE1304B")
    test_work_details()
    
    print("✅ API 테스트 완료")
```

---

## 📊 성능 지표

### 1. 응답 시간

- **평균 응답 시간**: 2-5초
- **헬스 체크**: <100ms
- **채팅 API**: 2-8초 (LLM 호출 포함)
- **작업상세 생성**: 3-10초 (LLM 호출 포함)

### 2. 처리량

- **동시 요청**: 최대 10개
- **분당 요청**: 최대 60개
- **일일 요청**: 최대 10,000개

### 3. 정확도

- **위치 인식 정확도**: 95%+
- **설비유형 정규화 정확도**: 90%+
- **현상코드 정규화 정확도**: 85%+
- **우선순위 인식 정확도**: 90%+

---

## 🔒 보안 고려사항

### 1. 현재 상태 (개발 환경)

- 인증/인가 없음
- CORS 허용
- 모든 IP에서 접근 가능

### 2. 프로덕션 권장사항

- API 키 인증 추가
- Rate Limiting 구현
- CORS 정책 강화
- HTTPS 적용
- 로그 보안 강화

---

## 📞 지원 및 문의

### 1. API 문서

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### 2. 문제 해결

- **로그 확인**: `tail -f backend/logs/app.log`
- **상태 확인**: `curl http://localhost:8001/health`
- **이슈 리포트**: GitHub Issues

### 3. 연락처

- **기술 지원**: [이메일]
- **문서**: docs/ 디렉토리

---

**PMark2 API 문서** - 설비관리 시스템의 AI 기반 작업요청 생성 API를 활용하세요. 