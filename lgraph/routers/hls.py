from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from services import tts_service, hls_service

router = APIRouter(
    prefix="/podcast/hls",
    tags=["HLS Streaming"]
)

@router.get("/{tts_id}/master.m3u8")
async def get_hls_master_playlist_endpoint(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """HLS Master Playlist를 스트리밍합니다."""
    tts_result = tts_service.get_tts_result_by_id(db, tts_id)
    if not tts_result or tts_result.is_hls_generated != "true":
        raise HTTPException(status_code=404, detail="HLS master playlist not found or not generated yet")
    
    stream = hls_service.get_hls_stream_response(tts_result.hls_master_playlist)
    return StreamingResponse(
        stream,
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "public, max-age=300", "Access-Control-Allow-Origin": "*"}
    )

@router.get("/{tts_id}/{bitrate}k/playlist.m3u8")
async def get_hls_bitrate_playlist_endpoint(
    tts_id: int,
    bitrate: int,
    db: Session = Depends(get_db)
):
    """특정 비트레이트의 HLS Playlist를 스트리밍합니다."""
    tts_result = tts_service.get_tts_result_by_id(db, tts_id)
    if not tts_result or tts_result.is_hls_generated != "true" or bitrate not in tts_result.hls_bitrates:
        raise HTTPException(status_code=404, detail=f"HLS playlist for bitrate {bitrate}k not found")
        
    playlist_object_name = f"{tts_result.hls_folder_name}/{bitrate}k/playlist.m3u8"
    stream = hls_service.get_hls_stream_response(playlist_object_name)
    return StreamingResponse(
        stream,
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "public, max-age=300", "Access-Control-Allow-Origin": "*"}
    )

@router.get("/{tts_id}/{bitrate}k/{segment_name}")
async def get_hls_segment_endpoint(
    tts_id: int,
    bitrate: int,
    segment_name: str,
    db: Session = Depends(get_db)
):
    """HLS 미디어 세그먼트를 스트리밍합니다."""
    if not segment_name.endswith('.ts'):
        raise HTTPException(status_code=400, detail="Invalid segment file format")

    tts_result = tts_service.get_tts_result_by_id(db, tts_id)
    if not tts_result or tts_result.is_hls_generated != "true":
        raise HTTPException(status_code=404, detail="HLS segment not found or not generated yet")

    segment_object_name = f"{tts_result.hls_folder_name}/{bitrate}k/{segment_name}"
    stream = hls_service.get_hls_stream_response(segment_object_name)
    return StreamingResponse(
        stream,
        media_type="video/mp2t",
        headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"}
    )

@router.get("/{tts_id}/info")
async def get_hls_info_endpoint(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """HLS 스트리밍 정보를 반환합니다."""
    tts_result = tts_service.get_tts_result_by_id(db, tts_id)
    if not tts_result or tts_result.is_hls_generated != "true":
        raise HTTPException(status_code=404, detail="HLS info not found or not generated yet")
    
    return hls_service.get_hls_info(tts_result)

@router.get("/list")
async def list_available_hls_endpoint(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """사용 가능한 HLS 스트리밍 목록을 반환합니다."""
    return hls_service.list_available_hls(db, skip, limit) 