from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool

from utils.prompt_loader import get_prompt, prompt_loader
from utils.message_formatter import stream_and_print

load_dotenv()


def create_tts_agent():
    """Korean Story TTS Optimization Agent를 생성합니다. 프롬프트는 파일에서 동적으로 로드됩니다."""
    tts_prompt = get_prompt("tts_gemini_agent")
    
    # 슈퍼바이저 패턴에 맞게 프롬프트 수정
    enhanced_prompt = tts_prompt + """
    
    IMPORTANT: TTS 최적화 작업 완료 후 반드시 응답 마지막에 '[TTS_READY]' 태그를 추가하세요.
    이는 슈퍼바이저가 전체 팟캐스트 제작 프로세스가 완료되었음을 인식할 수 있도록 하는 신호입니다.
    """
    
    return create_react_agent(
        model="openai:gpt-4.1-mini",
        tools=[
            # 현재는 별도 도구 없음 - 내러티브 스크립트를 TTS에 최적화
        ],
        prompt=enhanced_prompt,
        name="tts_agent",
    )


def reload_tts_agent():
    """
    프롬프트를 다시 로드하여 Korean Podcast TTS Agent를 재생성합니다.
    서비스 운영 중 프롬프트 업데이트 시 호출하세요.
    """
    global tts_agent
    print("Reloading Korean TTS agent with updated prompt...")
    tts_agent = create_tts_agent()
    print("Korean TTS agent reloaded successfully!")
    return tts_agent


def get_available_prompts():
    """사용 가능한 프롬프트 목록을 반환합니다."""
    return prompt_loader.list_available_prompts()


# Korean Podcast TTS Agent 인스턴스 생성
tts_agent = create_tts_agent()
