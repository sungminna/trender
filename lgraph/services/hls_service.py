"""
HLS 스트리밍 관련 비즈니스 로직을 처리하는 서비스 모듈
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Generator

from database import TTSResult
from utils.minio_client import get_minio_client

def get_hls_stream_response(object_name: str) -> Generator[bytes, None, None]:
    """MinIO에서 HLS 파일 스트림을 가져옵니다."""
    minio_client = get_minio_client()
    try:
        stream = minio_client.get_object_stream(object_name)
        yield from stream
    except Exception as e:
        print(f"❌ MinIO 스트림 가져오기 실패: {e}")
        # 예외를 다시 발생시켜 상위 핸들러(라우터 또는 전역 핸들러)가 처리하도록 함
        raise e

def get_hls_info(tts_result: TTSResult) -> Dict[str, Any]:
    """HLS 스트리밍 상세 정보를 구성합니다."""
    return {
        "tts_id": tts_result.id,
        "hls_status": tts_result.hls_status.value,
        "hls_folder_name": tts_result.hls_folder_name,
        "master_playlist_url": f"/podcast/hls/{tts_result.id}/master.m3u8",
        "available_bitrates": tts_result.hls_bitrates,
        "total_segments": tts_result.hls_total_segments,
        "duration": tts_result.audio_duration,
        "generated_at": tts_result.hls_generated_at.isoformat() if tts_result.hls_generated_at else None,
        "bitrate_playlists": {
            str(bitrate): f"/podcast/hls/{tts_result.id}/{bitrate}k/playlist.m3u8" 
            for bitrate in tts_result.hls_bitrates
        }
    }

def list_available_hls(db: Session, skip: int, limit: int) -> Dict[str, Any]:
    """사용 가능한 모든 HLS 스트리밍 목록을 구성합니다."""
    tts_results = db.query(TTSResult).filter(
        TTSResult.is_hls_generated == "true"
    ).offset(skip).limit(limit).all()
    
    hls_list = [
        {
            "tts_id": r.id,
            "task_id": r.task_id,
            "user_request": r.user_request,
            "master_playlist_url": f"/podcast/hls/{r.id}/master.m3u8",
            "available_bitrates": r.hls_bitrates,
            "duration": r.audio_duration,
            "generated_at": r.hls_generated_at.isoformat() if r.hls_generated_at else None,
            "info_url": f"/podcast/hls/{r.id}/info"
        }
        for r in tts_results
    ]
    
    return {
        "total_count": len(hls_list),
        "hls_streams": hls_list,
        "pagination": {
            "skip": skip,
            "limit": limit,
            "has_more": len(hls_list) == limit
        }
    } 