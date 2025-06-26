"""
공통 Celery 앱 설정
"""

from celery import Celery
import os

# 공통 Celery 앱 인스턴스
celery_app = Celery(
    "lgraph",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Celery 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분 제한
    task_soft_time_limit=25 * 60,  # 25분 소프트 제한
) 