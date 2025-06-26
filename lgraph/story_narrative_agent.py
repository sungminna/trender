from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool

from utils.prompt_loader import get_prompt, prompt_loader
from utils.message_formatter import stream_and_print

load_dotenv()


def create_story_narrative_agent():
    """Korean Story Narrative Agent를 생성합니다. 프롬프트는 파일에서 동적으로 로드됩니다."""
    story_narrative_prompt = get_prompt("story_narrative_agent")
    
    # 슈퍼바이저 패턴에 맞게 프롬프트 수정
    enhanced_prompt = story_narrative_prompt + """
    
    IMPORTANT: 내러티브 작업 완료 후 반드시 응답 마지막에 '[NARRATIVE_COMPLETE]' 태그를 추가하세요.
    이는 슈퍼바이저가 다음 단계(TTS 최적화)로 진행할 수 있도록 하는 신호입니다.
    """
    
    return create_react_agent(
        model="openai:gpt-4.1-mini",
        tools=[
            # 현재는 별도 도구 없음 - 리서치 결과를 바탕으로 한국어 팟캐스트 내러티브 생성
        ],
        prompt=enhanced_prompt,
        name="story_narrative_agent",
    )


def reload_story_narrative_agent():
    """
    프롬프트를 다시 로드하여 Korean Podcast Story Narrative Agent를 재생성합니다.
    서비스 운영 중 프롬프트 업데이트 시 호출하세요.
    """
    global story_narrative_agent
    print("Reloading Korean story narrative agent with updated prompt...")
    story_narrative_agent = create_story_narrative_agent()
    print("Korean story narrative agent reloaded successfully!")
    return story_narrative_agent


def get_available_prompts():
    """사용 가능한 프롬프트 목록을 반환합니다."""
    return prompt_loader.list_available_prompts()


# Korean Podcast Story Narrative Agent 인스턴스 생성
story_narrative_agent = create_story_narrative_agent()
