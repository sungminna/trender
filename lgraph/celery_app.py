"""
LGraph Celery Application Entry Point

Celery 기반 비동기 작업 처리 시스템
- 팟캐스트 생성 파이프라인의 백그라운드 작업 관리
- Redis 브로커를 통한 작업 큐 관리
- 분산 워커를 통한 확장 가능한 처리

Task Modules:
- tasks/podcast_tasks.py: 멀티 에이전트 팟캐스트 생성
- tasks/tts_tasks.py: TTS 음성 생성 및 MinIO 업로드
- tasks/hls_tasks.py: HLS 스트리밍 변환
- tasks/utils.py: 공통 유틸리티 함수
"""

# Celery 앱 설정 import
from tasks.celery_config import celery_app

# 모든 태스크 모듈 자동 탐지 설정
celery_app.conf.update(
    include=["tasks"]
)

# 태스크 함수 자동 등록
from tasks import *

# 주요 태스크 함수 명시적 import (하위 호환성)
from tasks.podcast_tasks import process_podcast_task
from tasks.tts_tasks import generate_tts_audio
from tasks.hls_tasks import generate_hls_from_wav


def list_registered_tasks():
    """등록된 Celery 태스크 목록 출력 (디버깅용)"""
    print("🎯 등록된 Celery 태스크 목록:")
    for task_name in sorted(celery_app.tasks.keys()):
        if not task_name.startswith('celery.'):  # 내장 태스크 제외
            print(f"   - {task_name}")


if __name__ == "__main__":
    # 실행 명령: celery -A celery_app worker --loglevel=info
    list_registered_tasks()
    print("\n🚀 Celery Worker 시작 준비 완료!")
    print("실행 명령: celery -A celery_app worker --loglevel=info") 