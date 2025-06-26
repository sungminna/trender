"""
Podcast Task 관련 비즈니스 로직을 처리하는 서비스 모듈
"""
from sqlalchemy.orm import Session
from typing import List, Optional

from database import PodcastTask, AgentResult, TTSResult, TaskStatus
from schemas import PodcastRequestCreate
from celery_app import celery_app
from tasks.podcast_tasks import process_podcast_task

def create_podcast_task(db: Session, request: PodcastRequestCreate) -> PodcastTask:
    """새로운 팟캐스트 작업을 생성하고 백그라운드 처리를 시작합니다."""
    db_task = PodcastTask(
        user_request=request.user_request,
        status=TaskStatus.PENDING
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Celery 백그라운드 작업 시작
    celery_task = process_podcast_task.delay(db_task.id, request.user_request)
    print(f"🎯 새로운 팟캐스트 작업 생성됨 - Task ID: {db_task.id}, Celery Task ID: {celery_task.id}")
    
    return db_task

def get_podcast_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[PodcastTask]:
    """모든 팟캐스트 작업 목록을 조회합니다."""
    return db.query(PodcastTask).offset(skip).limit(limit).all()

def get_podcast_task_by_id(db: Session, task_id: int) -> Optional[PodcastTask]:
    """ID로 특정 팟캐스트 작업을 조회합니다."""
    return db.query(PodcastTask).filter(PodcastTask.id == task_id).first()

def get_agent_results_by_task_id(db: Session, task_id: int) -> List[AgentResult]:
    """특정 작업에 대한 모든 에이전트 실행 결과를 조회합니다."""
    return db.query(AgentResult).filter(AgentResult.task_id == task_id).all()

def get_tts_result_by_task_id(db: Session, task_id: int) -> Optional[TTSResult]:
    """특정 작업에 대한 TTS 결과를 조회합니다."""
    return db.query(TTSResult).filter(TTSResult.task_id == task_id).first()

def delete_podcast_task(db: Session, task_id: int) -> bool:
    """ID로 팟캐스트 작업을 삭제합니다."""
    task = get_podcast_task_by_id(db, task_id)
    if not task:
        return False
    
    # 관련 TTS 결과와 에이전트 결과도 함께 삭제
    db.query(TTSResult).filter(TTSResult.task_id == task_id).delete(synchronize_session=False)
    db.query(AgentResult).filter(AgentResult.task_id == task_id).delete(synchronize_session=False)
    db.delete(task)
    db.commit()
    return True

def get_system_stats(db: Session) -> dict:
    """시스템 전체 통계를 계산합니다."""
    total_tasks = db.query(PodcastTask).count()
    pending_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.PENDING).count()
    processing_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.PROCESSING).count()
    completed_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.COMPLETED).count()
    failed_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.FAILED).count()
    
    total_agents = db.query(AgentResult).count()
    
    total_tts_results = db.query(TTSResult).count()
    audio_generated_count = db.query(TTSResult).filter(TTSResult.is_audio_generated == "true").count()
    
    try:
        active_celery_tasks = len(celery_app.control.inspect().active() or {})
    except Exception:
        active_celery_tasks = -1 # Celery 연결 실패 시

    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "processing_tasks": processing_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "total_agent_executions": total_agents,
        "total_tts_results": total_tts_results,
        "audio_generated_count": audio_generated_count,
        "audio_pending_count": total_tts_results - audio_generated_count,
        "celery_active_tasks": active_celery_tasks
    } 