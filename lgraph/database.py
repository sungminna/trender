from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import os
from config import settings

# Database URL from environment
DATABASE_URL = settings.DATABASE_URL.replace("asyncpg", "psycopg2")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class UserRole(enum.Enum):
    """사용자 역할"""
    USER = "user"
    ADMIN = "admin"


class TaskStatus(enum.Enum):
    """팟캐스트 생성 작업 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(enum.Enum):
    """멀티 에이전트 시스템의 에이전트 유형"""
    RESEARCH = "research"
    STORY_NARRATIVE = "story_narrative"
    TTS = "tts"
    SUPERVISOR = "supervisor"


class TTSStatus(enum.Enum):
    """TTS 음성 생성 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HLSStatus(enum.Enum):
    """HLS 스트리밍 변환 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """
    사용자 정보 테이블
    - JWT 토큰 기반 인증
    - 사용자별 팟캐스트 작업 관리
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # 관계: 사용자의 팟캐스트 작업들
    podcast_tasks = relationship("PodcastTask", back_populates="user")


class PodcastTask(Base):
    """
    팟캐스트 생성 작업 마스터 테이블
    - 사용자 요청부터 최종 완료까지 전체 작업 추적
    - 멀티 에이전트 파이프라인의 시작점
    """
    __tablename__ = "podcast_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 사용자 외래키 추가
    user_request = Column(Text, nullable=False)  # 사용자 원본 요청
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    final_result = Column(JSON, nullable=True)  # 전체 파이프라인 결과
    
    # 관계: 사용자
    user = relationship("User", back_populates="podcast_tasks")
    # 관계: 하위 에이전트 실행 결과들
    agent_results = relationship("AgentResult", back_populates="task")
    tts_results = relationship("TTSResult", back_populates="task")


class AgentResult(Base):
    """
    개별 에이전트 실행 결과 저장
    - Research, Story Narrative, TTS 각 에이전트의 실행 기록
    - 멀티 에이전트 파이프라인의 중간 결과 추적
    """
    __tablename__ = "agent_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("podcast_tasks.id"), nullable=False)
    agent_type = Column(SQLEnum(AgentType), nullable=False)
    agent_name = Column(String(100), nullable=False)
    execution_order = Column(Integer, default=1)  # 동일 에이전트의 실행 순서
    input_data = Column(JSON, nullable=True)  # 에이전트 입력 데이터
    output_data = Column(JSON, nullable=True)  # 에이전트 출력 데이터
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time = Column(Integer, nullable=True)  # 실행 시간(초)
    error_message = Column(Text, nullable=True)
    
    # 관계: 상위 작업
    task = relationship("PodcastTask", back_populates="agent_results")


class TTSResult(Base):
    """
    TTS 및 HLS 생성 결과 통합 관리
    - TTS 스크립트 저장 및 음성 생성 결과
    - HLS 스트리밍 변환 결과
    - MinIO 오브젝트 스토리지 연동 정보
    """
    __tablename__ = "tts_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("podcast_tasks.id"), nullable=False)
    user_request = Column(Text, nullable=False)  # 원본 사용자 요청
    script_content = Column(Text, nullable=False)  # 정제된 TTS 스크립트
    raw_script = Column(Text, nullable=True)  # 원본 스크립트 백업
    
    # TTS 음성 파일 정보
    audio_file_path = Column(String(500), nullable=True)  # MinIO 저장 경로
    audio_file_name = Column(String(255), nullable=True)  # 파일명
    audio_file_size = Column(Integer, nullable=True)  # 파일 크기(bytes)
    audio_duration = Column(Integer, nullable=True)  # 음성 길이(초)
    is_audio_generated = Column(String(10), default="false")  # 음성 생성 완료 여부
    tts_status = Column(SQLEnum(TTSStatus), default=TTSStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    audio_generated_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # HLS 스트리밍 변환 정보
    hls_folder_name = Column(String(255), nullable=True)  # HLS 세그먼트 폴더명
    hls_master_playlist = Column(String(500), nullable=True)  # master.m3u8 경로
    hls_bitrates = Column(JSON, nullable=True)  # 지원 비트레이트 목록
    hls_total_segments = Column(Integer, nullable=True)  # 총 세그먼트 수
    is_hls_generated = Column(String(10), default="false")  # HLS 생성 완료 여부
    hls_status = Column(SQLEnum(HLSStatus), default=HLSStatus.PENDING)
    hls_generated_at = Column(DateTime(timezone=True), nullable=True)
    hls_error_message = Column(Text, nullable=True)
    
    # 관계: 상위 작업
    task = relationship("PodcastTask", back_populates="tts_results")


def get_db():
    """데이터베이스 세션 의존성 주입용 제너레이터"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """모든 데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!") 