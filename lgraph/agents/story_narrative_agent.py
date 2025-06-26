from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool

from utils.prompt_loader import get_prompt, prompt_loader
from utils.message_formatter import stream_and_print

load_dotenv()


def create_story_narrative_agent():
    """
    Korean Story Narrative Agent 생성
    
    역할:
    - 리서치 결과를 바탕으로 한국어 팟캐스트 내러티브 구성
    - 청취자 친화적인 스토리텔링 구조 생성
    - 20분 분량의 매력적인 팟캐스트 스크립트 작성
    
    특징:
    - 별도 외부 도구 없이 언어 모델 기반 내러티브 생성
    - 한국어 팟캐스트 특성을 고려한 구성
    
    Returns:
        LangGraph ReactAgent instance
    """
    story_narrative_prompt = get_prompt("story_narrative_agent")
    
    # 슈퍼바이저 연동을 위한 완료 신호 추가
    enhanced_prompt = story_narrative_prompt + """
    
    IMPORTANT: 내러티브 작업 완료 후 반드시 응답 마지막에 '[NARRATIVE_COMPLETE]' 태그를 추가하세요.
    이는 슈퍼바이저가 다음 단계(TTS 최적화)로 진행할 수 있도록 하는 신호입니다.
    """
    
    return create_react_agent(
        model="openai:gpt-4.1-mini",
        tools=[],  # 내러티브 생성은 언어 모델만으로 처리
        prompt=enhanced_prompt,
        name="story_narrative_agent",
    )


def reload_story_narrative_agent():
    """
    Story Narrative Agent 프롬프트 재로드
    - 서비스 운영 중 프롬프트 업데이트 적용
    """
    global story_narrative_agent
    print("Reloading Korean story narrative agent with updated prompt...")
    story_narrative_agent = create_story_narrative_agent()
    print("Korean story narrative agent reloaded successfully!")
    return story_narrative_agent


def get_available_prompts():
    """사용 가능한 프롬프트 목록 반환"""
    return prompt_loader.list_available_prompts()


# Korean Podcast Story Narrative Agent 인스턴스 생성
story_narrative_agent = create_story_narrative_agent()
