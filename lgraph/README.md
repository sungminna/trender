# LGraph Multi-Agent Podcast System

한국어 팟캐스트 자동 생성을 위한 Multi-Agent AI 시스템

## 🎯 주요 기능

- **멀티 에이전트 파이프라인**: Research → Story Narrative → TTS Optimization
- **비동기 처리**: Celery 기반 백그라운드 작업
- **음성 생성**: TTS 엔진을 통한 고품질 한국어 음성 합성
- **스트리밍**: HLS 변환을 통한 적응형 스트리밍
- **트레이싱**: Langfuse 연동을 통한 멀티 에이전트 실행 추적
- **실시간 업데이트**: WebSocket을 통한 작업 진행 상황 실시간 알림

## 🏗️ 시스템 아키텍처

```
사용자 요청 → FastAPI → Celery → Multi-Agent Pipeline → TTS → HLS → 최종 결과
                ↓
            PostgreSQL ← → MinIO Storage ← → Langfuse Tracing
```

## 🚀 빠른 시작

### 1. 환경 설정

필수 환경변수를 `.env` 파일에 설정:

```bash
# 데이터베이스
DATABASE_URL=postgresql+psycopg2://user:password@localhost/lgraph

# Redis (Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=lgraph-audio
MINIO_SECURE=false

# TTS API 키
GEMINI_API_KEY=your_gemini_api_key_here
ELEVEN_API_KEY=your_eleven_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Langfuse 트레이싱 (선택사항)
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 2. 서비스 실행

```bash
# 1. FastAPI 서버 시작
python main.py

# 2. Celery 워커 시작 (별도 터미널)
celery -A celery_app worker --loglevel=info

# 3. (선택사항) Celery 모니터링
celery -A celery_app flower
```

## 📊 Langfuse 트레이싱

### 설정 방법

1. **Langfuse 계정 생성**: [https://langfuse.com](https://langfuse.com)
2. **프로젝트 생성** 및 API 키 획득
3. **환경변수 설정**:
   ```bash
   LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
   LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
   LANGFUSE_HOST=https://cloud.langfuse.com  # EU region
   # LANGFUSE_HOST=https://us.cloud.langfuse.com  # US region
   ```

### 자동 트레이싱 범위

✅ **추적되는 항목**:
- 멀티 에이전트 파이프라인 전체 실행
- 각 에이전트별 개별 실행 (Research, Story Narrative, TTS)
- 에이전트 간 메시지 전달
- 실행 시간 및 성능 메트릭
- 오류 및 예외 처리

✅ **트레이스 정보**:
- 작업 ID별 구분된 트레이스
- 에이전트별 입력/출력 데이터
- 실행 순서 및 소요 시간
- 최종 TTS 스크립트 결과

### 트레이싱 비활성화

Langfuse 환경변수를 설정하지 않으면 자동으로 비활성화되며, 시스템은 정상 작동합니다.

## 🔧 API 사용법

### 팟캐스트 생성

```bash
curl -X POST "http://localhost:8000/podcast/create" \
     -H "Content-Type: application/json" \
     -d '{"user_request": "아이폰과 갤럭시의 기술적 비교"}'
```

### 작업 상태 확인

```bash
curl "http://localhost:8000/podcast/tasks/1/status"
```

### WebSocket 실시간 업데이트

```javascript
// JWT 토큰을 쿼리 파라미터로 전달하여 WebSocket 연결
const token = "your_jwt_access_token";
const ws = new WebSocket(`ws://localhost:8000/ws/task-updates?token=${token}`);

