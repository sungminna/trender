from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os

from database import get_db, create_tables, PodcastTask, AgentResult, TaskStatus, TTSResult
from schemas import (
    PodcastRequestCreate, 
    PodcastTaskResponse, 
    PodcastTaskSummary,
    TaskStatusUpdate,
    TTSResultResponse
)
from celery_app import process_podcast_task, generate_tts_audio, celery_app
from tts import get_tts_generator

# FastAPI 앱 생성
app = FastAPI(
    title="LGraph Multi-Agent Podcast System",
    description="Korean Podcast Production System using Multi-Agent Architecture",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """앱 시작시 데이터베이스 테이블 생성"""
    create_tables()
    print("🚀 LGraph Multi-Agent System API started!")


@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "LGraph Multi-Agent Podcast System API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "celery_status": "active" if celery_app.control.inspect().active() else "inactive"
    }


@app.post("/podcast/create", response_model=PodcastTaskResponse)
async def create_podcast_task(
    request: PodcastRequestCreate,
    db: Session = Depends(get_db)
):
    """
    새로운 팟캐스트 생성 작업을 시작합니다.
    작업은 백그라운드에서 비동기로 처리됩니다.
    """
    # 데이터베이스에 작업 생성
    db_task = PodcastTask(
        user_request=request.user_request,
        status=TaskStatus.PENDING,
        created_at=datetime.utcnow()
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Celery 백그라운드 작업 시작
    celery_task = process_podcast_task.delay(db_task.id, request.user_request)
    
    print(f"🎯 새로운 팟캐스트 작업 생성됨 - Task ID: {db_task.id}, Celery Task ID: {celery_task.id}")
    
    return db_task


@app.get("/podcast/tasks", response_model=List[PodcastTaskSummary])
async def list_podcast_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """모든 팟캐스트 작업 목록을 반환합니다."""
    tasks = db.query(PodcastTask).offset(skip).limit(limit).all()
    return tasks


@app.get("/podcast/tasks/{task_id}", response_model=PodcastTaskResponse)
async def get_podcast_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 팟캐스트 작업의 상세 정보를 반환합니다."""
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@app.get("/podcast/tasks/{task_id}/status")
async def get_task_status(
    task_id: int,
    db: Session = Depends(get_db)
):
    """작업의 현재 상태를 반환합니다."""
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task_id,
        "status": task.status,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message
    }


@app.get("/podcast/tasks/{task_id}/agents")
async def get_task_agent_results(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 작업의 모든 에이전트 실행 결과를 반환합니다."""
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    agents = db.query(AgentResult).filter(AgentResult.task_id == task_id).all()
    return {
        "task_id": task_id,
        "total_agents": len(agents),
        "agents": agents
    }


@app.get("/podcast/tasks/{task_id}/tts", response_model=TTSResultResponse)
async def get_task_tts_result(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 작업의 TTS 결과를 반환합니다."""
    # 작업 존재 확인
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # TTS 결과 조회
    tts_result = db.query(TTSResult).filter(TTSResult.task_id == task_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found for this task")
    
    return tts_result


@app.get("/podcast/tts", response_model=List[TTSResultResponse])
async def list_tts_results(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """모든 TTS 결과 목록을 반환합니다."""
    tts_results = db.query(TTSResult).offset(skip).limit(limit).all()
    return tts_results


@app.get("/podcast/tts/{tts_id}/script")
async def get_tts_script_content(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """TTS 스크립트 내용을 텍스트로 반환합니다."""
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    return {
        "tts_id": tts_id,
        "task_id": tts_result.task_id,
        "user_request": tts_result.user_request,
        "script_content": tts_result.script_content,
        "script_length": len(tts_result.script_content),
        "is_audio_generated": tts_result.is_audio_generated,
        "audio_file_name": tts_result.audio_file_name
    }


@app.delete("/podcast/tasks/{task_id}")
async def delete_podcast_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """팟캐스트 작업을 삭제합니다."""
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 관련 TTS 결과와 에이전트 결과도 함께 삭제
    db.query(TTSResult).filter(TTSResult.task_id == task_id).delete()
    db.query(AgentResult).filter(AgentResult.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    
    return {"message": f"Task {task_id} deleted successfully"}


@app.post("/podcast/tts/{tts_id}/generate-audio")
async def generate_tts_audio_endpoint(
    tts_id: int,
    voice_name: str = "Kore",
    db: Session = Depends(get_db)
):
    """TTS 결과로부터 음원을 생성합니다."""
    # TTS 결과 존재 확인
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    # 이미 음원이 생성되었는지 확인
    if tts_result.is_audio_generated == "true":
        return {
            "message": "Audio already generated",
            "tts_id": tts_id,
            "audio_file_name": tts_result.audio_file_name,
            "audio_file_size": tts_result.audio_file_size,
            "audio_duration": tts_result.audio_duration
        }
    
    # 비동기 음원 생성 작업 시작
    celery_task = generate_tts_audio.delay(tts_id)
    
    return {
        "message": "Audio generation started",
        "tts_id": tts_id,
        "celery_task_id": celery_task.id,
        "status": "processing"
    }


@app.get("/podcast/tts/{tts_id}/audio-status")
async def get_tts_audio_status(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """TTS 음원 생성 상태를 확인합니다."""
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    return {
        "tts_id": tts_id,
        "is_audio_generated": tts_result.is_audio_generated,
        "tts_status": tts_result.tts_status,
        "audio_file_name": tts_result.audio_file_name,
        "audio_file_size": tts_result.audio_file_size,
        "audio_duration": tts_result.audio_duration,
        "audio_generated_at": tts_result.audio_generated_at,
        "error_message": tts_result.error_message
    }


@app.get("/podcast/tts/voices")
async def get_available_voices():
    """사용 가능한 TTS 음성 목록을 반환합니다."""
    try:
        tts_generator = get_tts_generator()
        voices = tts_generator.get_available_voices()
        return {
            "total_voices": len(voices),
            "voices": voices,
            "recommended_for_korean": ["Kore", "Leda", "Iapetus", "Alnilam"]
        }
    except Exception as e:
        return {
            "error": "Failed to get voices",
            "detail": str(e),
            "default_voices": ["Kore", "Leda", "Iapetus", "Alnilam"]
        }



@app.get("/podcast/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """시스템 통계를 반환합니다."""
    total_tasks = db.query(PodcastTask).count()
    pending_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.PENDING).count()
    processing_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.PROCESSING).count()
    completed_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.COMPLETED).count()
    failed_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.FAILED).count()
    
    total_agents = db.query(AgentResult).count()
    
    # TTS 관련 통계
    total_tts_results = db.query(TTSResult).count()
    audio_generated_count = db.query(TTSResult).filter(TTSResult.is_audio_generated == "true").count()
    audio_pending_count = total_tts_results - audio_generated_count
    
    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "processing_tasks": processing_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "total_agent_executions": total_agents,
        "total_tts_results": total_tts_results,
        "audio_generated_count": audio_generated_count,
        "audio_pending_count": audio_pending_count,
        "celery_active_tasks": len(celery_app.control.inspect().active() or {})
    }


# 예외 처리
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 처리기"""
    print(f"❌ Unexpected error: {str(exc)}")
    return {
        "error": "Internal server error",
        "detail": str(exc) if os.getenv("DEBUG") == "true" else "An unexpected error occurred"
    }


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