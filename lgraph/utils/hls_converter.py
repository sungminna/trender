"""
HLS (HTTP Live Streaming) 변환 유틸리티

WAV 오디오 파일을 HLS 형식으로 변환하여 스트리밍 최적화
"""

import os
import tempfile
import shutil
from typing import Dict, List, Optional
import ffmpeg
from datetime import datetime
from utils.minio_client import get_minio_client


class HLSConverter:
    """HLS 변환기"""
    
    def __init__(self):
        self.minio_client = get_minio_client()
        # HLS 설정
        self.segment_duration = 10  # 10초 세그먼트
        self.playlist_type = "vod"  # VOD 타입
        
    def convert_wav_to_hls(self, 
                          wav_object_name: str, 
                          hls_folder_name: str,
                          bitrates: List[int] = None) -> Dict:
        """
        WAV 파일을 HLS 형식으로 변환
        
        Args:
            wav_object_name: MinIO의 WAV 파일 객체명
            hls_folder_name: HLS 파일들이 저장될 폴더명 (MinIO)
            bitrates: 다중 비트레이트 리스트 (기본: [64, 128, 320])
            
        Returns:
            변환 결과 정보
        """
        if bitrates is None:
            bitrates = [64, 128, 320]  # kbps
            
        try:
            print(f"🎬 HLS 변환 시작: {wav_object_name}")
            
            # 임시 디렉토리 생성
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. MinIO에서 WAV 파일 다운로드
                wav_temp_path = os.path.join(temp_dir, "input.wav")
                download_result = self.minio_client.download_file(wav_object_name, wav_temp_path)
                
                if not download_result["success"]:
                    raise Exception(f"WAV 파일 다운로드 실패: {download_result['error']}")
                
                # 2. 다중 비트레이트 HLS 생성
                hls_results = {}
                master_playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n\n"
                
                for bitrate in bitrates:
                    print(f"  📊 {bitrate}kbps 비트레이트 변환 중...")
                    
                    # 비트레이트별 폴더 생성
                    bitrate_dir = os.path.join(temp_dir, f"{bitrate}k")
                    os.makedirs(bitrate_dir, exist_ok=True)
                    
                    # HLS 변환 실행
                    hls_result = self._convert_single_bitrate(
                        wav_temp_path, 
                        bitrate_dir, 
                        bitrate
                    )
                    
                    if hls_result["success"]:
                        hls_results[bitrate] = hls_result
                        
                        # Master playlist에 추가
                        master_playlist_content += f"#EXT-X-STREAM-INF:BANDWIDTH={bitrate * 1000},CODECS=\"mp4a.40.2\"\n"
                        master_playlist_content += f"{bitrate}k/playlist.m3u8\n\n"
                    else:
                        print(f"  ❌ {bitrate}kbps 변환 실패: {hls_result['error']}")
                
                # 3. Master playlist 생성
                master_playlist_path = os.path.join(temp_dir, "master.m3u8")
                with open(master_playlist_path, 'w', encoding='utf-8') as f:
                    f.write(master_playlist_content)
                
                # 4. 모든 HLS 파일을 MinIO에 업로드
                upload_results = self._upload_hls_files_to_minio(temp_dir, hls_folder_name)
                
                # 5. 결과 정보 생성
                total_segments = sum(result.get("segment_count", 0) for result in hls_results.values())
                total_duration = max(result.get("duration", 0) for result in hls_results.values()) if hls_results else 0
                
                result = {
                    "success": True,
                    "hls_folder_name": hls_folder_name,
                    "master_playlist": f"{hls_folder_name}/master.m3u8",
                    "bitrates": list(bitrates),
                    "total_segments": total_segments,
                    "duration": total_duration,
                    "upload_results": upload_results,
                    "converted_at": datetime.utcnow().isoformat()
                }
                
                print(f"✅ HLS 변환 완료!")
                print(f"   - 비트레이트: {bitrates}")
                print(f"   - 총 세그먼트: {total_segments}개")
                print(f"   - 재생시간: {total_duration:.1f}초")
                
                return result
                
        except Exception as e:
            error_msg = f"HLS 변환 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "wav_object_name": wav_object_name
            }
    
    def _convert_single_bitrate(self, input_path: str, output_dir: str, bitrate: int) -> Dict:
        """단일 비트레이트로 HLS 변환"""
        try:
            playlist_path = os.path.join(output_dir, "playlist.m3u8")
            segment_pattern = os.path.join(output_dir, "segment_%03d.ts")
            
            # FFmpeg로 HLS 변환
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream,
                playlist_path,
                format='hls',
                audio_bitrate=f'{bitrate}k',
                hls_time=self.segment_duration,
                hls_playlist_type=self.playlist_type,
                hls_segment_filename=segment_pattern,
                hls_flags='delete_segments'  # 이전 세그먼트 자동 삭제
            )
            
            # 변환 실행
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            # 생성된 파일들 확인
            segments = [f for f in os.listdir(output_dir) if f.endswith('.ts')]
            
            # 재생시간 확인
            probe = ffmpeg.probe(input_path)
            duration = float(probe['streams'][0]['duration'])
            
            return {
                "success": True,
                "bitrate": bitrate,
                "segment_count": len(segments),
                "duration": duration,
                "playlist_file": "playlist.m3u8",
                "segments": segments
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "bitrate": bitrate
            }
    
    def _upload_hls_files_to_minio(self, temp_dir: str, hls_folder_name: str) -> Dict:
        """HLS 파일들을 MinIO에 업로드"""
        upload_results = {
            "master_playlist": None,
            "bitrate_playlists": {},
            "segments": {}
        }
        
        try:
            # Master playlist 업로드
            master_playlist_path = os.path.join(temp_dir, "master.m3u8")
            if os.path.exists(master_playlist_path):
                master_object_name = f"{hls_folder_name}/master.m3u8"
                result = self.minio_client.upload_file(
                    object_name=master_object_name,
                    file_path=master_playlist_path,
                    content_type="application/vnd.apple.mpegurl"
                )
                upload_results["master_playlist"] = result
            
            # 각 비트레이트별 파일들 업로드
            for bitrate_dir in os.listdir(temp_dir):
                bitrate_path = os.path.join(temp_dir, bitrate_dir)
                if os.path.isdir(bitrate_path) and bitrate_dir.endswith('k'):
                    bitrate = bitrate_dir.replace('k', '')
                    upload_results["bitrate_playlists"][bitrate] = {}
                    upload_results["segments"][bitrate] = []
                    
                    # Playlist 파일 업로드
                    playlist_file = os.path.join(bitrate_path, "playlist.m3u8")
                    if os.path.exists(playlist_file):
                        playlist_object_name = f"{hls_folder_name}/{bitrate_dir}/playlist.m3u8"
                        result = self.minio_client.upload_file(
                            object_name=playlist_object_name,
                            file_path=playlist_file,
                            content_type="application/vnd.apple.mpegurl"
                        )
                        upload_results["bitrate_playlists"][bitrate] = result
                    
                    # 세그먼트 파일들 업로드
                    for segment_file in os.listdir(bitrate_path):
                        if segment_file.endswith('.ts'):
                            segment_path = os.path.join(bitrate_path, segment_file)
                            segment_object_name = f"{hls_folder_name}/{bitrate_dir}/{segment_file}"
                            result = self.minio_client.upload_file(
                                object_name=segment_object_name,
                                file_path=segment_path,
                                content_type="video/mp2t"
                            )
                            upload_results["segments"][bitrate].append(result)
            
            return upload_results
            
        except Exception as e:
            print(f"❌ HLS 파일 업로드 실패: {str(e)}")
            return {"error": str(e)}
    
    def get_hls_info(self, hls_folder_name: str) -> Optional[Dict]:
        """HLS 정보 조회"""
        try:
            # Master playlist 존재 확인
            master_playlist_name = f"{hls_folder_name}/master.m3u8"
            master_info = self.minio_client.get_object_info(master_playlist_name)
            
            if not master_info:
                return None
            
            # HLS 폴더의 모든 객체 조회
            hls_objects = self.minio_client.list_objects(prefix=hls_folder_name)
            
            # 비트레이트별 정보 수집
            bitrates = {}
            total_segments = 0
            
            for obj in hls_objects:
                obj_name = obj["object_name"]
                if "/playlist.m3u8" in obj_name and obj_name != master_playlist_name:
                    # 비트레이트 추출
                    bitrate = obj_name.split("/")[-2].replace("k", "")
                    if bitrate.isdigit():
                        bitrates[bitrate] = {
                            "playlist": obj_name,
                            "segments": []
                        }
                elif ".ts" in obj_name:
                    total_segments += 1
                    # 해당 비트레이트의 세그먼트로 분류
                    for bitrate in bitrates:
                        if f"/{bitrate}k/" in obj_name:
                            bitrates[bitrate]["segments"].append(obj_name)
            
            return {
                "hls_folder_name": hls_folder_name,
                "master_playlist": master_playlist_name,
                "bitrates": bitrates,
                "total_segments": total_segments,
                "master_playlist_info": master_info
            }
            
        except Exception as e:
            print(f"❌ HLS 정보 조회 실패: {str(e)}")
            return None
    
    def delete_hls_files(self, hls_folder_name: str) -> Dict:
        """HLS 파일들 삭제"""
        try:
            # HLS 폴더의 모든 객체 조회
            hls_objects = self.minio_client.list_objects(prefix=hls_folder_name)
            
            deleted_count = 0
            for obj in hls_objects:
                delete_result = self.minio_client.delete_object(obj["object_name"])
                if delete_result["success"]:
                    deleted_count += 1
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "hls_folder_name": hls_folder_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "hls_folder_name": hls_folder_name
            }


# 전역 인스턴스
hls_converter = None

def get_hls_converter() -> HLSConverter:
    """HLS 변환기 인스턴스를 반환합니다."""
    global hls_converter
    if hls_converter is None:
        hls_converter = HLSConverter()
    return hls_converter


if __name__ == "__main__":
    # 테스트 코드
    converter = get_hls_converter()
    
    # 테스트용 WAV 파일이 있다면 변환 테스트
    test_wav = "test_audio.wav"  # MinIO 객체명
    test_hls_folder = "test_hls_output"
    
    print("HLS 변환기 테스트 준비 완료")
    print(f"테스트 명령: converter.convert_wav_to_hls('{test_wav}', '{test_hls_folder}')") 