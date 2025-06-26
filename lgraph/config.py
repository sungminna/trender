from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    애플리케이션 설정을 관리하는 클래스.
    .env 파일 또는 환경 변수에서 값을 로드합니다.
    """
    # .env 파일 우선 로드
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://user:password@localhost/lgraph"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET_NAME: str = "lgraph-audio"
    MINIO_SECURE: bool = False

    # TTS APIs
    GEMINI_API_KEY: str = "your_gemini_api_key_here"
    ELEVEN_API_KEY: str = "your_eleven_api_key_here"

    # System
    DEBUG: bool = False

@lru_cache
def get_settings() -> Settings:
    """캐시된 설정 인스턴스를 반환합니다."""
    return Settings()

settings = get_settings() 