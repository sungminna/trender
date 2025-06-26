from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas import (
    PodcastRequestCreate, 
    PodcastTaskResponse, 
    PodcastTaskSummary,
    TTSResultResponse
)
from services import podcast_service

router = APIRouter(
    prefix="/podcast",
    tags=["Podcast Tasks"]
)

@router.post("/create", response_model=PodcastTaskResponse)
async def create_podcast_task_endpoint(
    request: PodcastRequestCreate,
    db: Session = Depends(get_db)
):
    """팟캐스트 생성 작업 시작 - 멀티 에이전트 파이프라인 실행"""
    return podcast_service.create_podcast_task(db, request)

@router.get("/tasks", response_model=List[PodcastTaskSummary])
async def list_podcast_tasks_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """전체 팟캐스트 작업 목록 조회 (페이지네이션 지원)"""
    tasks = podcast_service.get_podcast_tasks(db, skip=skip, limit=limit)
    return tasks

@router.get("/tasks/{task_id}", response_model=PodcastTaskResponse)
async def get_podcast_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 팟캐스트 작업 상세 정보 조회 (에이전트 실행 결과 포함)"""
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/tasks/{task_id}/status")
async def get_task_status_endpoint(
    task_id: int,
    db: Session = Depends(get_db)
):
    """작업 진행 상태 및 실행 시간 정보 조회"""
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task.id,
        "status": task.status,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message
    }

@router.get("/tasks/{task_id}/agents")
async def get_task_agent_results_endpoint(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 작업의 멀티 에이전트 실행 결과 상세 조회"""
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    agents = podcast_service.get_agent_results_by_task_id(db, task_id)
    return {
        "task_id": task_id,
        "total_agents": len(agents),
        "agents": agents
    }

@router.get("/tasks/{task_id}/tts", response_model=TTSResultResponse)
async def get_task_tts_result_endpoint(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 작업의 TTS 스크립트 및 음성 생성 결과 조회"""
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tts_result = podcast_service.get_tts_result_by_task_id(db, task_id)
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found for this task")
    return tts_result

@router.delete("/tasks/{task_id}")
async def delete_podcast_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db)
):
    """팟캐스트 작업 및 관련 데이터 삭제 (TTS, HLS 결과 포함)"""
    success = podcast_service.delete_podcast_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": f"Task {task_id} deleted successfully"}

@router.get("/stats")
async def get_system_stats_endpoint(db: Session = Depends(get_db)):
    """시스템 전체 통계 조회 (작업 상태별 집계, Celery 워커 상태 포함)"""
    stats = podcast_service.get_system_stats(db)
    return stats 