# L-Graph: AI 기반 한국어 팟캐스트 자동 생성 시스템

**L-Graph**는 최신 AI 기술을 활용하여 사용자의 간단한 요청만으로 완전한 형태의 한국어 팟캐스트를 제작하는 시스템입니다. '아이폰과 갤럭시 비교'와 같은 주제만 던져주면, 정보 조사부터 대본 작성, 음성 합성에 이르는 전 과정을 자동화하여 스트리밍 가능한 오디오 콘텐츠를 제공합니다.

[![Video Label](http://img.youtube.com/vi/E5a-3oG-s2U/0.jpg)](https://youtu.be/E5a-3oG-s2U)

## ✨ 주요 특징

- **🤖 멀티 에이전트 오케스트레이션**: `LangGraph` 기반의 슈퍼바이저 에이전트가 **Research → Story Narrative → TTS 최적화** 에이전트들을 유기적으로 지휘하여 높은 품질의 결과물을 생성합니다.
- **⚡️ 100% 비동기 처리**: `FastAPI`와 `Celery`를 통해 모든 요청을 비동기로 처리하여, 무거운 AI 작업 중에도 시스템이 안정적으로 반응하고 높은 동시성을 보장합니다.
- **🎤 고품질 TTS 및 스트리밍**: 최신 TTS 엔진을 활용하여 자연스러운 한국어 음성을 생성하고, `HLS` 변환을 통해 모든 환경에서 안정적인 청취 경험을 제공합니다.
- **🔍 엔드투엔드 추적 및 관찰**: `Langfuse`와 `OpenTelemetry`를 도입하여, 복잡한 에이전트 파이프라인의 모든 단계를 시각적으로 추적하고 시스템의 성능 및 로그를 체계적으로 모니터링합니다.
- ** realtime-icon 실시간 피드백**: `WebSocket`과 `Redis Pub/Sub`을 통해 팟캐스트 생성의 모든 진행 상황(에이전트 실행, TTS 생성 등)을 클라이언트에 실시간으로 전달합니다.
- **🔧 유연한 아키텍처**: `Docker Compose` 기반으로 전체 시스템이 모듈화되어 있어 개발, 배포, 확장이 용이합니다.

## 🏗️ 시스템 아키텍처

L-Graph는 여러 컴포넌트가 유기적으로 상호작용하는 이벤트 기반 아키텍처로 설계되었습니다.

```mermaid
graph TD
    subgraph "Client (Flutter)"
        A[사용자]
    end

    subgraph "Backend (FastAPI)"
        B(API Endpoints)
        C(WebSocket Manager)
    end

    subgraph "Task Queue"
        D(Celery)
        E(Redis)
    end

    subgraph "AI Agent Pipeline (LangGraph)"
        F[Supervisor Agent]
        G[Research Agent]
        H[Story Narrative Agent]
        I[TTS Optimization Agent]
    end

    subgraph "Data & Storage"
        J(PostgreSQL)
        K(MinIO Storage)
    end
    
    subgraph "Observability"
        L(Langfuse)
        M(OpenTelemetry)
    end

    A -- "1. 팟캐스트 생성 요청 (HTTP)" --> B
    B -- "2. 작업 생성 및 DB 저장" --> J
    B -- "3. 비동기 작업 발행" --> E
    A -- "1.1 WebSocket 연결" --> C
    E -- "4. 작업 전달" --> D
    D -- "5. 멀티 에이전트 파이프라인 실행" --> F
    F -- "6. 정보 조사 지시" --> G
    G -- "결과" --> F
    F -- "7. 대본 작성 지시" --> H
    H -- "결과" --> F
    F -- "8. TTS 최적화 지시" --> I
    I -- "최종 대본" --> F
    F -- "9. 파이프라인 결과 반환" --> D
    D -- "10. TTS 음성 생성/HLS 변환 작업 발행" --> E
    D -- "진행상황 업데이트 (DB 저장)" --> J
    D -- "에이전트 진행 상황 알림 (Pub)" --> E
    E -- "11. 실시간 알림 수신 (Sub)" --> C
    C -- "12. 클라이언트에 상태 전송" --> A
    D -- "13. 생성된 음원/HLS 파일 저장" --> K
```

## 🚀 시작하기

### 1. 필수 구성

- Docker
- Docker Compose

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 환경과 목적에 맞게 수정합니다.

```sh
# PostgreSQL 데이터베이스
DATABASE_URL=postgresql+psycopg2://lgraph_user:lgraph_password@postgres/lgraph

# Redis (Celery Broker & WebSocket Pub/Sub)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# MinIO Object Storage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=lgraph-audio
MINIO_SECURE=false

# LLM & TTS API Keys
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
ELEVEN_API_KEY=YOUR_ELEVENLABS_API_KEY
OPENAI_API_KEY=YOUR_OPENAI_API_KEY # LangGraph Supervisor 용

# Langfuse Tracing (선택사항)
LANGFUSE_PUBLIC_KEY=pk-lf-your-key
LANGFUSE_SECRET_KEY=sk-lf-your-key
LANGFUSE_HOST=https://cloud.langfuse.com

# JWT
JWT_SECRET_KEY=a_very_secret_key_that_should_be_long_and_random
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440 # 1 day
REFRESH_TOKEN_EXPIRE_MINUTES=20160 # 14 days
```

### 3. 전체 서비스 실행

아래 명령어로 모든 서비스(DB, Redis, MinIO, FastAPI, Celery)를 한번에 실행합니다.

```bash
docker-compose up --build
```

- **API 서버**: `http://localhost:8000`
- **API 문서 (Swagger UI)**: `http://localhost:8000/docs`
- **Celery 모니터링 (Flower)**: `http://localhost:5555`
- **MinIO 콘솔**: `http://localhost:9001`

## 📂 프로젝트 구조

```
lgraph/
├── agents/              # 🤖 멀티 에이전트 (LangGraph)
│   ├── super_agent.py   #   - 슈퍼바이저 (오케스트레이터)
│   ├── research_agent.py
│   ├── story_narrative_agent.py
│   └── tts_agent.py
├── tasks/               # ⚡️ Celery 비동기 작업
│   ├── podcast_tasks.py #   - 에이전트 파이프라인 실행
│   ├── tts_tasks.py     #   - TTS 음성 생성
│   └── hls_tasks.py     #   - HLS 스트리밍 변환
├── routers/             # 🔌 FastAPI 라우터 (API Endpoints)
├── services/            # ⚙️ 비즈니스 로직
├── schemas.py           # 📝 Pydantic 데이터 모델 (DTO)
├── database.py          # 🗃️ 데이터베이스 설정 및 모델
├── alembic/             #   - DB 마이그레이션 (스키마 변경)
├── prompts/             # 🗣️ 에이전트 프롬프트 템플릿
├── utils/               # 🛠️ 공용 유틸리티
│   ├── websocket_manager.py # - WebSocket 연결 관리
│   └── broker.py        # - Redis Pub/Sub 브로커
├── observability.py     # 🔍 OpenTelemetry 설정
├── main.py              # 🚀 FastAPI 애플리케이션 진입점
├── celery_app.py        #   - Celery 앱 초기화
├── config.py            #   - 환경변수 및 설정 관리
└── docker-compose.yml   #   - 서비스 컨테이너 오케스트레이션
```

## 🔧 주요 API 엔드포인트

> **인증**: 모든 요청은 `Authorization: Bearer <JWT_TOKEN>` 헤더가 필요합니다.

### 팟캐스트 생성

- `POST /podcast/create`
- **요청 본문**: `{ "user_request": "아이폰과 갤럭시의 기술적 비교" }`
- **설명**: 팟캐스트 생성 파이프라인을 시작합니다. 즉시 작업 ID를 반환하고, 모든 과정은 백그라운드에서 실행됩니다.

### 작업 상태 및 결과 조회

- `GET /podcast/tasks/{task_id}`: 특정 작업의 상세 정보와 모든 에이전트, TTS 결과를 조회합니다.
- `GET /podcast/tasks`: 현재 사용자의 모든 작업 목록을 조회합니다.
- `GET /podcast/tasks/{task_id}/status`: 특정 작업의 현재 상태(예: `PROCESSING`, `COMPLETED`)를 가볍게 확인합니다.

### 스크립트 수정 및 음성 재성성

- `PUT /podcast/tasks/{task_id}/regenerate`
- **요청 본문**: `{ "script": "수정된 최종 대본입니다..." }`
- **설명**: AI가 생성한 대본을 사용자가 직접 수정한 후, TTS 음성만 다시 생성합니다. 전체 파이프라인을 재실행하지 않아 효율적입니다.

### 실시간 업데이트 수신 (WebSocket)

- `GET ws://localhost:8000/ws/task-updates?token=<JWT_TOKEN>`
- **설명**: WebSocket에 연결하여 팟캐스트 생성 과정의 모든 단계를 실시간으로 수신합니다. (연결 수립, 상태 변경, 에이전트 진행 상황 등)

## 💡 개선 방안 제안

이어서 이 프로젝트를 더 발전시킬 수 있는 구체적인 개선 방안을 제안합니다.

---

(개선 방안 내용은 다음 메시지에서 이어집니다.)
