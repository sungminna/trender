from celery import Celery
from datetime import datetime
import os
from sqlalchemy.orm import sessionmaker
from database import engine, PodcastTask, AgentResult, TaskStatus, AgentType, TTSResult, TTSStatus
from super_agent import supervisor
from langchain_core.messages import convert_to_messages
from tts import get_tts_generator
import json
import traceback

# Celery 앱 설정
celery_app = Celery(
    "lgraph",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["celery_app"]
)

# Celery 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분 제한
    task_soft_time_limit=25 * 60,  # 25분 소프트 제한
)

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """데이터베이스 세션 컨텍스트 매니저"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
            final_tts_script = ""  # 멀티 에이전트 최종 TTS 스크립트
            
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
            
            # 멀티 에이전트 파이프라인의 최종 결과에서 TTS 스크립트 추출
            print(f"🔍 멀티 에이전트 최종 결과에서 TTS 스크립트 추출 중...")
            final_tts_script = _extract_final_tts_script(final_messages)
            
            # TTS 결과 저장 (스크립트만 저장, 음원은 아직 생성 안됨)
            tts_result_id = None
            if final_tts_script:
                try:
                    # 스크립트 정제
                    cleaned_script = _clean_tts_script(final_tts_script)
                    
                    # 음원 파일 경로 생성
                    audio_file_path, audio_file_name = _generate_audio_file_path(task_id, user_request)
                    
                    # TTS 결과 저장 (PENDING 상태로)
                    tts_result = TTSResult(
                        task_id=task_id,
                        user_request=user_request,
                        script_content=cleaned_script,
                        raw_script=final_tts_script,  # 원본 백업
                        audio_file_path=audio_file_path,
                        audio_file_name=audio_file_name,
                        is_audio_generated="false",
                        tts_status=TTSStatus.PENDING  # 스크립트만 저장된 상태
                    )
                    
                    db.add(tts_result)
                    db.commit()  # TTS 결과 먼저 저장
                    db.refresh(tts_result)  # ID 가져오기
                    tts_result_id = tts_result.id
                    
                    print(f"🎙️ TTS 스크립트 저장 완료 (ID: {tts_result_id})")
                    print(f"   - 스크립트 길이: {len(cleaned_script)} 문자")
                    print(f"   - 예정 음원 파일: {audio_file_name}")
                    
                except Exception as tts_save_error:
                    print(f"⚠️ TTS 결과 저장 실패: {tts_save_error}")
            
            # 최종 결과 저장
            final_result = {
                "messages": final_messages,
                "completed_at": datetime.utcnow().isoformat(),
                "total_agent_executions": len(agent_results_batch),
                "agent_execution_summary": agent_execution_count,
                "tts_script_available": bool(final_tts_script),
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
                try:
                    # 비동기 음원 생성 작업 시작
                    generate_audio_task = generate_tts_audio.delay(tts_result_id)
                    print(f"🎵 TTS 음원 생성 작업 시작됨 - TTS Result ID: {tts_result_id}, Celery Task ID: {generate_audio_task.id}")
                except Exception as tts_task_error:
                    print(f"⚠️ TTS 음원 생성 작업 시작 실패: {tts_task_error}")
            
            return {"status": "completed", "task_id": task_id, "tts_result_id": tts_result_id}
            
        except Exception as e:
            # 에러 발생 시 롤백 후 상태 업데이트
            try:
                db.rollback()
            except Exception:
                pass
            
            error_message = str(e)
            error_traceback = traceback.format_exc()
            
            print(f"❌ Task {task_id} failed: {error_message}")
            print(f"Traceback: {error_traceback}")
            
            try:
                task = db.query(PodcastTask).filter(PodcastTask.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_message = f"{error_message}\n\nTraceback:\n{error_traceback}"
                    task.completed_at = datetime.utcnow()
                    db.commit()
            except Exception as db_error:
                print(f"⚠️ 데이터베이스 업데이트 실패: {db_error}")
            
            raise Exception(f"Task {task_id} failed: {error_message}")


def _serialize_message(message):
    """메시지 객체를 JSON 직렬화 가능한 dict로 변환합니다."""
    try:
        if hasattr(message, 'dict'):
            return message.dict()
        elif hasattr(message, 'model_dump'):
            return message.model_dump()
        elif isinstance(message, dict):
            return message
        else:
            # 기본적인 속성들을 추출
            return {
                "content": getattr(message, 'content', str(message)),
                "type": getattr(message, 'type', type(message).__name__),
                "role": getattr(message, 'role', 'unknown')
            }
    except Exception as e:
        print(f"⚠️ 메시지 직렬화 실패: {e}")
        return {
            "content": str(message),
            "type": "serialization_error",
            "error": str(e)
        }


def _clean_tts_script(script_content: str) -> str:
    """TTS 스크립트를 정제합니다."""
    if not script_content:
        return ""
    
    # [TTS_SCRIPT_COMPLETE] 제거
    cleaned = script_content.replace("[TTS_SCRIPT_COMPLETE]", "").strip()
    
    # 백슬래시 이스케이프 문자를 실제 문자로 변환
    cleaned = cleaned.replace("\\n", "\n")  # 개행문자
    cleaned = cleaned.replace("\\\"", "\"")  # 따옴표
    cleaned = cleaned.replace("\\t", "\t")  # 탭
    cleaned = cleaned.replace("\\r", "\r")  # 캐리지 리턴
    cleaned = cleaned.replace("\\\\", "\\")  # 백슬래시 자체
    
    return cleaned.strip()


def _extract_tts_script_from_messages(messages: list) -> str:
    """메시지 리스트에서 TTS 스크립트를 추출합니다."""
    script_parts = []
    
    for msg in messages:
        if isinstance(msg, dict):
            content = msg.get("content", "")
        else:
            content = getattr(msg, 'content', str(msg))
        
        if content and isinstance(content, str):
            script_parts.append(content)
    
    return "\n".join(script_parts)


def _extract_final_tts_script(final_messages: list) -> str:
    """supervisor agent의 가장 마지막 출력에서 TTS 스크립트를 추출합니다."""
    if not final_messages:
        return ""
    
    # 가장 마지막 메시지에서 스크립트 추출
    last_message = None
    for msg in reversed(final_messages):  # 뒤에서부터 검색
        if isinstance(msg, dict):
            content = msg.get("content", "")
        else:
            content = getattr(msg, 'content', str(msg))
        
        # 내용이 있고 충분히 긴 경우 (실제 스크립트로 판단)
        if content and isinstance(content, str) and len(content.strip()) > 50:
            last_message = content
            break
    
    if not last_message:
        print("⚠️ supervisor의 마지막 출력에서 유효한 스크립트를 찾을 수 없습니다.")
        return ""
    
    # 마지막 [TTS_SCRIPT_COMPLETE] 마커만 제거
    script_content = last_message.replace("[TTS_SCRIPT_COMPLETE]", "").strip()
    
    print(f"📝 supervisor 마지막 출력에서 TTS 스크립트 추출 완료:")
    print(f"   - 원본 메시지 길이: {len(last_message)} 문자")
    print(f"   - 정제된 스크립트 길이: {len(script_content)} 문자")
    print(f"   - 스크립트 미리보기: {script_content[:100]}...")
    
    return script_content


def _generate_audio_file_path(task_id: int, user_request: str) -> tuple:
    """음원 파일 경로와 파일명을 생성합니다."""
    # 사용자 요청에서 안전한 파일명 생성
    safe_request = "".join(c for c in user_request[:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_request = safe_request.replace(' ', '_')
    
    # 파일명 생성
    filename = f"podcast_task_{task_id}_{safe_request}.mp3"
    
    # 파일 저장 경로 (환경변수로 설정 가능)
    audio_base_dir = os.getenv("AUDIO_STORAGE_PATH", "/app/audio_files")
    file_path = os.path.join(audio_base_dir, filename)
    
    return file_path, filename


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
            print(f"   - 출력 파일: {tts_result.audio_file_name}")
            
            # 음원 파일 디렉토리 생성
            os.makedirs(os.path.dirname(tts_result.audio_file_path), exist_ok=True)
            
            # TTS 생성기 인스턴스 가져오기
            tts_generator = get_tts_generator()
            
            # 단일 화자 음성 생성 (기본 설정)
            generation_result = tts_generator.generate_single_speaker_audio(
                text=tts_result.script_content,
                output_path=tts_result.audio_file_path,
                voice_name="Kore"  # 한국어에 적합한 목소리
            )
            
            if generation_result["success"]:
                # 성공 시 데이터베이스 업데이트
                tts_result.is_audio_generated = "true"
                tts_result.tts_status = TTSStatus.COMPLETED
                tts_result.audio_generated_at = datetime.utcnow()
                
                # 파일 정보 업데이트
                file_info = generation_result["file_info"]
                tts_result.audio_file_size = file_info["file_size"]
                tts_result.audio_duration = file_info["duration"]
                
                db.commit()
                
                print(f"✅ TTS 음원 생성 완료!")
                print(f"   - 파일 경로: {tts_result.audio_file_path}")
                print(f"   - 파일 크기: {file_info['file_size']:,} bytes")
                print(f"   - 재생 시간: {file_info['duration']} 초")
                
                return {
                    "status": "completed", 
                    "tts_result_id": tts_result_id,
                    "audio_file_path": tts_result.audio_file_path,
                    "file_info": file_info
                }
            else:
                # 실패 시 에러 상태로 업데이트
                tts_result.tts_status = TTSStatus.FAILED
                tts_result.error_message = generation_result["error"]
                db.commit()
                
                raise Exception(generation_result["error"])
                
        except Exception as e:
            # 에러 발생 시 롤백 후 상태 업데이트
            try:
                db.rollback()
            except Exception:
                pass
            
            error_message = str(e)
            error_traceback = traceback.format_exc()
            
            print(f"❌ TTS 음원 생성 실패 (TTS Result ID: {tts_result_id}): {error_message}")
            print(f"Traceback: {error_traceback}")
            
            try:
                tts_result = db.query(TTSResult).filter(TTSResult.id == tts_result_id).first()
                if tts_result:
                    tts_result.tts_status = TTSStatus.FAILED
                    tts_result.error_message = f"{error_message}\n\nTraceback:\n{error_traceback}"
                    db.commit()
            except Exception as db_error:
                print(f"⚠️ 데이터베이스 업데이트 실패: {db_error}")
            
            raise Exception(f"TTS audio generation failed for {tts_result_id}: {error_message}")


def _get_agent_type(agent_name: str) -> AgentType:
    """에이전트 이름으로부터 AgentType을 반환합니다."""
    if "research" in agent_name.lower():
        return AgentType.RESEARCH
    elif "story" in agent_name.lower() or "narrative" in agent_name.lower():
        return AgentType.STORY_NARRATIVE
    elif "tts" in agent_name.lower():
        return AgentType.TTS
    else:
        return AgentType.SUPERVISOR


if __name__ == "__main__":
    # Celery worker 실행: celery -A celery_app worker --loglevel=info
    pass 