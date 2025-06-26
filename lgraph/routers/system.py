from fastapi import APIRouter
from datetime import datetime
from celery_app import celery_app

router = APIRouter(
    tags=["System"]
)

@router.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "LGraph Multi-Agent Podcast System API",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "celery_status": "active" if celery_app.control.inspect().active() else "inactive"
    } 