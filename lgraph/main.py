from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import io

from database import get_db, create_tables, PodcastTask, AgentResult, TaskStatus, TTSResult
from schemas import (
    PodcastRequestCreate, 
    PodcastTaskResponse, 
    PodcastTaskSummary,
    TaskStatusUpdate,
    TTSResultResponse
)
from celery_app import celery_app
from tasks.podcast_tasks import process_podcast_task
from tasks.tts_tasks import generate_tts_audio
from tasks.hls_tasks import generate_hls_from_wav
from tts import get_tts_generator
from utils.minio_client import get_minio_client
from utils.hls_converter import get_hls_converter

# FastAPI 앱 생성
app = FastAPI(
    title="LGraph Multi-Agent Podcast System",
    description="Korean Podcast Production System using Multi-Agent Architecture",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """앱 시작시 데이터베이스 테이블 생성"""
    create_tables()
    print("🚀 LGraph Multi-Agent System API started!")


@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "LGraph Multi-Agent Podcast System API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "celery_status": "active" if celery_app.control.inspect().active() else "inactive"
    }


@app.post("/podcast/create", response_model=PodcastTaskResponse)
async def create_podcast_task(
    request: PodcastRequestCreate,
    db: Session = Depends(get_db)
):
    """
    새로운 팟캐스트 생성 작업을 시작합니다.
    작업은 백그라운드에서 비동기로 처리됩니다.
    """
    # 데이터베이스에 작업 생성
    db_task = PodcastTask(
        user_request=request.user_request,
        status=TaskStatus.PENDING,
        created_at=datetime.utcnow()
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Celery 백그라운드 작업 시작
    celery_task = process_podcast_task.delay(db_task.id, request.user_request)
    
    print(f"🎯 새로운 팟캐스트 작업 생성됨 - Task ID: {db_task.id}, Celery Task ID: {celery_task.id}")
    
    return db_task


@app.get("/podcast/tasks", response_model=List[PodcastTaskSummary])
async def list_podcast_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """모든 팟캐스트 작업 목록을 반환합니다."""
    tasks = db.query(PodcastTask).offset(skip).limit(limit).all()
    return tasks


@app.get("/podcast/tasks/{task_id}", response_model=PodcastTaskResponse)
async def get_podcast_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 팟캐스트 작업의 상세 정보를 반환합니다."""
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@app.get("/podcast/tasks/{task_id}/status")
async def get_task_status(
    task_id: int,
    db: Session = Depends(get_db)
):
    """작업의 현재 상태를 반환합니다."""
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task_id,
        "status": task.status,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message
    }


@app.get("/podcast/tasks/{task_id}/agents")
async def get_task_agent_results(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 작업의 모든 에이전트 실행 결과를 반환합니다."""
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    agents = db.query(AgentResult).filter(AgentResult.task_id == task_id).all()
    return {
        "task_id": task_id,
        "total_agents": len(agents),
        "agents": agents
    }


@app.get("/podcast/tasks/{task_id}/tts", response_model=TTSResultResponse)
async def get_task_tts_result(
    task_id: int,
    db: Session = Depends(get_db)
):
    """특정 작업의 TTS 결과를 반환합니다."""
    # 작업 존재 확인
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # TTS 결과 조회
    tts_result = db.query(TTSResult).filter(TTSResult.task_id == task_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found for this task")
    
    return tts_result


@app.get("/podcast/tts", response_model=List[TTSResultResponse])
async def list_tts_results(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """모든 TTS 결과 목록을 반환합니다."""
    tts_results = db.query(TTSResult).offset(skip).limit(limit).all()
    return tts_results


@app.get("/podcast/tts/{tts_id}/script")
async def get_tts_script_content(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """TTS 스크립트 내용을 텍스트로 반환합니다."""
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
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


@app.delete("/podcast/tasks/{task_id}")
async def delete_podcast_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """팟캐스트 작업을 삭제합니다."""
    task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 관련 TTS 결과와 에이전트 결과도 함께 삭제
    db.query(TTSResult).filter(TTSResult.task_id == task_id).delete()
    db.query(AgentResult).filter(AgentResult.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    
    return {"message": f"Task {task_id} deleted successfully"}


@app.post("/podcast/tts/{tts_id}/generate-hls")
async def generate_hls_endpoint(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """TTS 결과로부터 HLS 스트리밍을 생성합니다."""
    # TTS 결과 존재 확인
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    # 이미 HLS가 생성되었는지 확인
    if tts_result.is_hls_generated == "true":
        return {
            "message": "HLS already generated",
            "tts_id": tts_id,
            "hls_folder_name": tts_result.hls_folder_name,
            "master_playlist": tts_result.hls_master_playlist,
            "bitrates": tts_result.hls_bitrates,
            "total_segments": tts_result.hls_total_segments
        }
    
    # 비동기 HLS 변환 작업 시작
    if tts_result.is_audio_generated == "true":
        # WAV 파일이 이미 있으면 HLS 변환만 수행
        celery_task = generate_hls_from_wav.delay(tts_id)
        message = "HLS conversion started"
    else:
        # WAV 파일부터 생성 (완료 후 자동으로 HLS 변환)
        celery_task = generate_tts_audio.delay(tts_id)
        message = "Audio generation started (HLS conversion will follow automatically)"
    
    return {
        "message": message,
        "tts_id": tts_id,
        "celery_task_id": celery_task.id,
        "status": "processing"
    }


@app.get("/podcast/tts/{tts_id}/status")
async def get_tts_status(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """TTS 및 HLS 생성 상태를 확인합니다."""
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    return {
        "tts_id": tts_id,
        # TTS 상태
        "is_audio_generated": tts_result.is_audio_generated,
        "tts_status": tts_result.tts_status.value,
        "audio_file_name": tts_result.audio_file_name,
        "audio_file_size": tts_result.audio_file_size,
        "audio_duration": tts_result.audio_duration,
        "audio_generated_at": tts_result.audio_generated_at.isoformat() if tts_result.audio_generated_at else None,
        "tts_error_message": tts_result.error_message,
        
        # HLS 상태
        "is_hls_generated": tts_result.is_hls_generated,
        "hls_status": tts_result.hls_status.value,
        "hls_folder_name": tts_result.hls_folder_name,
        "hls_master_playlist": tts_result.hls_master_playlist,
        "hls_bitrates": tts_result.hls_bitrates,
        "hls_total_segments": tts_result.hls_total_segments,
        "hls_generated_at": tts_result.hls_generated_at.isoformat() if tts_result.hls_generated_at else None,
        "hls_error_message": tts_result.hls_error_message
    }


@app.get("/podcast/tts/voices")
async def get_available_voices():
    """사용 가능한 TTS 음성 목록을 반환합니다."""
    try:
        tts_generator = get_tts_generator()
        voices = tts_generator.get_available_voices()
        return {
            "total_voices": len(voices),
            "voices": voices,
            "recommended_for_korean": ["Kore", "Leda", "Iapetus", "Alnilam"]
        }
    except Exception as e:
        return {
            "error": "Failed to get voices",
            "detail": str(e),
            "default_voices": ["Kore", "Leda", "Iapetus", "Alnilam"]
        }



@app.get("/podcast/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """시스템 통계를 반환합니다."""
    total_tasks = db.query(PodcastTask).count()
    pending_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.PENDING).count()
    processing_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.PROCESSING).count()
    completed_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.COMPLETED).count()
    failed_tasks = db.query(PodcastTask).filter(PodcastTask.status == TaskStatus.FAILED).count()
    
    total_agents = db.query(AgentResult).count()
    
    # TTS 관련 통계
    total_tts_results = db.query(TTSResult).count()
    audio_generated_count = db.query(TTSResult).filter(TTSResult.is_audio_generated == "true").count()
    audio_pending_count = total_tts_results - audio_generated_count
    
    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "processing_tasks": processing_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "total_agent_executions": total_agents,
        "total_tts_results": total_tts_results,
        "audio_generated_count": audio_generated_count,
        "audio_pending_count": audio_pending_count,
        "celery_active_tasks": len(celery_app.control.inspect().active() or {})
    }


# ==========================================
# 🎬 HLS 스트리밍 API 엔드포인트
# ==========================================

@app.get("/podcast/hls/{tts_id}/master.m3u8")
async def get_hls_master_playlist(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """
    HLS Master Playlist를 반환합니다.
    클라이언트가 적응형 스트리밍을 시작할 수 있습니다.
    """
    # TTS 결과 확인
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    if tts_result.is_hls_generated != "true":
        raise HTTPException(status_code=404, detail="HLS not yet generated")
    
    try:
        # MinIO에서 Master Playlist 가져오기
        minio_client = get_minio_client()
        playlist_stream = minio_client.get_object_stream(tts_result.hls_master_playlist)
        
        # 스트리밍 응답 생성
        def iterfile():
            try:
                while True:
                    chunk = playlist_stream.read(8192)
                    if not chunk:
                        break
                    yield chunk
            finally:
                playlist_stream.close()
        
        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.apple.mpegurl",
            headers={
                "Cache-Control": "public, max-age=300",  # 5분 캐시
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        print(f"❌ HLS Master Playlist 제공 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="HLS master playlist failed")


@app.get("/podcast/hls/{tts_id}/{bitrate}k/playlist.m3u8")
async def get_hls_bitrate_playlist(
    tts_id: int,
    bitrate: int,
    db: Session = Depends(get_db)
):
    """
    특정 비트레이트의 HLS Playlist를 반환합니다.
    """
    # TTS 결과 확인
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    if tts_result.is_hls_generated != "true":
        raise HTTPException(status_code=404, detail="HLS not yet generated")
    
    # 요청된 비트레이트가 사용 가능한지 확인
    if bitrate not in tts_result.hls_bitrates:
        raise HTTPException(status_code=404, detail=f"Bitrate {bitrate}k not available")
    
    try:
        # MinIO에서 비트레이트별 Playlist 가져오기
        playlist_object_name = f"{tts_result.hls_folder_name}/{bitrate}k/playlist.m3u8"
        minio_client = get_minio_client()
        playlist_stream = minio_client.get_object_stream(playlist_object_name)
        
        # 스트리밍 응답 생성
        def iterfile():
            try:
                while True:
                    chunk = playlist_stream.read(8192)
                    if not chunk:
                        break
                    yield chunk
            finally:
                playlist_stream.close()
        
        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.apple.mpegurl",
            headers={
                "Cache-Control": "public, max-age=300",  # 5분 캐시
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        print(f"❌ HLS Bitrate Playlist 제공 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="HLS bitrate playlist failed")


@app.get("/podcast/hls/{tts_id}/{bitrate}k/{segment_name}")
async def get_hls_segment(
    tts_id: int,
    bitrate: int,
    segment_name: str,
    db: Session = Depends(get_db)
):
    """
    HLS 세그먼트 파일을 반환합니다.
    """
    # TTS 결과 확인
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    if tts_result.is_hls_generated != "true":
        raise HTTPException(status_code=404, detail="HLS not yet generated")
    
    # 세그먼트 파일명 검증 (.ts 파일만 허용)
    if not segment_name.endswith('.ts'):
        raise HTTPException(status_code=400, detail="Invalid segment file")
    
    try:
        # MinIO에서 세그먼트 파일 가져오기
        segment_object_name = f"{tts_result.hls_folder_name}/{bitrate}k/{segment_name}"
        minio_client = get_minio_client()
        segment_stream = minio_client.get_object_stream(segment_object_name)
        
        # 스트리밍 응답 생성
        def iterfile():
            try:
                while True:
                    chunk = segment_stream.read(8192)
                    if not chunk:
                        break
                    yield chunk
            finally:
                segment_stream.close()
        
        return StreamingResponse(
            iterfile(),
            media_type="video/mp2t",
            headers={
                "Cache-Control": "public, max-age=3600",  # 1시간 캐시
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        print(f"❌ HLS 세그먼트 제공 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="HLS segment failed")


@app.get("/podcast/hls/{tts_id}/info")
async def get_hls_info(
    tts_id: int,
    db: Session = Depends(get_db)
):
    """
    HLS 스트리밍 정보를 반환합니다.
    """
    # TTS 결과 확인
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    if not tts_result:
        raise HTTPException(status_code=404, detail="TTS result not found")
    
    if tts_result.is_hls_generated != "true":
        raise HTTPException(status_code=404, detail="HLS not yet generated")
    
    return {
        "tts_id": tts_id,
        "hls_status": tts_result.hls_status.value,
        "hls_folder_name": tts_result.hls_folder_name,
        "master_playlist_url": f"/podcast/hls/{tts_id}/master.m3u8",
        "available_bitrates": tts_result.hls_bitrates,
        "total_segments": tts_result.hls_total_segments,
        "duration": tts_result.audio_duration,
        "generated_at": tts_result.hls_generated_at.isoformat() if tts_result.hls_generated_at else None,
        "bitrate_playlists": {
            str(bitrate): f"/podcast/hls/{tts_id}/{bitrate}k/playlist.m3u8" 
            for bitrate in tts_result.hls_bitrates
        }
    }


@app.get("/podcast/hls/list")
async def list_available_hls(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    사용 가능한 HLS 스트리밍 목록을 반환합니다.
    """
    # HLS가 생성된 TTS 결과만 조회
    tts_results = db.query(TTSResult).filter(
        TTSResult.is_hls_generated == "true"
    ).offset(skip).limit(limit).all()
    
    hls_list = []
    for tts_result in tts_results:
        hls_list.append({
            "tts_id": tts_result.id,
            "task_id": tts_result.task_id,
            "user_request": tts_result.user_request,
            "master_playlist_url": f"/podcast/hls/{tts_result.id}/master.m3u8",
            "available_bitrates": tts_result.hls_bitrates,
            "total_segments": tts_result.hls_total_segments,
            "duration": tts_result.audio_duration,
            "generated_at": tts_result.hls_generated_at.isoformat() if tts_result.hls_generated_at else None,
            "info_url": f"/podcast/hls/{tts_result.id}/info"
        })
    
    return {
        "total_count": len(hls_list),
        "hls_streams": hls_list,
        "pagination": {
            "skip": skip,
            "limit": limit,
            "has_more": len(hls_list) == limit
        }
    }


# 예외 처리
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 처리기"""
    print(f"❌ Unexpected error: {str(exc)}")
    return {
        "error": "Internal server error",
        "detail": str(exc) if os.getenv("DEBUG") == "true" else "An unexpected error occurred"
    }


if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 