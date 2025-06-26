# HLS 스트리밍 가이드

## 🎬 HLS (HTTP Live Streaming) 개요

HLS는 Apple에서 개발한 적응형 스트리밍 프로토콜로, 네트워크 상황에 따라 자동으로 품질을 조절하여 끊김 없는 재생을 제공합니다.

### 주요 특징
- **적응형 스트리밍**: 네트워크 상황에 따라 자동 품질 조절
- **다중 비트레이트**: 64kbps, 128kbps, 320kbps 3가지 품질 제공
- **세그먼트 기반**: 10초 단위 세그먼트로 분할하여 빠른 시작
- **CDN 친화적**: 정적 파일로 구성되어 CDN 캐싱 최적화
- **크로스 플랫폼**: 모든 주요 브라우저 및 모바일 지원

## 🚀 HLS 생성 및 사용법

### 1. HLS 스트리밍 생성

```bash
# TTS 결과로부터 HLS 생성
POST /podcast/tts/{tts_id}/generate-hls

# 응답 예시
{
    "message": "Audio generation and HLS conversion started",
    "tts_id": 1,
    "celery_task_id": "abc123-def456",
    "status": "processing"
}
```

### 2. HLS 생성 상태 확인

```bash
# TTS 및 HLS 상태 확인
GET /podcast/tts/{tts_id}/status

# 응답 예시
{
    "tts_id": 1,
    "is_audio_generated": "true",
    "tts_status": "completed",
    "is_hls_generated": "true",
    "hls_status": "completed",
    "hls_folder_name": "hls_1",
    "hls_master_playlist": "hls_1/master.m3u8",
    "hls_bitrates": [64, 128, 320],
    "hls_total_segments": 15
}
```

### 3. HLS 스트리밍 재생

```bash
# Master Playlist 접근
GET /podcast/hls/{tts_id}/master.m3u8

# 특정 비트레이트 Playlist
GET /podcast/hls/{tts_id}/128k/playlist.m3u8

# 세그먼트 파일
GET /podcast/hls/{tts_id}/128k/segment_001.ts
```

## 🎵 프론트엔드 구현 예시

### HTML5 Video/Audio 태그

```html
<!-- 기본 HTML5 audio 태그 -->
<audio controls>
    <source src="/podcast/hls/1/master.m3u8" type="application/vnd.apple.mpegurl">
    Your browser does not support HLS streaming.
</audio>
```

### HLS.js 사용 (권장)

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<body>
    <audio id="audio" controls></audio>
    
    <script>
        const audio = document.getElementById('audio');
        const hlsUrl = '/podcast/hls/1/master.m3u8';
        
        if (Hls.isSupported()) {
            const hls = new Hls({
                debug: true,
                enableWorker: true,
                lowLatencyMode: false,
                backBufferLength: 90
            });
            
            hls.loadSource(hlsUrl);
            hls.attachMedia(audio);
            
            hls.on(Hls.Events.MANIFEST_PARSED, function() {
                console.log('HLS playlist loaded');
                // 자동 재생하려면: audio.play();
            });
            
            hls.on(Hls.Events.ERROR, function(event, data) {
                console.error('HLS error:', data);
            });
        } else if (audio.canPlayType('application/vnd.apple.mpegurl')) {
            // Safari 네이티브 HLS 지원
            audio.src = hlsUrl;
        } else {
            console.error('HLS not supported');
        }
    </script>
</body>
</html>
```

### React 컴포넌트

```jsx
import React, { useEffect, useRef } from 'react';
import Hls from 'hls.js';

const HLSPlayer = ({ ttsId, autoPlay = false }) => {
    const audioRef = useRef(null);
    const hlsRef = useRef(null);
    
    useEffect(() => {
        const audio = audioRef.current;
        const hlsUrl = `/podcast/hls/${ttsId}/master.m3u8`;
        
        if (Hls.isSupported()) {
            const hls = new Hls({
                debug: false,
                enableWorker: true,
                lowLatencyMode: false,
                backBufferLength: 90
            });
            
            hls.loadSource(hlsUrl);
            hls.attachMedia(audio);
            hlsRef.current = hls;
            
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                console.log('HLS manifest loaded');
                if (autoPlay) {
                    audio.play().catch(console.error);
                }
            });
            
            hls.on(Hls.Events.ERROR, (event, data) => {
                console.error('HLS error:', data);
                if (data.fatal) {
                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            hls.recoverMediaError();
                            break;
                        default:
                            hls.destroy();
                            break;
                    }
                }
            });
        } else if (audio.canPlayType('application/vnd.apple.mpegurl')) {
            audio.src = hlsUrl;
        }
        
        return () => {
            if (hlsRef.current) {
                hlsRef.current.destroy();
            }
        };
    }, [ttsId, autoPlay]);
    
    return (
        <div className="hls-player">
            <audio 
                ref={audioRef} 
                controls 
                preload="metadata"
                style={{ width: '100%' }}
            />
        </div>
    );
};

