"""
WebSocket 알림 관련 함수들
- Celery Task에서 호출되어 실시간 진행 상황을 클라이언트에게 전송
"""
import asyncio
from typing import Optional
from datetime import datetime
import json
import redis

from sqlalchemy.orm import Session

# 절대 경로로 수정하여 Celery 워커에서 모듈을 찾을 수 있도록 함
from database import TaskStatus, PodcastTask
from utils.websocket_manager import manager
from utils.broker import CHANNEL_NAME, REDIS_URL

# Helper to run coroutine in correct loop context
async def _noop():
    pass


def _run_coroutine_threadsafe(coro):
    """Utility to run coroutine either in existing loop or a new loop"""
    try:
        loop = asyncio.get_running_loop()
        # If we're in the main FastAPI event loop, schedule the task asynchronously
        loop.create_task(coro)
    except RuntimeError:
        # No running loop in this thread (e.g., Celery worker); run synchronously
        asyncio.run(coro)


def _publish_redis(message: dict):
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.publish(CHANNEL_NAME, json.dumps(message, ensure_ascii=False))
    except Exception as e:
        print(f"⚠️ Redis publish 실패: {e}")


def _build_task_status_msg(task_id, user_id, status, error_message, additional):
    msg = {
        "type": "task_status_update",
        "task_id": task_id,
        "user_id": user_id,
        "status": status.value,
        "timestamp": datetime.utcnow().isoformat(),
        "error_message": error_message
    }
    if additional:
        msg.update(additional)
    return msg


def _send_task_status_update_async(task_id: int, user_id: int, status: TaskStatus, 
                                 error_message: Optional[str] = None, 
                                 additional_data: Optional[dict] = None):
    """
    WebSocket을 통한 비동기 작업 상태 업데이트 전송
    - 동기 함수에서 호출 가능하도록 새 이벤트 루프에서 실행
    """
    message = _build_task_status_msg(task_id, user_id, status, error_message, additional_data)
    _publish_redis(message)
    # local broadcast for API process
    try:
        _run_coroutine_threadsafe(manager.send_personal_message(message, user_id))
    except Exception:
        pass


def update_task_status_with_websocket(db: Session, task_id: int, status: TaskStatus, 
                                    error_message: Optional[str] = None,
                                    final_result: Optional[dict] = None,
                                    completed_at: Optional[datetime] = None):
    """
    데이터베이스 작업 상태 업데이트 + WebSocket 실시간 알림
    """
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        return False
    
    # 상태 업데이트
    task.status = status
    if error_message:
        task.error_message = error_message
    if final_result:
        task.final_result = final_result
    if completed_at:
        task.completed_at = completed_at
    elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        task.completed_at = datetime.utcnow()
    
    if status == TaskStatus.PROCESSING and not task.started_at:
        task.started_at = datetime.utcnow()
    
    db.add(task)
    db.commit()
    
    # WebSocket을 통한 실시간 알림
    additional_data = {}
    if final_result:
        additional_data["final_result"] = final_result
    if task.started_at:
        additional_data["started_at"] = task.started_at.isoformat()
    if task.completed_at:
        additional_data["completed_at"] = task.completed_at.isoformat()
    
    _send_task_status_update_async(task_id, task.user_id, status, error_message, additional_data)
    return True


def send_agent_progress_update(task_id: int, user_id: int, agent_name: str, 
                              agent_status: TaskStatus, progress_data: Optional[dict] = None):
    """
    에이전트 진행 상황 WebSocket 업데이트 (Celery 작업에서 호출)
    """
    message = {
        "type": "agent_progress_update",
        "task_id": task_id,
        "user_id": user_id,
        "agent_name": agent_name,
        "agent_status": agent_status.value,
        "timestamp": datetime.utcnow().isoformat()
    }
    if progress_data:
        message.update(progress_data)

    # Always publish to Redis so that API process forwards to WebSocket clients
    _publish_redis(message)

    # Additionally, if we're inside the API process (running loop exists), push directly
    try:
        _run_coroutine_threadsafe(
            manager.send_personal_message(message, user_id)
        )
    except Exception:
        pass


def send_tts_progress_update(task_id: int, user_id: int, tts_status: str, 
                            progress_data: Optional[dict] = None):
    """
    TTS 진행 상황 WebSocket 업데이트 (Celery 작업에서 호출)
    """
    message = {
        "type": "tts_progress_update",
        "task_id": task_id,
        "user_id": user_id,
        "tts_status": tts_status,
        "timestamp": datetime.utcnow().isoformat()
    }
    if progress_data:
        message.update(progress_data)

    _publish_redis(message)

    try:
        _run_coroutine_threadsafe(
            manager.send_personal_message(message, user_id)
        )
    except Exception:
        pass 