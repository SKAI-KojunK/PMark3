from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, work_details, autocomplete
from app.database import db_manager
from app.config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    logger.info("🚀 PMark2.5 AI Assistant 시작 중...")
    try:
        # 엑셀 데이터를 불러와 DB를 초기화합니다.
        db_manager.load_excel_data()
        logger.info("✅ 데이터베이스 초기화 완료 (from Excel)")
    except Exception as e:
        logger.error(f"⚠️ 데이터베이스 초기화 오류: {e}")
        logger.info("📝 샘플 데이터로 시작합니다.")
        db_manager._create_sample_data() # 샘플 데이터 생성 호출 추가

app.include_router(chat.router, prefix="/api/v1")
app.include_router(work_details.router, prefix="/api/v1")
app.include_router(autocomplete.router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    print("🛑 PMark2.5 AI Assistant 종료 중...")
    db_manager.close()

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "PMark2.5 AI Assistant API",
        "version": Config.API_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=Config.BACKEND_PORT,
        reload=Config.DEBUG
    ) 