from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
import os

from database import create_tables
from routers import podcast, tts, hls, system
from config import settings

# FastAPI 앱 생성
app = FastAPI(
    title="LGraph Multi-Agent Podcast System",
    description="Korean Podcast Production System using Multi-Agent Architecture",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """앱 시작시 데이터베이스 테이블 생성"""
    create_tables()
    print("🚀 LGraph Multi-Agent System API started!")

# 라우터 포함
app.include_router(system.router)
app.include_router(podcast.router)
app.include_router(tts.router)
app.include_router(hls.router)


# 예외 처리
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리기: 처리되지 않은 모든 예외를 500으로 처리합니다."""
    error_message = f"❌ 서버 내부 오류 발생: {exc}"
    print(error_message)
    
    # 디버그 모드일 때만 상세 에러 노출
    detail = str(exc) if settings.DEBUG else "An unexpected error occurred. Please contact administrator."
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": detail
        },
    )

if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 