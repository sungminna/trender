# 🎵 오디오 스트리밍 서비스 개발 전략

## 📋 개요

LGraph 멀티 에이전트 시스템에서 생성된 TTS 오디오 파일을 효율적으로 스트리밍하기 위한 종합적인 개발 전략입니다.

## 🏗️ 현재 구현된 기본 기능

### 1. 기본 스트리밍 엔드포인트
- **GET** `/podcast/audio/{tts_id}/stream` - 브라우저 재생용 스트리밍
- **GET** `/podcast/audio/{tts_id}/download` - 강제 다운로드
- **GET** `/podcast/audio/{tts_id}/presigned-url` - 미리 서명된 URL 생성
- **GET** `/podcast/audio/list` - 사용 가능한 오디오 목록

### 2. MinIO 기반 객체 스토리지
- 파일시스템 대신 MinIO 사용
- 컨테이너 환경에서 확장 가능
- 자동 버킷 관리

## 🚀 고급 개발 전략

### 1. Range Request 지원 (HTTP 206)

**목적**: 대용량 오디오 파일의 부분 스트리밍, 탐색(seeking) 지원

```python
# 구현 예시
from fastapi import Request
import re

@app.get("/podcast/audio/{tts_id}/stream-range")
async def stream_audio_with_range(
    tts_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Range Request를 지원하는 오디오 스트리밍"""
    
    # 파일 크기 및 정보 조회
    tts_result = db.query(TTSResult).filter(TTSResult.id == tts_id).first()
    file_size = tts_result.audio_file_size
    
    # Range 헤더 파싱
    range_header = request.headers.get('Range')
    if range_header:
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            
            # MinIO에서 부분 객체 가져오기
            minio_client = get_minio_client()
            partial_object = minio_client.client.get_partial_object(
                bucket_name=minio_client.bucket_name,
                object_name=tts_result.audio_file_name,
                offset=start,
                length=end - start + 1
            )
            
            return StreamingResponse(
                partial_object,
                status_code=206,
                headers={
                    'Content-Range': f'bytes {start}-{end}/{file_size}',
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(end - start + 1),
                    'Content-Type': 'audio/wav'
                }
            )
```

### 2. 적응형 비트레이트 스트리밍 (ABS)

**목적**: 네트워크 상황에 따른 자동 품질 조정

```python
# 구현 전략
class AudioQualityManager:
    """오디오 품질 관리자"""
    
    QUALITY_PROFILES = {
        'low': {'bitrate': '64k', 'sample_rate': 22050},
        'medium': {'bitrate': '128k', 'sample_rate': 44100},
        'high': {'bitrate': '320k', 'sample_rate': 48000}
    }
    
    async def generate_multiple_qualities(self, tts_id: int):
        """하나의 TTS 결과로부터 여러 품질의 오디오 생성"""
        # FFmpeg를 사용한 실시간 트랜스코딩
        # MinIO에 다중 품질 저장
        pass
    
    async def select_optimal_quality(self, client_bandwidth: int):
        """클라이언트 대역폭에 따른 최적 품질 선택"""
        pass

# 엔드포인트 예시
@app.get("/podcast/audio/{tts_id}/adaptive/{quality}")
async def adaptive_stream(tts_id: int, quality: str):
    """적응형 품질 스트리밍"""
    pass
```

### 3. 실시간 스트리밍 (WebSocket/Server-Sent Events)

**목적**: TTS 생성과 동시에 실시간 스트리밍

```python
from fastapi import WebSocket
import asyncio

@app.websocket("/podcast/audio/{tts_id}/realtime")
async def realtime_audio_stream(websocket: WebSocket, tts_id: int):
    """실시간 오디오 스트리밍 (WebSocket)"""
    await websocket.accept()
    
    try:
        # TTS 생성 상태 모니터링
        while True:
            # Celery 작업 상태 확인
            # 생성된 청크가 있으면 즉시 전송
            # 완료되면 연결 종료
            await asyncio.sleep(0.1)
    except:
        await websocket.close()

@app.get("/podcast/audio/{tts_id}/events")
async def stream_audio_events(tts_id: int):
    """Server-Sent Events를 통한 스트리밍"""
    async def event_generator():
        # TTS 생성 진행상황을 실시간으로 전송
        yield "event: progress\ndata: 10%\n\n"
        yield "event: chunk\ndata: <audio_chunk_base64>\n\n"
        yield "event: complete\ndata: finished\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### 4. CDN 통합 및 캐싱 전략

**목적**: 글로벌 배포 및 성능 최적화

```python
class CDNManager:
    """CDN 관리자"""
    
    def __init__(self):
        self.cloudflare_zone = os.getenv("CLOUDFLARE_ZONE_ID")
        self.aws_cloudfront = os.getenv("AWS_CLOUDFRONT_DISTRIBUTION")
    
    async def push_to_cdn(self, object_name: str):
        """오디오 파일을 CDN에 배포"""
        # MinIO -> CloudFlare R2 / AWS S3
        # CDN 캐시 무효화
        pass
    
    async def get_cdn_url(self, object_name: str) -> str:
        """CDN URL 반환"""
        return f"https://cdn.lgraph.io/audio/{object_name}"

# 캐싱 헤더 최적화
@app.get("/podcast/audio/{tts_id}/cached")
async def cached_audio_stream(tts_id: int):
    """캐싱 최적화된 스트리밍"""
    return StreamingResponse(
        audio_stream,
        headers={
            'Cache-Control': 'public, max-age=86400, immutable',
            'ETag': f'"{tts_id}-{file_hash}"',
            'Last-Modified': last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
        }
    )
```

### 5. 보안 및 접근 제어

**목적**: 인증된 사용자만 오디오 접근 가능

```python
from datetime import timedelta
import jwt