export default HLSPlayer;
```

### React Native 구현

```jsx
import React from 'react';
import { View } from 'react-native';
import Video from 'react-native-video';

const HLSPlayer = ({ ttsId }) => {
    const hlsUrl = `https://your-domain.com/podcast/hls/${ttsId}/master.m3u8`;
    
    return (
        <View>
            <Video
                source={{ uri: hlsUrl }}
                audioOnly={true}
                controls={true}
                resizeMode="contain"
                onError={(error) => console.error('Video error:', error)}
                onLoad={(data) => console.log('Video loaded:', data)}
                style={{ height: 50 }}
            />
        </View>
    );
};
```

## 📊 HLS 관리 API

### 사용 가능한 HLS 목록 조회

```bash
GET /podcast/hls/list?skip=0&limit=10

# 응답 예시
{
    "total_count": 3,
    "hls_streams": [
        {
            "tts_id": 1,
            "task_id": 1,
            "user_request": "AI 기술 트렌드",
            "master_playlist_url": "/podcast/hls/1/master.m3u8",
            "available_bitrates": [64, 128, 320],
            "total_segments": 15,
            "duration": 150,
            "generated_at": "2023-12-01T10:00:00Z",
            "info_url": "/podcast/hls/1/info"
        }
    ],
    "pagination": {
        "skip": 0,
        "limit": 10,
        "has_more": false
    }
}
```

### HLS 상세 정보 조회

```bash
GET /podcast/hls/{tts_id}/info

# 응답 예시
{
    "tts_id": 1,
    "hls_status": "completed",
    "hls_folder_name": "hls_1",
    "master_playlist_url": "/podcast/hls/1/master.m3u8",
    "available_bitrates": [64, 128, 320],
    "total_segments": 15,
    "duration": 150,
    "generated_at": "2023-12-01T10:00:00Z",
    "bitrate_playlists": {
        "64": "/podcast/hls/1/64k/playlist.m3u8",
        "128": "/podcast/hls/1/128k/playlist.m3u8",
        "320": "/podcast/hls/1/320k/playlist.m3u8"
    }
}
```

## 🔧 고급 설정

### 사용자 정의 비트레이트

기본적으로 64kbps, 128kbps, 320kbps 3가지 품질을 제공하지만, 필요시 `utils/hls_converter.py`에서 수정 가능합니다.

```python
# 기본 비트레이트 변경
bitrates = [32, 64, 128, 256, 320]  # 5가지 품질
```

### 세그먼트 길이 조정

```python
# HLS 변환기 설정
self.segment_duration = 6  # 6초 세그먼트 (기본: 10초)
```

### CDN 최적화

HLS 파일들은 정적 파일이므로 CDN을 통해 서비스하면 성능이 크게 향상됩니다:

1. **CloudFlare**: 자동 HLS 캐싱 지원
2. **AWS CloudFront**: Origin에서 MinIO 설정
3. **Azure CDN**: 커스텀 규칙으로 .m3u8, .ts 파일 캐싱

## 📱 모바일 최적화

### iOS Safari
- 네이티브 HLS 지원
- 백그라운드 재생 지원
- Picture-in-Picture 지원

### Android Chrome
- HLS.js 사용 권장
- Service Worker로 오프라인 캐싱 가능

## 🚨 문제 해결

### 일반적인 문제들

1. **CORS 오류**
   ```
   Access-Control-Allow-Origin: *
   Access-Control-Allow-Headers: *
   ```

2. **HLS 로딩 실패**
   - Master playlist 접근 가능 여부 확인
   - 네트워크 연결 상태 확인
   - 브라우저 콘솔에서 오류 메시지 확인

3. **품질 전환 안됨**
   - HLS.js 버전 확인 (최신 버전 사용 권장)
   - 네트워크 속도 테스트

### 로그 확인

```bash
# Celery 로그에서 HLS 변환 상태 확인
docker-compose logs celery

# MinIO 객체 확인
docker-compose exec minio mc ls minio/lgraph-audio/hls_1/
```

## 🎯 성능 최적화 팁

1. **프리로딩**: `preload="metadata"` 사용
2. **버퍼링**: HLS.js `backBufferLength` 조정
3. **CDN 활용**: 정적 파일 CDN 서비스
4. **압축**: MinIO에서 gzip 압축 활성화
5. **캐싱**: 적절한 Cache-Control 헤더 설정

이제 고품질의 적응형 오디오 스트리밍 서비스를 제공할 수 있습니다! 🎉 