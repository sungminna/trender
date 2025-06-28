from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from database import TaskStatus, AgentType, TTSStatus, HLSStatus, UserRole


# User 관련 스키마
class UserBase(BaseModel):
    """사용자 기본 스키마"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """사용자 생성 스키마"""
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    """사용자 정보 수정 스키마"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserResponse(UserBase):
    """사용자 정보 응답 스키마"""
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """로그인 요청 스키마"""
    username: str  # email 또는 username 허용
    password: str


class Token(BaseModel):
    """JWT 토큰 응답 스키마"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """토큰 데이터 스키마"""
    username: Optional[str] = None
    user_id: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    """리프레시 토큰 요청 스키마"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """비밀번호 변경 요청 스키마"""
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class PodcastRequestCreate(BaseModel):
    """팟캐스트 생성 요청 스키마"""
    user_request: str = Field(..., min_length=1, max_length=10000, description="팟캐스트 생성 요청 내용")


class AgentResultResponse(BaseModel):
    """개별 에이전트 실행 결과 응답 스키마"""
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


class TTSResultResponse(BaseModel):
    """TTS 및 HLS 결과 통합 응답 스키마"""
    id: int
    task_id: int
    user_request: str
    script_content: str
    raw_script: Optional[str] = None
    
    # TTS 관련 필드
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


class PodcastTaskResponse(BaseModel):
    """팟캐스트 작업 상세 정보 응답 스키마"""
    id: int
    user_request: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    final_result: Optional[Dict[str, Any]] = None
    agent_results: List[AgentResultResponse] = []
    tts_results: List[TTSResultResponse] = []

    class Config:
        from_attributes = True


class PodcastTaskSummary(BaseModel):
    """팟캐스트 작업 목록용 요약 스키마"""
    id: int
    user_request: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
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


class PodcastRegenerateRequest(BaseModel):
    """팟캐스트 대본 수정 및 재성성 요청 스키마"""
    script: str = Field(..., min_length=1, description="사용자가 수정한 최종 팟캐스트 대본")


class TaskStatusUpdate(BaseModel):
    """작업 상태 업데이트 스키마"""
    status: TaskStatus
    error_message: Optional[str] = None
    final_result: Optional[Dict[str, Any]] = None


class TTSResultCreate(BaseModel):
    """TTS 결과 생성 스키마"""
    script_content: str
    audio_file_path: Optional[str] = None
    audio_file_name: Optional[str] = None
    is_audio_generated: str = "false"


class HLSInfoResponse(BaseModel):
    """HLS 스트리밍 정보 응답 스키마"""
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
    """HLS 스트림 목록 응답 스키마"""
    total_count: int
    hls_streams: List[Dict[str, Any]]
    pagination: Dict[str, Any]


class HLSGenerationRequest(BaseModel):
    """HLS 생성 요청 스키마"""
    bitrates: Optional[List[int]] = Field(default=[64, 128, 320], description="생성할 비트레이트 목록 (kbps)")
    segment_duration: Optional[int] = Field(default=10, description="세그먼트 길이 (초)")


class HLSGenerationResponse(BaseModel):
    """HLS 생성 응답 스키마"""
    message: str
    tts_id: int
    celery_task_id: str
    status: str
    hls_folder_name: Optional[str] = None
    master_playlist: Optional[str] = None


# WebSocket 관련 스키마
class WebSocketMessage(BaseModel):
    """WebSocket 메시지 기본 스키마"""
    type: str
    timestamp: str


class TaskStatusWebSocketMessage(WebSocketMessage):
    """작업 상태 업데이트 WebSocket 메시지"""
    task_id: int
    status: str
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    final_result: Optional[Dict[str, Any]] = None


class AgentProgressWebSocketMessage(WebSocketMessage):
    """에이전트 진행 상황 WebSocket 메시지"""
    task_id: int
    agent_name: str
    agent_status: str
    execution_order: Optional[int] = None
    execution_time: Optional[int] = None
    output_messages_count: Optional[int] = None
    message: Optional[str] = None


class TTSProgressWebSocketMessage(WebSocketMessage):
    """TTS 진행 상황 WebSocket 메시지"""
    task_id: int
    tts_status: str
    message: Optional[str] = None
    tts_result_id: Optional[int] = None
    script_length: Optional[int] = None
    audio_file_name: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    error: Optional[str] = None


class ConnectionEstablishedWebSocketMessage(WebSocketMessage):
    """연결 성공 WebSocket 메시지"""
    user_id: int
    message: str


class PingPongWebSocketMessage(WebSocketMessage):
    """Ping/Pong WebSocket 메시지"""
    pass


class ErrorWebSocketMessage(WebSocketMessage):
    """에러 WebSocket 메시지"""
    message: str
    error_code: Optional[str] = None

# Pydantic V2 스타일로 Forward-referencing 해결
PodcastTaskResponse.model_rebuild() 