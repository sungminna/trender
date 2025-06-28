"""
TTS 음원 생성 관련 Celery 태스크들
"""

import os
import tempfile
from datetime import datetime
from database import TTSResult, TTSStatus, PodcastTask, TaskStatus
from tts import get_tts_generator
from utils.minio_client import get_minio_client
from .celery_config import celery_app
from .utils import get_db, handle_task_error


@celery_app.task(bind=True)
def generate_tts(self, task_id: int, script: str, user_request: str):
    """
    새로운 TTSResult를 생성하고, 실제 음원 생성을 위한 백그라운드 태스크를 시작합니다.
    이 태스크는 팟캐스트 재성성(regeneration) 플로우에서 사용됩니다.
    """
    with next(get_db()) as db:
        try:
            # 상위 PodcastTask의 상태를 PROCESSING으로 업데이트
            task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
            if not task:
                raise Exception(f"PodcastTask {task_id} not found")
            
            task.status = TaskStatus.PROCESSING
            db.commit()

            # 1. 새로운 TTSResult 레코드 생성
            audio_file_name = f"podcast_task_{task_id}_tts_{int(datetime.utcnow().timestamp())}.wav"
            
            new_tts_result = TTSResult(
                task_id=task_id,
                user_request=user_request,
                script_content=script,
                raw_script=script, # 원본 스크립트도 저장
                tts_status=TTSStatus.PENDING,
                audio_file_name=audio_file_name,
                audio_file_path=f"audio-files/{audio_file_name}" # MinIO 경로
            )
            db.add(new_tts_result)
            db.commit()
            db.refresh(new_tts_result)
            
            print(f"✅ 새로운 TTS Result 레코드 생성됨 (ID: {new_tts_result.id})")

            # 2. 실제 음원 생성을 위한 태스크 호출
            generate_tts_audio.delay(new_tts_result.id)
            
            return {"status": "success", "tts_result_id": new_tts_result.id}

        except Exception as e:
            handle_task_error("TTS Result Creation", task_id, e)
            # 상위 작업 상태를 FAILED로 업데이트
            try:
                task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_message = f"TTS Result 생성 실패: {e}"
                    db.commit()
            except Exception as db_error:
                print(f"⚠️ 작업 상태 업데이트 실패: {db_error}")

            raise e


@celery_app.task(bind=True)
def generate_tts_audio(self, tts_result_id: int):
    """TTS 결과로부터 실제 음원을 생성하는 Celery 태스크"""
    with next(get_db()) as db:
        try:
            # TTS 결과 조회
            tts_result = db.query(TTSResult).filter(TTSResult.id == tts_result_id).first()
            if not tts_result:
                raise Exception(f"TTS Result {tts_result_id} not found")
            
            # 이미 음원이 생성되었는지 확인
            if tts_result.is_audio_generated == "true":
                print(f"⚠️ TTS Result {tts_result_id}의 음원이 이미 생성되어 있습니다.")
                return {"status": "already_generated", "tts_result_id": tts_result_id}
            
            # TTS 상태를 PROCESSING으로 업데이트
            tts_result.tts_status = TTSStatus.PROCESSING
            db.commit()
            
            print(f"🎙️ TTS 음원 생성 시작... (TTS Result ID: {tts_result_id})")
            print(f"   - 스크립트 길이: {len(tts_result.script_content)} 문자")
            print(f"   - MinIO 객체명: {tts_result.audio_file_name}")
            
            # TTS 생성기 인스턴스 가져오기
            tts_generator = get_tts_generator()
            
            # MinIO 클라이언트 가져오기
            minio_client = get_minio_client()
            
            # 임시 파일에 음성 생성
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                # 단일 화자 음성 생성 (임시 파일에)
                generation_result = tts_generator.generate_single_speaker_audio(
                    text=tts_result.script_content,
                    output_path=temp_file_path,
                    voice_name="Kore"  # 한국어에 적합한 목소리
                )
            
                if generation_result["success"]:
                    # TTS 생성 성공 시 MinIO에 업로드
                    upload_result = minio_client.upload_file(
                        object_name=tts_result.audio_file_name,
                        file_path=temp_file_path,
                        content_type="audio/wav"
                    )
                    
                    if upload_result["success"]:
                        # MinIO 업로드 성공 시 데이터베이스 업데이트
                        tts_result.is_audio_generated = "true"
                        tts_result.tts_status = TTSStatus.COMPLETED
                        tts_result.audio_generated_at = datetime.utcnow()
                        
                        # 파일 정보 업데이트
                        file_info = generation_result["file_info"]
                        tts_result.audio_file_size = file_info["file_size"]
                        tts_result.audio_duration = file_info["duration"]
                        
                        db.commit()
                        
                        print(f"✅ TTS 음원 생성 및 MinIO 업로드 완료!")
                        print(f"   - MinIO 객체명: {tts_result.audio_file_name}")
                        print(f"   - 파일 크기: {file_info['file_size']:,} bytes")
                        print(f"   - 재생 시간: {file_info['duration']} 초")
                        
                        # HLS 변환 작업을 별도 태스크로 시작
                        _start_hls_conversion_task(tts_result_id)
                        
                        return {
                            "status": "completed", 
                            "tts_result_id": tts_result_id,
                            "object_name": tts_result.audio_file_name,
                            "minio_path": tts_result.audio_file_path,
                            "file_info": file_info,
                            "hls_task_started": True
                        }
                    else:
                        # MinIO 업로드 실패
                        raise Exception(f"MinIO 업로드 실패: {upload_result['error']}")
                else:
                    # TTS 생성 실패
                    raise Exception(generation_result["error"])
                    
            finally:
                # 임시 파일 정리
                try:
                    os.unlink(temp_file_path)
                    print(f"🗑️ 임시 파일 삭제: {temp_file_path}")
                except Exception as cleanup_error:
                    print(f"⚠️ 임시 파일 삭제 실패: {cleanup_error}")
                
        except Exception as e:
            # 에러 발생 시 롤백 후 상태 업데이트
            try:
                db.rollback()
            except Exception:
                pass
            
            error_info = handle_task_error("TTS Audio Generation", tts_result_id, e)
            
            try:
                tts_result = db.query(TTSResult).filter(TTSResult.id == tts_result_id).first()
                if tts_result:
                    tts_result.tts_status = TTSStatus.FAILED
                    tts_result.error_message = f"{error_info['error_message']}\n\nTraceback:\n{error_info['error_traceback']}"
                    db.commit()
            except Exception as db_error:
                print(f"⚠️ 데이터베이스 업데이트 실패: {db_error}")
            
            raise Exception(f"TTS audio generation failed for {tts_result_id}: {error_info['error_message']}")


def _start_hls_conversion_task(tts_result_id: int):
    """HLS 변환 태스크를 시작합니다."""
    try:
        # 지연 import로 순환 참조 방지
        from .hls_tasks import generate_hls_from_wav
        
        hls_task = generate_hls_from_wav.delay(tts_result_id)
        print(f"🎬 HLS 변환 작업 시작됨 - TTS Result ID: {tts_result_id}, Celery Task ID: {hls_task.id}")
    except Exception as hls_task_error:
        print(f"⚠️ HLS 변환 작업 시작 실패: {hls_task_error}") 