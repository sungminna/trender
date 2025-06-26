"""
HLS 변환 관련 Celery 태스크들
"""

from datetime import datetime
import os
from database import TTSResult, HLSStatus
from utils.hls_converter import get_hls_converter
from .celery_config import celery_app
from .utils import get_db, handle_task_error


@celery_app.task(bind=True)
def generate_hls_from_wav(self, tts_result_id: int):
    """WAV 파일로부터 HLS를 생성하는 별도 Celery 태스크"""
    with next(get_db()) as db:
        try:
            # TTS 결과 조회
            tts_result = db.query(TTSResult).filter(TTSResult.id == tts_result_id).first()
            if not tts_result:
                raise Exception(f"TTS Result {tts_result_id} not found")
            
            # WAV 파일이 생성되어 있는지 확인
            if tts_result.is_audio_generated != "true":
                raise Exception(f"WAV 파일이 아직 생성되지 않았습니다: {tts_result_id}")
            
            print(f"🎬 HLS 변환 시작... (TTS Result ID: {tts_result_id})")
            
            # HLS 변환 실행
            hls_result = _convert_to_hls_helper(tts_result, db)
            
            return {
                "status": "completed" if hls_result["success"] else "failed",
                "tts_result_id": tts_result_id,
                "hls_result": hls_result
            }
            
        except Exception as e:
            error_info = handle_task_error("HLS Conversion", tts_result_id, e)
            
            try:
                tts_result = db.query(TTSResult).filter(TTSResult.id == tts_result_id).first()
                if tts_result:
                    tts_result.hls_status = HLSStatus.FAILED
                    tts_result.hls_error_message = f"HLS 변환 실패: {error_info['error_message']}"
                    db.commit()
            except Exception:
                pass
            
            raise Exception(f"HLS conversion failed for {tts_result_id}: {error_info['error_message']}")


def _convert_to_hls_helper(tts_result, db) -> dict:
    """WAV 파일을 HLS로 변환하는 헬퍼 함수"""
    try:
        print(f"🎬 HLS 변환 시작... (TTS Result ID: {tts_result.id})")
        
        # HLS 상태를 PROCESSING으로 업데이트
        tts_result.hls_status = HLSStatus.PROCESSING
        db.commit()
        
        # HLS 변환기 가져오기
        hls_converter = get_hls_converter()
        
        # HLS 폴더명 생성 (tts_id_hls)
        hls_folder_name = f"hls_{tts_result.id}"
        
        # WAV 파일을 HLS로 변환
        conversion_result = hls_converter.convert_wav_to_hls(
            wav_object_name=tts_result.audio_file_name,
            hls_folder_name=hls_folder_name,
            bitrates=[64, 128, 320]  # 3가지 품질
        )
        
        if conversion_result["success"]:
            # HLS 변환 성공 시 데이터베이스 업데이트
            tts_result.hls_folder_name = hls_folder_name
            tts_result.hls_master_playlist = conversion_result["master_playlist"]
            tts_result.hls_bitrates = conversion_result["bitrates"]
            tts_result.hls_total_segments = conversion_result["total_segments"]
            tts_result.is_hls_generated = "true"
            tts_result.hls_status = HLSStatus.COMPLETED
            tts_result.hls_generated_at = datetime.utcnow()
            
            db.commit()
            
            print(f"✅ HLS 변환 완료!")
            print(f"   - HLS 폴더: {hls_folder_name}")
            print(f"   - Master playlist: {conversion_result['master_playlist']}")
            print(f"   - 비트레이트: {conversion_result['bitrates']}")
            print(f"   - 총 세그먼트: {conversion_result['total_segments']}개")
            
            return {
                "success": True,
                "hls_folder_name": hls_folder_name,
                "master_playlist": conversion_result["master_playlist"],
                "bitrates": conversion_result["bitrates"],
                "total_segments": conversion_result["total_segments"]
            }
        else:
            # HLS 변환 실패
            tts_result.hls_status = HLSStatus.FAILED
            tts_result.hls_error_message = conversion_result["error"]
            db.commit()
            
            print(f"❌ HLS 변환 실패: {conversion_result['error']}")
            return {
                "success": False,
                "error": conversion_result["error"]
            }
            
    except Exception as e:
        # HLS 변환 중 예외 발생
        error_msg = f"HLS 변환 중 예외 발생: {str(e)}"
        print(f"❌ {error_msg}")
        
        try:
            tts_result.hls_status = HLSStatus.FAILED
            tts_result.hls_error_message = error_msg
            db.commit()
        except Exception:
            pass
        
        return {
            "success": False,
            "error": error_msg
        }


 