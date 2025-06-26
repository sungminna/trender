from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    LGraph 애플리케이션 설정 관리
    
    Environment Variables:
    - .env 파일 또는 시스템 환경변수에서 값을 로드
    - 환경변수는 클래스 속성명과 동일하게 설정 (예: DATABASE_URL)
    """
    # .env 파일 우선 로드
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # PostgreSQL 데이터베이스 연결
    DATABASE_URL: str = "postgresql+psycopg2://user:password@localhost/lgraph"

    # Redis 기반 Celery 브로커 및 백엔드
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # MinIO 오브젝트 스토리지 (오디오 파일 저장)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET_NAME: str = "lgraph-audio"
    MINIO_SECURE: bool = False

    # TTS 서비스 API 키
    GEMINI_API_KEY: str = "your_gemini_api_key_here"
    ELEVEN_API_KEY: str = "your_eleven_api_key_here"

    # Langfuse 트레이싱 설정
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # System
    DEBUG: bool = False

@lru_cache
def get_settings() -> Settings:
    """설정 인스턴스 캐싱 반환"""
    return Settings()

settings = get_settings() 