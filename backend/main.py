from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import Config
from app.api import chat, work_details
from app.database import db_manager

# FastAPI 앱 생성
app = FastAPI(
    title=Config.API_TITLE,
    version=Config.API_VERSION,
    debug=Config.DEBUG
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(work_details.router, prefix="/api/v1", tags=["work-details"])

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    print("🚀 PMark2 AI Assistant 시작 중...")
    
    # 데이터베이스 초기화
    try:
        db_manager.load_excel_data()
        print("✅ 데이터베이스 초기화 완료")
    except Exception as e:
        print(f"⚠️ 데이터베이스 초기화 오류: {e}")
        print("📝 샘플 데이터로 시작합니다.")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    print("🛑 PMark2 AI Assistant 종료 중...")
    db_manager.close()

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "PMark2 AI Assistant API",
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