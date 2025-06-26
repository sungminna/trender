from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas import TTSResultResponse
from services import tts_service

router = APIRouter(
    prefix="/podcast/tts",
    tags=["TTS"]
)

@router.get("/", response_model=List[TTSResultResponse])
async def list_tts_results_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """모든 TTS 결과 목록을 반환합니다."""
    return tts_service.get_tts_results(db, skip, limit)

@router.get("/{tts_id}/script")
async def get_tts_script_content_endpoint(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """TTS 스크립트 내용을 텍스트로 반환합니다."""
    tts_result = tts_service.get_tts_result_by_id(db, tts_id)
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

@router.post("/{tts_id}/generate-hls")
async def generate_hls_endpoint(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """TTS 결과로부터 HLS 스트리밍 생성을 시작합니다."""
    tts_result = tts_service.get_tts_result_by_id(db, tts_id)
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    return tts_service.start_hls_generation(tts_result)

@router.get("/{tts_id}/status")
async def get_tts_status_endpoint(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """TTS 및 HLS 생성 상태를 확인합니다."""
    tts_result = tts_service.get_tts_result_by_id(db, tts_id)
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    return {
        "tts_id": tts_id,
        "is_audio_generated": tts_result.is_audio_generated,
        "tts_status": tts_result.tts_status.value,
        "audio_file_name": tts_result.audio_file_name,
        "audio_file_size": tts_result.audio_file_size,
        "audio_duration": tts_result.audio_duration,
        "audio_generated_at": tts_result.audio_generated_at.isoformat() if tts_result.audio_generated_at else None,
        "tts_error_message": tts_result.error_message,
        
        "is_hls_generated": tts_result.is_hls_generated,
        "hls_status": tts_result.hls_status.value,
        "hls_folder_name": tts_result.hls_folder_name,
        "hls_master_playlist": tts_result.hls_master_playlist,
        "hls_bitrates": tts_result.hls_bitrates,
        "hls_total_segments": tts_result.hls_total_segments,
        "hls_generated_at": tts_result.hls_generated_at.isoformat() if tts_result.hls_generated_at else None,
        "hls_error_message": tts_result.hls_error_message
    }

@router.get("/voices")
async def get_available_voices_endpoint():
    """사용 가능한 TTS 음성 목록을 반환합니다."""
    return tts_service.get_available_tts_voices() 