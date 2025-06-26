#!/bin/bash

# LGraph Multi-Agent System 실행 스크립트

echo "🚀 LGraph Multi-Agent System 시작 중..."

# 환경 변수 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다. env.example을 참고하여 .env 파일을 생성하세요."
    cp env.example .env
    echo "📝 .env 파일이 생성되었습니다. 필요한 환경 변수를 설정하세요."
    exit 1
fi

# 의존성 설치
echo "📦 의존성 설치 중..."
poetry install

# 데이터베이스 마이그레이션 (Alembic 사용)
echo "🗃️  데이터베이스 마이그레이션 중..."
if [ -d "alembic" ]; then
    echo "   Alembic 마이그레이션 적용 중..."
    poetry run alembic upgrade head
else
    echo "   기본 테이블 생성 중..."
    poetry run python database.py
    echo "   💡 프로덕션 환경에서는 'poetry run python migrate.py setup'을 사용하세요."
fi

# 터미널 세션 여러 개로 실행
echo "🌟 서비스들을 시작합니다..."
echo "   - FastAPI 서버: http://localhost:8000"
echo "   - API 문서: http://localhost:8000/docs"
echo "   - Celery Flower: http://localhost:5555"

# 백그라운드에서 Celery Worker 시작
echo "🔧 Celery Worker 시작 중..."
poetry run celery -A celery_app worker --loglevel=info &
CELERY_PID=$!

# 백그라운드에서 Celery Flower 시작
echo "🌸 Celery Flower 시작 중..."
poetry run celery -A celery_app flower --port=5555 &
FLOWER_PID=$!

# FastAPI 서버 시작 (포그라운드)
echo "🌐 FastAPI 서버 시작 중..."
poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# 종료 시그널 처리
cleanup() {
    echo "🛑 서비스들을 종료하는 중..."
    kill $CELERY_PID 2>/dev/null
    kill $FLOWER_PID 2>/dev/null
    kill $API_PID 2>/dev/null
    echo "✅ 모든 서비스가 종료되었습니다."
    exit 0
}

# CTRL+C 처리
trap cleanup SIGINT SIGTERM

echo "✅ 모든 서비스가 시작되었습니다!"
echo "   종료하려면 Ctrl+C를 누르세요."

# 대기
wait 