ws.onopen = function(event) {
    console.log('WebSocket 연결됨');
    
    // Ping/Pong으로 연결 유지
    setInterval(() => {
        ws.send(JSON.stringify({
            type: "ping",
            timestamp: new Date().toISOString()
        }));
    }, 30000);
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'connection_established':
            console.log('연결 확인:', message.message);
            break;
            
        case 'task_status_update':
            console.log(`작업 ${message.task_id} 상태 변경: ${message.status}`);
            if (message.error_message) {
                console.error('오류:', message.error_message);
            }
            break;
            
        case 'agent_progress_update':
            console.log(`에이전트 ${message.agent_name} 진행 상황: ${message.agent_status}`);
            break;
            
        case 'tts_progress_update':
            console.log(`TTS 진행 상황: ${message.tts_status}`);
            if (message.message) {
                console.log(message.message);
            }
            break;
            
        case 'pong':
            console.log('Pong 수신');
            break;
    }
};

ws.onerror = function(error) {
    console.error('WebSocket 오류:', error);
};

ws.onclose = function(event) {
    console.log('WebSocket 연결 해제');
};
```

#### WebSocket 메시지 타입

- **connection_established**: 연결 성공 확인
- **task_status_update**: 작업 상태 변경 (PENDING → PROCESSING → COMPLETED/FAILED)
- **agent_progress_update**: 개별 에이전트 실행 진행 상황
- **tts_progress_update**: TTS 음성 생성 진행 상황
- **ping/pong**: 연결 유지를 위한 하트비트

### 트레이싱 결과 확인

Langfuse 대시보드에서 실시간 멀티 에이전트 실행 상황을 모니터링할 수 있습니다.

## 📁 프로젝트 구조

```
lgraph/
├── agents/              # 멀티 에이전트 시스템
│   ├── super_agent.py   # 슈퍼바이저 에이전트 (Langfuse 연동)
│   ├── research_agent.py
│   ├── story_narrative_agent.py
│   └── tts_agent.py
├── tasks/               # Celery 비동기 작업
├── routers/             # FastAPI 라우터
├── services/            # 비즈니스 로직
├── utils/               # 유틸리티 함수
├── prompts/             # 동적 프롬프트 관리
└── main.py              # FastAPI 애플리케이션
```

## 🎵 워크플로우

1. **사용자 요청** → FastAPI 엔드포인트
2. **Celery 작업 생성** → 백그라운드 처리 시작
3. **멀티 에이전트 실행** (Langfuse 트레이싱 활성화):
   - Research Agent: 정보 수집
   - Story Narrative Agent: 팟캐스트 스크립트 생성
   - TTS Agent: TTS 최적화
4. **TTS 음성 생성** → MinIO 저장
5. **HLS 변환** → 스트리밍 준비
6. **완료 알림** → 클라이언트 응답

## 🔍 모니터링 및 디버깅

- **Langfuse**: 멀티 에이전트 실행 추적
- **Celery Flower**: 작업 큐 모니터링  
- **FastAPI Docs**: API 문서 (`/docs`)
- **시스템 통계**: `/podcast/stats` 엔드포인트
- **WebSocket 테스트**: `test_websocket_client.html` 파일로 실시간 업데이트 테스트

## 🧪 WebSocket 테스트 방법

1. **서버 실행**: FastAPI 서버와 Celery 워커를 실행합니다.
2. **브라우저에서 테스트 클라이언트 열기**:
   ```bash
   # 브라우저에서 직접 파일 열기
   open lgraph/test_websocket_client.html
   ```
3. **JWT 토큰 획득**: `/auth/login` 엔드포인트로 로그인하여 액세스 토큰을 획득합니다.
4. **WebSocket 연결**: 테스트 클라이언트에서 토큰을 입력하고 연결 버튼을 클릭합니다.
5. **팟캐스트 생성**: 연결된 상태에서 팟캐스트 생성 버튼을 클릭하여 실시간 업데이트를 확인합니다.

### 실시간 업데이트 확인 항목
- ✅ 작업 생성 시 PENDING → PROCESSING 상태 변경
- ✅ 각 에이전트 실행 진행 상황 (Research → Story Narrative → TTS)
- ✅ TTS 음원 생성 진행 상황
- ✅ HLS 변환 진행 상황
- ✅ 최종 완료 또는 오류 상태

## �� 라이선스

MIT License