class AudioAccessControl:
    """오디오 접근 제어"""
    
    async def generate_secure_token(self, user_id: str, tts_id: int) -> str:
        """보안 토큰 생성"""
        payload = {
            'user_id': user_id,
            'tts_id': tts_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    async def verify_access(self, token: str, tts_id: int) -> bool:
        """접근 권한 확인"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            return payload['tts_id'] == tts_id
        except:
            return False

@app.get("/podcast/audio/{tts_id}/secure")
async def secure_audio_stream(
    tts_id: int, 
    token: str = Depends(get_auth_token)
):
    """보안이 적용된 오디오 스트리밍"""
    if not await AudioAccessControl().verify_access(token, tts_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 정상 스트리밍 진행
    pass
```

### 6. 분석 및 모니터링

**목적**: 스트리밍 성능 및 사용량 분석

```python
from dataclasses import dataclass
import time

@dataclass
class StreamingMetrics:
    """스트리밍 메트릭"""
    tts_id: int
    user_id: str
    start_time: float
    bytes_transferred: int
    quality: str
    client_ip: str
    user_agent: str

class StreamingAnalytics:
    """스트리밍 분석"""
    
    async def track_stream_start(self, tts_id: int, request: Request):
        """스트리밍 시작 추적"""
        metrics = StreamingMetrics(
            tts_id=tts_id,
            user_id=get_user_from_request(request),
            start_time=time.time(),
            bytes_transferred=0,
            quality='auto',
            client_ip=request.client.host,
            user_agent=request.headers.get('User-Agent', '')
        )
        # Redis/InfluxDB에 저장
    
    async def track_stream_progress(self, tts_id: int, bytes_sent: int):
        """스트리밍 진행 추적"""
        # 실시간 메트릭 업데이트
        pass
    
    async def generate_analytics_report(self):
        """분석 리포트 생성"""
        return {
            'total_streams': 1000,
            'popular_content': [...],
            'bandwidth_usage': {...},
            'geographic_distribution': {...}
        }
```

### 7. 모바일 최적화

**목적**: 모바일 앱에서의 원활한 오디오 재생

```python
class MobileOptimization:
    """모바일 최적화"""
    
    async def detect_mobile_client(self, request: Request) -> bool:
        """모바일 클라이언트 감지"""
        user_agent = request.headers.get('User-Agent', '').lower()
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad']
        return any(keyword in user_agent for keyword in mobile_keywords)
    
    async def optimize_for_mobile(self, audio_stream, is_mobile: bool):
        """모바일에 최적화된 스트리밍"""
        if is_mobile:
            # 더 작은 청크 크기
            # 압축률 증가
            # 배터리 효율 고려
            pass
        return audio_stream

@app.get("/podcast/audio/{tts_id}/mobile")
async def mobile_optimized_stream(tts_id: int, request: Request):
    """모바일 최적화 스트리밍"""
    is_mobile = await MobileOptimization().detect_mobile_client(request)
    # 모바일 최적화 적용
    pass
```

### 8. 오프라인 지원

**목적**: 네트워크 불안정 환경에서도 원활한 재생

```python
class OfflineSupport:
    """오프라인 지원"""
    
    async def enable_progressive_download(self, tts_id: int):
        """점진적 다운로드 활성화"""
        # 클라이언트가 부분적으로 다운로드 가능
        # 중단된 지점부터 재개 가능
        pass
    
    async def generate_offline_package(self, tts_ids: List[int]):
        """오프라인 패키지 생성"""
        # 여러 오디오를 하나의 패키지로 압축
        # 메타데이터 포함
        pass
```

## 📊 성능 최적화 체크리스트

### 1. 서버 측 최적화
- [ ] MinIO 클러스터 구성 (분산 저장)
- [ ] Redis 캐싱 레이어 추가
- [ ] 비동기 처리 최적화
- [ ] 커넥션 풀링
- [ ] 로드 밸런싱

### 2. 네트워크 최적화
- [ ] GZIP 압축
- [ ] HTTP/2 지원
- [ ] Keep-Alive 연결
- [ ] CDN 통합
- [ ] Edge 캐싱

### 3. 클라이언트 최적화
- [ ] 프리로딩 전략
- [ ] 버퍼링 최적화
- [ ] 오류 복구 메커니즘
- [ ] 네트워크 상태 감지
- [ ] 사용자 경험 개선

## 🔧 구현 우선순위

### Phase 1: 기본 구현 (완료)
- [x] 기본 스트리밍 엔드포인트
- [x] MinIO 통합
- [x] Presigned URL 지원

### Phase 2: 성능 최적화
- [ ] Range Request 지원
- [ ] 캐싱 전략 구현
- [ ] 모니터링 시스템

### Phase 3: 고급 기능
- [ ] 적응형 스트리밍
- [ ] 실시간 스트리밍
- [ ] 보안 강화

### Phase 4: 확장성
- [ ] CDN 통합
- [ ] 모바일 최적화
- [ ] 오프라인 지원

## 🚨 주의사항

1. **저작권 및 라이선스**: TTS 생성된 콘텐츠의 저작권 확인 필요
2. **대역폭 비용**: 대용량 스트리밍으로 인한 비용 증가 고려
3. **보안**: 무단 접근 방지를 위한 인증 시스템 필수
4. **법적 규제**: 각 국가별 오디오 스트리밍 관련 법규 준수

## 📚 참고 자료

- [FastAPI StreamingResponse 문서](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [MinIO Python SDK](https://docs.min.io/docs/python-client-quickstart-guide.html)
- [HTTP Range Requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests)
- [Adaptive Bitrate Streaming](https://en.wikipedia.org/wiki/Adaptive_bitrate_streaming) 