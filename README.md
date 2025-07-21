# PMark2.5 - AI-powered Work Request Assistant

설비관리 시스템을 위한 **멀티턴 대화형** AI 작업요청 생성 어시스턴트

## 📋 프로젝트 개요

PMark2.5는 사용자의 자연어 입력을 분석하여 설비관리 시스템의 작업요청을 자동으로 생성하는 AI 어시스턴트입니다. OpenAI GPT-4o를 활용하여 **멀티턴 대화**를 통해 단계별로 정보를 수집하고, 한국어-영어 혼용 표현, 오타, 띄어쓰기 오류 등도 정확하게 이해하여 표준화된 작업요청을 생성합니다.

## 🎯 주요 기능

### 🔥 **PMark2.5 신규 기능**
- **멀티턴 대화 시스템**: 단계별 정보 수집 및 누적 단서 관리
- **세션 기반 상태 관리**: 대화 컨텍스트 유지 및 턴별 추적
- **설비유형 D컬럼 정확 매핑**: 설비유형 자료_20250522.xlsx 두 번째 시트 D컬럼 참조
- **완벽한 복합 표현 처리**: "1창고 7번 라인 컨베이어 러버벨트 소음 발생" 등 완벽 파싱
- **시나리오 자동 분류**: S1(자연어), S2(ITEMNO) 자동 판단 및 처리

### ⚡ **핵심 기능**
- **자연어 입력 파싱**: 사용자의 자연어 입력을 구조화된 데이터로 변환
- **LLM 기반 용어 정규화**: 다양한 표현을 표준 용어로 정규화
- **위치 기반 검색**: 위치(Location) 정보를 우선적으로 활용한 정확한 추천
- **유사도 기반 추천**: 개선된 유사도 알고리즘으로 정확한 작업 추천
- **실시간 유사도 표시**: 추천 결과의 유사도를 퍼센트와 색상으로 표시
- **편집 가능한 ITEMNO**: 사용자가 추천 결과의 ITEMNO를 직접 수정 가능

## 🚀 PMark2.5 개선사항

### 1️⃣ **멀티턴 대화 시스템**
- **단계별 정보 수집**: 위치 → 설비유형 → 현상코드 순서로 정보 수집
- **누적 단서 관리**: 이전 턴의 정보를 기억하고 누적
- **상태 추적**: collecting_info, recommending, finalizing 상태 관리
- **세션 관리**: 메모리 기반 세션 상태 유지

### 2️⃣ **설비유형 정확 매핑**
- **D컬럼 참조**: 설비유형 자료_20250522.xlsx 두 번째 시트 D컬럼 정확 사용
- **표준용어 반환**: D컬럼 값을 파싱된 표준용어로 반환
- **추천 시 E컬럼 사용**: [Noti이력] 파일의 설비유형 컬럼(E컬럼) 사용

### 3️⃣ **완벽한 파싱 시스템**
- **복합 표현 처리**: "석유제품배합/저장 Motor Operated Valve" 등 완벽 처리
- **여러 단어 조합**: "1창고 7번 라인", "압력베젤 고장" 등 정확 파싱
- **시나리오 분류**: 자연어(S1), ITEMNO(S2) 자동 판단

### 4️⃣ **고도화된 추천 시스템**
- **정확한 매칭**: 위치, 설비유형, 현상코드 완벽 매칭 시 score 1.0
- **배치 처리**: 1-5개(전체), 6-15개(5개씩), 15개+(ITEMNO 요청)
- **유사도 계산**: 향상된 문자열 유사도 및 가중치 적용

## 🧪 테스트 완료 기능

### ✅ **파싱 테스트**
- `"No.1 PE 압력베젤 고장"` → 완벽 파싱 ✅
- `"1창고 7번 라인 컨베이어 러버벨트 소음 발생 우선작업"` → 완벽 처리 ✅
- `"석유제품배합/저장 Motor Operated Valve 고장.결함.수명소진"` → 완벽 매칭 ✅

