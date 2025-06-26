"""
Celery Tasks 공통 유틸리티 함수들
"""

from datetime import datetime
from sqlalchemy.orm import sessionmaker
from database import engine, AgentType
from langchain_core.messages import convert_to_messages
import traceback

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """데이터베이스 세션 컨텍스트 매니저"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


def _extract_raw_final_script(final_messages: list) -> str:
    """supervisor agent의 가장 마지막 출력에서 원본(raw) 스크립트를 추출합니다."""
    if not final_messages:
        return ""
    
    # 가장 마지막 메시지에서 스크립트 추출
    last_message_content = ""
    for msg in reversed(final_messages):  # 뒤에서부터 검색
        if isinstance(msg, dict):
            content = msg.get("content", "")
        else:
            content = getattr(msg, 'content', str(msg))
        
        # 내용이 있고 충분히 긴 경우 (실제 스크립트로 판단)
        if content and isinstance(content, str) and len(content.strip()) > 50:
            last_message_content = content
            break
    
    if not last_message_content:
        print("⚠️ supervisor의 마지막 출력에서 유효한 스크립트를 찾을 수 없습니다.")
        return ""
    
    print(f"📝 supervisor 마지막 출력에서 원본 스크립트 추출 완료:")
    print(f"   - 원본 메시지 길이: {len(last_message_content)} 문자")
    print(f"   - 스크립트 미리보기: {last_message_content[:100]}...")
    
    return last_message_content


def _generate_audio_object_name(tts_id: int, task_id: int, user_request: str) -> str:
    """MinIO 객체명을 생성합니다. 형식: tts_id_주제_task_id.wav"""
    # 사용자 요청에서 안전한 파일명 생성 (주제 부분)
    safe_request = "".join(c for c in user_request[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_request = safe_request.replace(' ', '_')
    
    # 빈 문자열이면 기본값 설정
    if not safe_request:
        safe_request = "podcast"
    
    # 객체명 생성: tts_id_주제_task_id.wav
    object_name = f"{tts_id}_{safe_request}_{task_id}.wav"
    
    return object_name


def handle_task_error(task_name: str, task_id: int, error: Exception, db_session=None):
    """태스크 에러 처리 공통 함수"""
    error_message = str(error)
    error_traceback = traceback.format_exc()
    
    print(f"❌ {task_name} 실패 (ID: {task_id}): {error_message}")
    print(f"Traceback: {error_traceback}")
    
    return {
        "error_message": error_message,
        "error_traceback": error_traceback,
        "timestamp": datetime.utcnow().isoformat()
    } 