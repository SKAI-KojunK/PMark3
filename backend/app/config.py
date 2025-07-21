import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """애플리케이션 설정 클래스"""
    
    # API 설정
    API_TITLE = "PMark1 - AI 작업요청 Assistant"
    API_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # 포트 설정 (기존 프로젝트와 충돌 방지)
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8001))
    FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 3001))
    
    # LLM 설정
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, local
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # 데이터베이스 설정
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/sample_notifications.db")
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/sample_notifications.db")
    
    # 파일 경로 설정 (절대 경로 사용)
    # 현재 파일(backend/app/config.py)에서 프로젝트 루트까지의 경로 계산
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/app/
    BACKEND_DIR = os.path.dirname(CURRENT_DIR)  # backend/
    PROJECT_ROOT = os.path.dirname(BACKEND_DIR)  # PMark2-Dev/
    
    # 절대 경로로 파일 경로 설정
    NOTIFICATION_HISTORY_FILE = os.getenv("NOTIFICATION_HISTORY_FILE") or os.path.join(PROJECT_ROOT, "[Noti이력].xlsx")
    STATUS_CODE_FILE = os.getenv("STATUS_CODE_FILE") or os.path.join(PROJECT_ROOT, "[현상코드].xlsx")
    EQUIPMENT_TYPE_FILE = os.getenv("EQUIPMENT_TYPE_FILE") or os.path.join(PROJECT_ROOT, "설비유형 자료_20250522.xlsx")
    
    # 벡터 DB 설정
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # 추천 설정
    MAX_RECOMMENDATIONS = int(os.getenv("MAX_RECOMMENDATIONS", 15))
    MIN_RECOMMENDATIONS = int(os.getenv("MIN_RECOMMENDATIONS", 1))
    
    # 에러 처리 설정
    MAX_SQL_RETRY = int(os.getenv("MAX_SQL_RETRY", 5))
    
    # CORS 설정 (여러 사용자 접속 허용)
    ALLOWED_ORIGINS = [
        f"http://localhost:{FRONTEND_PORT}",
        f"http://127.0.0.1:{FRONTEND_PORT}",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3001",
        "*"  # 개발 환경에서 모든 origin 허용 (프로덕션에서는 제거 필요)
    ] 