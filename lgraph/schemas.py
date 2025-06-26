from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from database import TaskStatus, AgentType, TTSStatus, HLSStatus


class PodcastRequestCreate(BaseModel):
    user_request: str = Field(..., min_length=1, max_length=10000, description="팟캐스트 생성 요청 내용")


class AgentResultResponse(BaseModel):
    id: int
    agent_type: AgentType
    agent_name: str
    execution_order: int
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    status: TaskStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class PodcastTaskResponse(BaseModel):
    id: int
    user_request: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    final_result: Optional[Dict[str, Any]] = None
    agent_results: List[AgentResultResponse] = []

    class Config:
        from_attributes = True


class PodcastTaskSummary(BaseModel):
    id: int
    user_request: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    error_message: Optional[str] = None
    final_result: Optional[Dict[str, Any]] = None


class TTSResultResponse(BaseModel):
    id: int
    task_id: int
    user_request: str
    script_content: str
    raw_script: Optional[str] = None
    audio_file_path: Optional[str] = None
    audio_file_name: Optional[str] = None
    audio_file_size: Optional[int] = None
    audio_duration: Optional[int] = None
    is_audio_generated: str = "false"
    tts_status: TTSStatus
    created_at: datetime
    audio_generated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # HLS 관련 필드
    hls_folder_name: Optional[str] = None
    hls_master_playlist: Optional[str] = None
    hls_bitrates: Optional[List[int]] = None
    hls_total_segments: Optional[int] = None
    is_hls_generated: str = "false"
    hls_status: HLSStatus
    hls_generated_at: Optional[datetime] = None
    hls_error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TTSResultCreate(BaseModel):
    script_content: str
    audio_file_path: Optional[str] = None
    audio_file_name: Optional[str] = None
    is_audio_generated: str = "false"


class HLSInfoResponse(BaseModel):
    tts_id: int
    hls_status: str
    hls_folder_name: str
    master_playlist_url: str
    available_bitrates: List[int]
    total_segments: int
    duration: Optional[int] = None
    generated_at: Optional[str] = None
    bitrate_playlists: Dict[str, str]


class HLSListResponse(BaseModel):
    total_count: int
    hls_streams: List[Dict[str, Any]]
    pagination: Dict[str, Any]


class HLSGenerationRequest(BaseModel):
    bitrates: Optional[List[int]] = Field(default=[64, 128, 320], description="생성할 비트레이트 목록 (kbps)")
    segment_duration: Optional[int] = Field(default=10, description="세그먼트 길이 (초)")


class HLSGenerationResponse(BaseModel):
    message: str
    tts_id: int
    celery_task_id: str
    status: str
    hls_folder_name: Optional[str] = None
    master_playlist: Optional[str] = None 