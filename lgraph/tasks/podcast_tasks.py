"""
팟캐스트 생성 관련 Celery 태스크들
"""

from datetime import datetime
import os
from database import PodcastTask, AgentResult, TaskStatus, TTSResult, TTSStatus, HLSStatus
from agents.super_agent import supervisor
from langchain_core.messages import convert_to_messages
from .celery_config import celery_app
from .utils import (
    get_db, 
    _serialize_message, 
    _get_agent_type, 
    _extract_raw_final_script, 
    _clean_tts_script,
    _generate_audio_object_name,
    handle_task_error
)
import traceback


@celery_app.task(bind=True)
def process_podcast_task(self, task_id: int, user_request: str):
    """팟캐스트 생성 작업을 처리하는 Celery 태스크"""
    with next(get_db()) as db:
        try:
            # 작업 상태를 PROCESSING으로 업데이트
            task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
            if not task:
                raise Exception(f"Task {task_id} not found")
            
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            db.commit()
            
            # 에이전트 실행 결과를 배치로 저장할 리스트
            agent_results_batch = []
            agent_execution_count = {}  # 에이전트별 실행 횟수 추적
            final_messages = []
            raw_final_script = ""  # 멀티 에이전트 최종 TTS 스크립트
            
            # 슈퍼바이저 실행
            print(f"🎯 Korean Podcast Production Pipeline 시작... (Task ID: {task_id})")
            
            # 입력 메시지 저장 (모든 에이전트가 공유)
            initial_input = {
                "messages": [{"role": "user", "content": user_request}],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for chunk in supervisor.stream(
                {
                    "messages": [
                        {
                            "role": "user", 
                            "content": user_request
                        }
                    ]
                },
                subgraphs=True,
            ):
                # 각 에이전트의 결과를 배치에 추가
                if isinstance(chunk, tuple):
                    ns, update = chunk
                    if len(ns) > 0:  # 서브그래프 업데이트만 처리
                        
                        for node_name, node_update in update.items():
                            # 에이전트 실행 횟수 증가
                            agent_execution_count[node_name] = agent_execution_count.get(node_name, 0) + 1
                            execution_order = agent_execution_count[node_name]
                            
                            # 실행 시간 계산을 위한 시작 시간
                            start_time = datetime.utcnow()
                            
                            # 메시지를 JSON 직렬화 가능한 형태로 변환
                            try:
                                messages = convert_to_messages(node_update.get("messages", []))
                                serializable_messages = [_serialize_message(msg) for msg in messages]
                            except Exception as msg_error:
                                print(f"⚠️ 메시지 변환 실패: {msg_error}")
                                serializable_messages = []
                            
                            # 에이전트 결과 생성 (아직 DB에 저장하지 않음)
                            agent_result = AgentResult(
                                task_id=task_id,
                                agent_type=_get_agent_type(node_name),
                                agent_name=node_name,
                                execution_order=execution_order,
                                input_data=initial_input,  # 실제 입력 데이터
                                output_data={"messages": serializable_messages},  # JSON 직렬화 가능한 출력 데이터
                                status=TaskStatus.COMPLETED,
                                started_at=start_time,
                                completed_at=datetime.utcnow(),
                                execution_time=int((datetime.utcnow() - start_time).total_seconds())
                            )
                            
                            agent_results_batch.append(agent_result)
                            print(f"📊 {node_name} 완료 (실행 #{execution_order})")
                            
                            # 최종 메시지 수집
                            try:
                                messages = convert_to_messages(node_update["messages"])
                                final_messages.extend([_serialize_message(msg) for msg in messages])
                            except Exception as msg_error:
                                print(f"⚠️ 메시지 변환 실패: {msg_error}")
                else:
                    # 최종 결과 처리
                    for node_name, node_update in chunk.items():
                        try:
                            messages = convert_to_messages(node_update["messages"])
                            final_messages.extend([_serialize_message(msg) for msg in messages])
                        except Exception as msg_error:
                            print(f"⚠️ 최종 메시지 변환 실패: {msg_error}")
            
            # 배치로 모든 에이전트 결과 저장
            if agent_results_batch:
                db.add_all(agent_results_batch)
                print(f"💾 {len(agent_results_batch)}개 에이전트 결과 일괄 저장")
            
            # 멀티 에이전트 파이프라인의 최종 결과에서 원본 TTS 스크립트 추출
            print(f"🔍 멀티 에이전트 최종 결과에서 원본 TTS 스크립트 추출 중...")
            raw_final_script = _extract_raw_final_script(final_messages)
            
            # TTS 결과 저장 (스크립트만 저장, 음원은 아직 생성 안됨)
            tts_result_id = None
            if raw_final_script:
                tts_result_id = _save_tts_script(db, task_id, user_request, raw_final_script)
            
            # 최종 결과 저장
            final_result = {
                "messages": final_messages,
                "completed_at": datetime.utcnow().isoformat(),
                "total_agent_executions": len(agent_results_batch),
                "agent_execution_summary": agent_execution_count,
                "tts_script_available": bool(raw_final_script),
                "tts_result_id": tts_result_id
            }
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.final_result = final_result
            db.commit()
            
            print(f"✅ Task {task_id} completed successfully")
            print(f"📈 Agent executions: {agent_execution_count}")
            
            # TTS 스크립트가 있으면 음원 생성 작업 시작
            if tts_result_id:
                _start_tts_generation_task(tts_result_id)
            
            return {"status": "completed", "task_id": task_id, "tts_result_id": tts_result_id}
            
        except Exception as e:
            # 에러 발생 시 롤백 후 상태 업데이트
            try:
                db.rollback()
            except Exception:
                pass
            
            error_info = handle_task_error("Podcast Task", task_id, e)
            
            try:
                task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_message = f"{error_info['error_message']}\n\nTraceback:\n{error_info['error_traceback']}"
                    task.completed_at = datetime.utcnow()
                    db.commit()
            except Exception as db_error:
                print(f"⚠️ 데이터베이스 업데이트 실패: {db_error}")
            
            raise Exception(f"Task {task_id} failed: {error_info['error_message']}")


def _save_tts_script(db, task_id: int, user_request: str, raw_script: str) -> int:
    """TTS 스크립트를 데이터베이스에 저장하고 TTS 결과 ID를 반환합니다."""
    try:
        # 스크립트 정제
        cleaned_script = _clean_tts_script(raw_script)
        
        # TTS 결과 저장 (PENDING 상태로, 파일 경로는 나중에 설정)
        tts_result = TTSResult(
            task_id=task_id,
            user_request=user_request,
            script_content=cleaned_script,
            raw_script=raw_script,  # 원본 백업
            audio_file_path="",  # 나중에 설정
            audio_file_name="",  # 나중에 설정
            is_audio_generated="false",
            tts_status=TTSStatus.PENDING,  # 스크립트만 저장된 상태
            hls_status=HLSStatus.PENDING  # HLS 상태도 명시적으로 설정
        )
        
        db.add(tts_result)
        db.commit()  # TTS 결과 먼저 저장
        db.refresh(tts_result)  # ID 가져오기
        tts_result_id = tts_result.id
        
        # TTS ID가 있으므로 이제 MinIO 객체명 생성 가능
        object_name = _generate_audio_object_name(tts_result_id, task_id, user_request)
        
        # MinIO 객체명 업데이트 (파일 경로는 MinIO URL로 설정)
        tts_result.audio_file_path = f"minio://{os.getenv('MINIO_BUCKET_NAME', 'lgraph-audio')}/{object_name}"
        tts_result.audio_file_name = object_name
        db.commit()
        
        print(f"🎙️ TTS 스크립트 저장 완료 (ID: {tts_result_id})")
        print(f"   - 스크립트 길이: {len(cleaned_script)} 문자")
        print(f"   - 예정 MinIO 객체명: {object_name}")
        print(f"   - 파일명 형식: tts_id_주제_task_id.wav")
        
        return tts_result_id
        
    except Exception as tts_save_error:
        print(f"⚠️ TTS 결과 저장 실패: {tts_save_error}")
        return None


def _start_tts_generation_task(tts_result_id: int):
    """TTS 음원 생성 태스크를 시작합니다."""
    try:
        # 지연 import로 순환 참조 방지
        from .tts_tasks import generate_tts_audio
        
        # 비동기 음원 생성 작업 시작 (WAV 생성 후 자동으로 HLS 변환)
        generate_audio_task = generate_tts_audio.delay(tts_result_id)
        print(f"🎵 TTS 음원 생성 작업 시작됨 - TTS Result ID: {tts_result_id}, Celery Task ID: {generate_audio_task.id}")
    except Exception as tts_task_error:
        print(f"⚠️ TTS 음원 생성 작업 시작 실패: {tts_task_error}") 