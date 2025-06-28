from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db, User
from schemas import (
    PodcastRequestCreate, 
    PodcastTaskResponse, 
    PodcastTaskSummary,
    TTSResultResponse,
    PodcastRegenerateRequest
)
from services import podcast_service
from utils.auth_dependencies import get_current_active_user, get_admin_user

router = APIRouter(
    prefix="/podcast",
    tags=["Podcast Tasks"]
)

@router.post("/create", response_model=PodcastTaskResponse)
async def create_podcast_task_endpoint(
    request: PodcastRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    팟캐스트 생성 작업 시작 - 멀티 에이전트 파이프라인 실행
    
    Headers:
        Authorization: Bearer {access_token}
    """
    return podcast_service.create_podcast_task(db, request, current_user.id)

@router.get("/tasks", response_model=List[PodcastTaskSummary])
async def list_podcast_tasks_endpoint(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    사용자의 팟캐스트 작업 목록 조회 (페이지네이션 지원)
    
    Headers:
        Authorization: Bearer {access_token}
    """
    tasks = podcast_service.get_podcast_tasks_by_user(db, current_user.id, skip=skip, limit=limit)
    return tasks

@router.get("/tasks/{task_id}", response_model=PodcastTaskResponse)
async def get_podcast_task_endpoint(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    특정 팟캐스트 작업 상세 정보 조회 (에이전트 실행 결과 포함)
    
    Headers:
        Authorization: Bearer {access_token}
    """
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 작업 소유자 확인 (관리자는 모든 작업 조회 가능)
    if task.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    
    return task

@router.put("/tasks/{task_id}/regenerate", response_model=PodcastTaskResponse)
async def regenerate_podcast_tts_endpoint(
    task_id: int,
    request: PodcastRegenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    사용자가 수정한 스크립트로 팟캐스트 음성을 다시 생성합니다.
    
    - 기존 TTS, HLS 결과는 삭제되고 새로 생성됩니다.
    - 전체 에이전트 파이프라인을 재실행하지 않고, TTS 생성 단계만 실행하여 효율적입니다.
    
    Headers:
        Authorization: Bearer {access_token}
    """
    updated_task = podcast_service.regenerate_tts_for_task(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
        new_script=request.script
    )
    return updated_task

@router.get("/tasks/{task_id}/status")
async def get_task_status_endpoint(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    작업 진행 상태 및 실행 시간 정보 조회
    
    Headers:
        Authorization: Bearer {access_token}
    """
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 작업 소유자 확인 (관리자는 모든 작업 조회 가능)
    if task.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    특정 작업의 멀티 에이전트 실행 결과 상세 조회
    
    Headers:
        Authorization: Bearer {access_token}
    """
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 작업 소유자 확인 (관리자는 모든 작업 조회 가능)
    if task.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    
    agents = podcast_service.get_agent_results_by_task_id(db, task_id)
    return {
        "task_id": task_id,
        "total_agents": len(agents),
        "agents": agents
    }

@router.get("/tasks/{task_id}/tts", response_model=TTSResultResponse)
async def get_task_tts_result_endpoint(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    특정 작업의 TTS 스크립트 및 음성 생성 결과 조회
    
    Headers:
        Authorization: Bearer {access_token}
    """
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 작업 소유자 확인 (관리자는 모든 작업 조회 가능)
    if task.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    
    tts_result = podcast_service.get_tts_result_by_task_id(db, task_id)
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found for this task")
    return tts_result

@router.delete("/tasks/{task_id}")
async def delete_podcast_task_endpoint(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    팟캐스트 작업 및 관련 데이터 삭제 (TTS, HLS 결과 포함)
    
    Headers:
        Authorization: Bearer {access_token}
    """
    task = podcast_service.get_podcast_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 작업 소유자 확인 (관리자는 모든 작업 삭제 가능)
    if task.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
    
    success = podcast_service.delete_podcast_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": f"Task {task_id} deleted successfully"}

# 관리자 전용 엔드포인트
@router.get("/admin/tasks", response_model=List[PodcastTaskSummary])
async def list_all_podcast_tasks_endpoint(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    전체 팟캐스트 작업 목록 조회 (관리자 전용)
    
    Headers:
        Authorization: Bearer {admin_access_token}
    """
    tasks = podcast_service.get_podcast_tasks(db, skip=skip, limit=limit)
    return tasks

@router.get("/stats")
async def get_system_stats_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    사용자별 통계 조회 (관리자는 시스템 전체 통계)
    
    Headers:
        Authorization: Bearer {access_token}
    """
    if current_user.role.value == "admin":
        # 관리자는 시스템 전체 통계
        stats = podcast_service.get_system_stats(db)
    else:
        # 일반 사용자는 개인 통계
        stats = podcast_service.get_user_stats(db, current_user.id)
    
    return stats 