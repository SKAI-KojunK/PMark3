import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """애플리케이션 설정 클래스"""
    
    # API 설정
    API_TITLE = "PMark2.5 - AI 작업요청 Assistant (TEST)"
    API_VERSION = "2.5.0"
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # 포트 설정 (테스트 환경용 - 기존과 충돌 방지)
    BACKEND_PORT = int(os.getenv("TEST_BACKEND_PORT", 8010))
    FRONTEND_PORT = int(os.getenv("TEST_FRONTEND_PORT", 3010))
    
    # LLM 설정
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, local
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # 데이터베이스 설정 (테스트용)
    DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./data/test_notifications.db")
    SQLITE_DB_PATH = os.getenv("TEST_SQLITE_DB_PATH", "./data/test_notifications.db")
    
    # 파일 경로 설정 (절대 경로 사용) - 영구적 수정
    # 현재 파일(test_env/backend/app/config.py)에서 프로젝트 루트까지의 경로 계산
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # test_env/backend/app/
    BACKEND_DIR = os.path.dirname(CURRENT_DIR)  # test_env/backend/
    TEST_ENV_DIR = os.path.dirname(BACKEND_DIR)  # test_env/
    PROJECT_ROOT = os.path.dirname(TEST_ENV_DIR)  # PMark2-Dev/
    
    # 절대 경로로 파일 경로 설정
    NOTIFICATION_HISTORY_FILE = os.getenv("NOTIFICATION_HISTORY_FILE") or os.path.join(PROJECT_ROOT, "[Noti이력].xlsx")
    STATUS_CODE_FILE = os.getenv("STATUS_CODE_FILE") or os.path.join(PROJECT_ROOT, "[현상코드].xlsx")
    EQUIPMENT_TYPE_FILE = os.getenv("EQUIPMENT_TYPE_FILE") or os.path.join(PROJECT_ROOT, "설비유형 자료_20250522.xlsx")
    
    # 벡터 DB 설정 (테스트용)
    VECTOR_DB_PATH = os.getenv("TEST_VECTOR_DB_PATH", "./data/test_vector_db")
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

# 디버깅용 경로 출력 함수
def print_file_paths():
    """파일 경로 디버깅용"""
    print("=== 파일 경로 설정 ===")
    print(f"PROJECT_ROOT: {Config.PROJECT_ROOT}")
    print(f"NOTIFICATION_HISTORY_FILE: {Config.NOTIFICATION_HISTORY_FILE}")
    print(f"STATUS_CODE_FILE: {Config.STATUS_CODE_FILE}")
    print(f"EQUIPMENT_TYPE_FILE: {Config.EQUIPMENT_TYPE_FILE}")
    print(f"파일 존재 여부:")
    print(f"  - [Noti이력].xlsx: {os.path.exists(Config.NOTIFICATION_HISTORY_FILE)}")
    print(f"  - [현상코드].xlsx: {os.path.exists(Config.STATUS_CODE_FILE)}")
    print(f"  - 설비유형 자료_20250522.xlsx: {os.path.exists(Config.EQUIPMENT_TYPE_FILE)}")
    print("===================")

if __name__ == "__main__":
    print_file_paths() 