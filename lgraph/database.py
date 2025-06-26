from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum, ForeignKey
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


class TaskStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(enum.Enum):
    RESEARCH = "research"
    STORY_NARRATIVE = "story_narrative"
    TTS = "tts"
    SUPERVISOR = "supervisor"


class TTSStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HLSStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PodcastTask(Base):
    """팟캐스트 생성 작업 전체를 관리하는 테이블"""
    __tablename__ = "podcast_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_request = Column(Text, nullable=False)  # 사용자 요청 내용
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    final_result = Column(JSON, nullable=True)  # 최종 결과 JSON
    
    # 관계 설정
    agent_results = relationship("AgentResult", back_populates="task")
    tts_results = relationship("TTSResult", back_populates="task")


class AgentResult(Base):
    """각 에이전트의 실행 결과를 저장하는 테이블"""
    __tablename__ = "agent_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("podcast_tasks.id"), nullable=False)
    agent_type = Column(SQLEnum(AgentType), nullable=False)
    agent_name = Column(String(100), nullable=False)
    execution_order = Column(Integer, default=1)  # 같은 에이전트의 실행 순서
    input_data = Column(JSON, nullable=True)  # 에이전트 입력 데이터
    output_data = Column(JSON, nullable=True)  # 에이전트 출력 데이터
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time = Column(Integer, nullable=True)  # 실행 시간 (초)
    error_message = Column(Text, nullable=True)
    
    # 관계 설정
    task = relationship("PodcastTask", back_populates="agent_results")


class TTSResult(Base):
    """TTS 에이전트의 최종 결과를 저장하는 테이블"""
    __tablename__ = "tts_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("podcast_tasks.id"), nullable=False)
    user_request = Column(Text, nullable=False)  # 원본 사용자 요청
    script_content = Column(Text, nullable=False)  # 정제된 TTS 스크립트 (백슬래시 제거)
    raw_script = Column(Text, nullable=True)  # 원본 스크립트 (백업용)
    audio_file_path = Column(String(500), nullable=True)  # 음원 파일 경로
    audio_file_name = Column(String(255), nullable=True)  # 음원 파일명
    audio_file_size = Column(Integer, nullable=True)  # 음원 파일 크기 (bytes)
    audio_duration = Column(Integer, nullable=True)  # 음원 길이 (초)
    is_audio_generated = Column(String(10), default="false")  # 음원 생성 여부 ("true"/"false")
    tts_status = Column(SQLEnum(TTSStatus), default=TTSStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    audio_generated_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # HLS 관련 필드
    hls_folder_name = Column(String(255), nullable=True)  # HLS 파일들이 저장된 폴더명
    hls_master_playlist = Column(String(500), nullable=True)  # Master playlist 경로
    hls_bitrates = Column(JSON, nullable=True)  # 사용 가능한 비트레이트 리스트
    hls_total_segments = Column(Integer, nullable=True)  # 총 세그먼트 수
    is_hls_generated = Column(String(10), default="false")  # HLS 생성 여부 ("true"/"false")
    hls_status = Column(SQLEnum(HLSStatus), default=HLSStatus.PENDING)
    hls_generated_at = Column(DateTime(timezone=True), nullable=True)
    hls_error_message = Column(Text, nullable=True)
    
    # 관계 설정
    task = relationship("PodcastTask", back_populates="tts_results")


def get_db():
    """데이터베이스 세션을 생성하는 제너레이터"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """테이블을 생성합니다."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!") 