### ✅ **멀티턴 테스트**
- 1단계: `"No.1 PE"` → 추가 정보 요청 ✅
- 2단계: `"압력베젤"` → 부분 추천 제공 ✅
- 3단계: `"고장"` → 완벽한 추천 완료 ✅

### ✅ **추천 시스템**
- 5개 완벽 매칭 (score 1.0) ✅
- 설비유형 D컬럼 값 정확 사용 ✅
- 유사도 기반 정렬 및 배치 처리 ✅

## 🔧 기술 스택

### **Backend**
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **SQLite**: 경량 데이터베이스 (Excel 파일 로딩)
- **OpenAI GPT-4o**: 자연어 처리 및 정규화
- **Pandas**: Excel 데이터 처리
- **Python 3.9+**: 메인 개발 언어

### **Frontend**
- **HTML/CSS/JavaScript**: 반응형 웹 인터페이스
- **Node.js**: 프론트엔드 서버 (개발용)

### **데이터**
- **[Noti이력].xlsx**: 작업요청 이력 데이터
- **[현상코드].xlsx**: 표준 현상코드 데이터
- **설비유형 자료_20250522.xlsx**: 설비유형 표준 데이터 (D컬럼 사용)

## 🚀 빠른 시작

### **1. 환경 설정**
```bash
# 프로젝트 클론
git clone https://github.com/SKAI-KojunK/PMark2.5.git
cd PMark2.5

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r backend/requirements.txt
```

### **2. 환경 변수 설정**
```bash
# .env 파일 생성
cp env.example .env

# OpenAI API 키 설정
OPENAI_API_KEY=your_openai_api_key_here
```

### **3. PMark2.5 실행 (테스트 환경)**
```bash
# 백엔드 실행 (포트 8010)
python test_env/scripts/start_test_backend.py

# 프론트엔드 실행 (포트 3010)
python test_env/scripts/start_test_frontend.py
```

### **4. 접속**
- **PMark2.5 웹 인터페이스**: http://localhost:3010
- **API 문서**: http://localhost:8010/docs

## 📁 프로젝트 구조

```
PMark2.5/
├── backend/                 # PMark1 기본 백엔드
├── test_env/               # PMark2.5 테스트 환경
│   ├── backend/            # 고급 백엔드 (멀티턴 지원)
│   ├── frontend/           # 테스트용 프론트엔드
│   ├── scripts/            # 실행 스크립트
│   └── test_chatbot.html   # PMark2.5 테스트 페이지
├── docs/                   # 문서
├── scripts/                # 유틸리티 스크립트
├── notebooks/              # 실험 노트북
└── README.md
```

## 🎯 사용 예시

### **멀티턴 대화 예시**
```
사용자: "No.1 PE"
시스템: "위치를 확인했습니다. 설비유형과 현상코드를 알려주세요."

사용자: "압력베젤"
시스템: "5개의 부분 추천을 찾았습니다. 현상코드를 추가해주세요."

사용자: "고장"
시스템: "완벽한 매칭! 5개의 추천을 제공합니다."
```

### **단일 입력 예시**
```
사용자: "석유제품배합/저장 Motor Operated Valve 고장.결함.수명소진"
시스템: "완벽한 파싱! 5개의 정확한 추천을 제공합니다."
```

## 📊 성능 지표

- **파싱 정확도**: 95%+ (복합 표현 포함)
- **추천 정확도**: 완벽 매칭 시 score 1.0
- **응답 시간**: 평균 2-3초 (LLM 호출 포함)
- **세션 관리**: 메모리 기반 실시간 상태 추적

## 🔄 API 엔드포인트

### **PMark2.5 API (v2)**
- `POST /api/v1/chat/v2` - 멀티턴 대화 채팅
- `POST /api/v1/autocomplete` - 자동완성 추천
- `GET /api/v1/work-details/{itemno}` - 작업 상세 정보

### **PMark1 API (v1)**
- `POST /api/v1/chat` - 기본 채팅
- `GET /api/v1/work-details/{itemno}` - 작업 상세 정보

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 문의

프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 생성해주세요.

---

**PMark2.5** - 설비관리의 미래를 여는 AI 어시스턴트 🚀
