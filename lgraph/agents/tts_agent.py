from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool

from utils.prompt_loader import get_prompt, prompt_loader
from utils.message_formatter import stream_and_print

load_dotenv()


def create_tts_agent():
    """
    Korean Story TTS Optimization Agent 생성
    
    역할:
    - 내러티브 스크립트를 TTS 엔진에 최적화
    - 자연스러운 음성 합성을 위한 텍스트 전처리
    - 발음, 억양, 호흡 등을 고려한 스크립트 조정
    
    특징:
    - TTS 엔진 특성에 맞는 텍스트 포맷팅
    - 한국어 TTS 최적화 전문
    - 6,500-8,500자 분량의 스크립트 생성
    
    Returns:
        LangGraph ReactAgent instance
    """
    tts_prompt = get_prompt("tts_gemini_agent")
    
    # 슈퍼바이저 연동을 위한 완료 신호 추가
    enhanced_prompt = tts_prompt + """
    
    IMPORTANT: TTS 최적화 작업 완료 후 반드시 응답 마지막에 '[TTS_READY]' 태그를 추가하세요.
    이는 슈퍼바이저가 전체 팟캐스트 제작 프로세스가 완료되었음을 인식할 수 있도록 하는 신호입니다.
    """
    
    return create_react_agent(
        model="openai:gpt-4.1-mini",
        tools=[],  # TTS 최적화는 언어 모델만으로 처리
        prompt=enhanced_prompt,
        name="tts_agent",
    )


def reload_tts_agent():
    """
    TTS Agent 프롬프트 재로드
    - 서비스 운영 중 프롬프트 업데이트 적용
    """
    global tts_agent
    print("Reloading Korean TTS agent with updated prompt...")
    tts_agent = create_tts_agent()
    print("Korean TTS agent reloaded successfully!")
    return tts_agent


def get_available_prompts():
    """사용 가능한 프롬프트 목록 반환"""
    return prompt_loader.list_available_prompts()


# Korean Podcast TTS Agent 인스턴스 생성
tts_agent = create_tts_agent()
