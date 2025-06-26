"""
TTS 및 HLS 생성 관련 비즈니스 로직을 처리하는 서비스 모듈
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from database import TTSResult
from tasks.hls_tasks import generate_hls_from_wav
from tasks.tts_tasks import generate_tts_audio
from tts import get_tts_generator

def get_tts_results(db: Session, skip: int = 0, limit: int = 100) -> List[TTSResult]:
    """모든 TTS 결과 목록을 조회합니다."""
    return db.query(TTSResult).offset(skip).limit(limit).all()

def get_tts_result_by_id(db: Session, tts_id: int) -> Optional[TTSResult]:
    """ID로 특정 TTS 결과를 조회합니다."""
    return db.query(TTSResult).filter(TTSResult.id == tts_id).first()

def start_hls_generation(tts_result: TTSResult) -> Dict[str, Any]:
    """TTS 결과로부터 HLS 생성을 시작(또는 오디오 생성부터 시작)합니다."""
    if tts_result.is_hls_generated == "true":
        return {
            "message": "HLS already generated",
            "tts_id": tts_result.id,
            "hls_folder_name": tts_result.hls_folder_name,
        }

    if tts_result.is_audio_generated == "true":
        # WAV 파일이 이미 있으면 HLS 변환만 수행
        celery_task = generate_hls_from_wav.delay(tts_result.id)
        message = "HLS conversion started"
    else:
        # WAV 파일부터 생성 (완료 후 자동으로 HLS 변환)
        celery_task = generate_tts_audio.delay(tts_result.id)
        message = "Audio generation started (HLS conversion will follow automatically)"
    
    return {
        "message": message,
        "tts_id": tts_result.id,
        "celery_task_id": celery_task.id,
        "status": "processing"
    }

def get_available_tts_voices() -> Dict[str, Any]:
    """사용 가능한 TTS 음성 목록을 조회합니다."""
    try:
        tts_generator = get_tts_generator()
        voices = tts_generator.get_available_voices()
        return {
            "total_voices": len(voices),
            "voices": voices,
            "recommended_for_korean": ["Kore", "Leda", "Iapetus", "Alnilam"]
        }
    except Exception as e:
        # 외부 서비스 조회 실패 시 기본값 또는 에러 정보 반환
        return {
            "error": "Failed to get voices from external service",
            "detail": str(e),
            "default_voices": ["Kore", "Leda", "Iapetus", "Alnilam"]
        } 