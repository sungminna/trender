FROM python:3.13-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (FFmpeg 포함)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install poetry

# Poetry 설정 (가상환경을 만들지 않도록)
RUN poetry config virtualenvs.create false

# 의존성 파일 복사
COPY pyproject.toml poetry.lock* ./

# 의존성 설치
RUN poetry install --only=main --no-root

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 기본 실행 명령
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 