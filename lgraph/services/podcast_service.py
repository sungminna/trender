"""
Podcast Task 비즈니스 로직 서비스
- 팟캐스트 생성 작업의 CRUD 및 상태 관리
- Celery 백그라운드 작업 연동
- 멀티 에이전트 파이프라인 결과 처리
"""
from sqlalchemy.orm import Session
from typing import List, Optional

from database import PodcastTask, AgentResult, TTSResult, TaskStatus
from schemas import PodcastRequestCreate
from celery_app import celery_app
from tasks.podcast_tasks import process_podcast_task

def create_podcast_task(db: Session, request: PodcastRequestCreate, user_id: int) -> PodcastTask:
    """
    새로운 팟캐스트 생성 작업 생성 및 백그라운드 처리 시작
    
    Flow:
    1. DB에 PENDING 상태 작업 생성
    2. Celery를 통한 멀티 에이전트 파이프라인 비동기 실행
    3. 생성된 작업 정보 반환
    """
    db_task = PodcastTask(
        user_id=user_id,
        user_request=request.user_request,
        status=TaskStatus.PENDING
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Celery 백그라운드 작업 시작
    celery_task = process_podcast_task.delay(db_task.id, request.user_request)
    print(f"🎯 새로운 팟캐스트 작업 생성됨 - User ID: {user_id}, Task ID: {db_task.id}, Celery Task ID: {celery_task.id}")
    
    return db_task

def get_podcast_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[PodcastTask]:
    """팟캐스트 작업 목록 페이지네이션 조회 (전체)"""
    return db.query(PodcastTask).offset(skip).limit(limit).all()

def get_podcast_tasks_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[PodcastTask]:
    """특정 사용자의 팟캐스트 작업 목록 조회"""
    return db.query(PodcastTask).filter(PodcastTask.user_id == user_id).offset(skip).limit(limit).all()

def get_podcast_task_by_id(db: Session, task_id: int) -> Optional[PodcastTask]:
    """특정 팟캐스트 작업 조회 (에이전트 결과 포함)"""
    return db.query(PodcastTask).filter(PodcastTask.id == task_id).first()

def get_agent_results_by_task_id(db: Session, task_id: int) -> List[AgentResult]:
    """특정 작업의 멀티 에이전트 실행 결과 조회"""
    return db.query(AgentResult).filter(AgentResult.task_id == task_id).all()

def get_tts_result_by_task_id(db: Session, task_id: int) -> Optional[TTSResult]:
    """특정 작업의 TTS 스크립트 및 음성 생성 결과 조회"""
    return db.query(TTSResult).filter(TTSResult.task_id == task_id).first()

def delete_podcast_task(db: Session, task_id: int) -> bool:
    """
    팟캐스트 작업 및 관련 데이터 삭제
    - 연관된 TTS 결과 및 에이전트 결과도 함께 삭제
    - 데이터 정합성 유지를 위한 트랜잭션 처리
    """
    task = get_podcast_task_by_id(db, task_id)
    if not task:
        return False
    
    # 관련 데이터 연쇄 삭제
    db.query(TTSResult).filter(TTSResult.task_id == task_id).delete(synchronize_session=False)
    db.query(AgentResult).filter(AgentResult.task_id == task_id).delete(synchronize_session=False)
    db.delete(task)
    db.commit()
    return True

def get_system_stats(db: Session) -> dict:
    """
    시스템 전체 통계 계산
    - 작업 상태별 집계
    - 에이전트 실행 통계
    - TTS 생성 현황
    - Celery 워커 상태
    """
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
        active_celery_tasks = -1  # Celery 연결 실패 시

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

def get_user_stats(db: Session, user_id: int) -> dict:
    """
    특정 사용자의 통계 계산
    - 사용자 작업 상태별 집계
    - 사용자의 에이전트 실행 통계
    - 사용자의 TTS 생성 현황
    """
    user_tasks = db.query(PodcastTask).filter(PodcastTask.user_id == user_id)
    
    total_tasks = user_tasks.count()
    pending_tasks = user_tasks.filter(PodcastTask.status == TaskStatus.PENDING).count()
    processing_tasks = user_tasks.filter(PodcastTask.status == TaskStatus.PROCESSING).count()
    completed_tasks = user_tasks.filter(PodcastTask.status == TaskStatus.COMPLETED).count()
    failed_tasks = user_tasks.filter(PodcastTask.status == TaskStatus.FAILED).count()
    
    # 사용자의 에이전트 실행 통계
    user_agent_results = db.query(AgentResult).join(PodcastTask).filter(PodcastTask.user_id == user_id)
    total_agents = user_agent_results.count()
    
    # 사용자의 TTS 결과 통계
    user_tts_results = db.query(TTSResult).join(PodcastTask).filter(PodcastTask.user_id == user_id)
    total_tts_results = user_tts_results.count()
    audio_generated_count = user_tts_results.filter(TTSResult.is_audio_generated == "true").count()
    
    return {
        "user_id": user_id,
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "processing_tasks": processing_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "total_agent_executions": total_agents,
        "total_tts_results": total_tts_results,
        "audio_generated_count": audio_generated_count,
        "audio_pending_count": total_tts_results - audio_generated_count
    } 