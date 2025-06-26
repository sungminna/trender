"""
LGraph Celery Application Entry Point

이 파일은 Celery 앱의 엔트리 포인트 역할을 합니다.
모든 태스크는 tasks/ 디렉토리에 기능별로 분리되어 있습니다.

구조:
- tasks/podcast_tasks.py: 팟캐스트 생성 관련 태스크
- tasks/tts_tasks.py: TTS 음원 생성 관련 태스크  
- tasks/hls_tasks.py: HLS 변환 관련 태스크
- tasks/utils.py: 공통 유틸리티 함수들
"""

# 공통 Celery 앱 설정 import
from tasks.celery_config import celery_app

# tasks 모듈 포함 설정
celery_app.conf.update(
    include=["tasks"]  # tasks 모듈의 모든 태스크 포함
)

# 모든 태스크 import (자동 등록)
from tasks import *

# 태스크 함수들을 직접 import하여 하위 호환성 유지
from tasks.podcast_tasks import process_podcast_task
from tasks.tts_tasks import generate_tts_audio
from tasks.hls_tasks import generate_hls_from_wav

# 디버깅용 태스크 목록 출력
def list_registered_tasks():
    """등록된 모든 태스크 목록을 출력합니다."""
    print("🎯 등록된 Celery 태스크 목록:")
    for task_name in sorted(celery_app.tasks.keys()):
        if not task_name.startswith('celery.'):  # 내장 태스크 제외
            print(f"   - {task_name}")

if __name__ == "__main__":
    # Celery worker 실행: celery -A celery_app worker --loglevel=info
    list_registered_tasks()
    print("\n🚀 Celery Worker 시작 준비 완료!")
    print("실행 명령: celery -A celery_app worker --loglevel=info") 