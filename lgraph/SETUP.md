# LGraph Multi-Agent System - FastAPI 설치 및 실행 가이드

## 🏗️ 시스템 아키텍처

이 시스템은 다음과 같은 구조로 구성되어 있습니다:

- **FastAPI**: API 서버 (비동기 처리)
- **Celery**: 백그라운드 작업 처리 
- **Redis**: Celery 브로커 및 캐시
- **PostgreSQL**: 데이터 저장소
- **LangGraph**: 멀티에이전트 오케스트레이션
- **Super Agent**: Research + Story Narrative + TTS 에이전트 관리

## 📋 사전 요구사항

### 1. 시스템 요구사항
- Python 3.13+
- Poetry (Python 패키지 관리)
- PostgreSQL 15+
- Redis 7+

### 2. API 키 준비
- **OpenAI API Key**: GPT 모델 사용
- **Tavily API Key**: 웹 검색 기능

## 🚀 빠른 시작 (로컬 개발)

### 1. 환경 설정

```bash
# 1. 환경 변수 파일 생성
cp env.example .env

# 2. .env 파일 편집 (필수 API 키 설정)
# OPENAI_API_KEY=your_openai_api_key_here
# TAVILY_API_KEY=your_tavily_api_key_here
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/lgraph
```

### 2. 의존성 설치

```bash
# Poetry로 의존성 설치
poetry install
```

### 3. 데이터베이스 설정

```bash
# PostgreSQL 설치 (macOS)
brew install postgresql
brew services start postgresql

# 데이터베이스 및 사용자 생성
createdb lgraph
createuser -s lgraph_user

# 개발 환경: 테이블 생성
poetry run python database.py

# 프로덕션 환경: Alembic 마이그레이션 사용
poetry run python migrate.py setup
```

### 4. Redis 설치 및 실행

```bash
# Redis 설치 (macOS)
brew install redis
brew services start redis
```

### 5. 시스템 실행

```bash
# 모든 서비스 한번에 실행
./run.sh
```

또는 각각 개별 실행:

```bash
# 터미널 1: Celery Worker
poetry run celery -A celery_app worker --loglevel=info

# 터미널 2: Celery Flower (모니터링)
poetry run celery -A celery_app flower --port=5555

# 터미널 3: FastAPI 서버
poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🐳 Docker 실행 (권장)

```bash
# 모든 서비스 한번에 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 종료
docker-compose down
```

## 📡 API 사용법

### 1. 서비스 접속 주소
- **API 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs (Swagger UI)
- **Celery 모니터링**: http://localhost:5555

### 2. 주요 API 엔드포인트

#### 팟캐스트 생성 작업 시작
```bash
curl -X POST "http://localhost:8000/podcast/create" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "아이폰과 갤럭시의 기술적 비교"
  }'
```

#### 작업 상태 확인
```bash
curl "http://localhost:8000/podcast/tasks/1/status"
```

#### 작업 상세 결과 조회
```bash
curl "http://localhost:8000/podcast/tasks/1"
```

#### 에이전트별 실행 결과 조회
```bash
curl "http://localhost:8000/podcast/tasks/1/agents"
```

### 3. 작업 흐름

1. **POST /podcast/create**: 새 팟캐스트 작업 생성
2. **작업 상태**: `pending` → `processing` → `completed` (또는 `failed`)
3. **GET /podcast/tasks/{id}**: 실행 중이거나 완료된 작업 조회
4. **각 에이전트 결과**: Research → Story Narrative → TTS 순서로 실행

## 🔧 개발 및 디버깅

### 1. 로그 확인
```bash
# Celery Worker 로그
poetry run celery -A celery_app worker --loglevel=debug

# FastAPI 서버 로그
poetry run uvicorn main:app --log-level debug --reload
```

### 2. 데이터베이스 직접 접속
```bash
# PostgreSQL 접속
psql -U lgraph_user -d lgraph -h localhost

# 테이블 확인
\dt
SELECT * FROM podcast_tasks;
SELECT * FROM agent_results;
```

### 3. Redis 상태 확인
```bash
# Redis 클라이언트 접속
redis-cli

# 큐 상태 확인
KEYS *
LLEN celery
```

## 📊 모니터링

### 1. Celery Flower
- 주소: http://localhost:5555
- 작업 큐, 워커 상태, 실행 중인 작업 모니터링

### 2. 시스템 통계 API
```bash
curl "http://localhost:8000/podcast/stats"
```

### 3. 헬스 체크
```bash
curl "http://localhost:8000/health"
```

## 🔒 보안 고려사항

### 프로덕션 환경
1. `.env` 파일 보안 관리
2. CORS 설정 (`allow_origins` 제한)
3. API 키 관리 (환경 변수 또는 Secret Manager)
4. 데이터베이스 접속 보안
5. Redis 인증 설정

## 🗃️ 데이터베이스 마이그레이션

### 개발 환경
```bash
# 단순 테이블 생성 (데이터 손실 가능)
poetry run python database.py
```

### 프로덕션 환경
```bash
# 1. Alembic 설정 및 초기 마이그레이션
poetry run python migrate.py setup

# 2. 스키마 변경 시 마이그레이션 생성
poetry run python migrate.py create -m "Add new field"

# 3. 마이그레이션 적용
poetry run python migrate.py apply
```

## 🐛 문제 해결

### 1. 일반적인 오류

#### "Connection refused" 오류
- PostgreSQL, Redis 서비스 실행 상태 확인
- 포트 충돌 확인 (5432, 6379, 8000)

#### "Module not found" 오류
- Poetry 가상환경 활성화: `poetry shell`
- 의존성 재설치: `poetry install`

#### Celery 작업이 처리되지 않음
- Redis 연결 확인
- Celery Worker 실행 상태 확인
- 작업 큐 상태 확인: `celery -A celery_app inspect active`

### 2. 로그 위치
- Celery: 콘솔 출력
- FastAPI: 콘솔 출력
- 에이전트 실행 로그: 데이터베이스 `agent_results` 테이블

## 📝 추가 기능 개발

### 1. 새로운 에이전트 추가
1. `new_agent.py` 생성
2. `super_agent.py`에 에이전트 등록
3. `celery_app.py`의 `_get_agent_type()` 함수 업데이트

### 2. API 엔드포인트 확장
- `main.py`에 새로운 라우터 추가
- `schemas.py`에 새로운 스키마 정의

### 3. 데이터베이스 스키마 변경
- `database.py` 모델 수정
- Alembic 마이그레이션 실행

## 🎯 성능 최적화

### 1. Celery 워커 확장
```bash
# 워커 수 증가
celery -A celery_app worker --concurrency=4

# 여러 워커 실행
celery multi start worker1 worker2 -A celery_app
```

### 2. 데이터베이스 최적화
- 인덱스 추가
- 커넥션 풀 설정
- 쿼리 최적화

### 3. Redis 설정
- 메모리 최적화
- 지속성 설정
- 클러스터링 (대용량 처리시)

---

**💡 도움이 필요하신가요?**
- 문제 발생시 GitHub Issues 또는 개발팀에 문의
- 상세한 로그와 함께 문의하시면 빠른 해결 가능합니다. 