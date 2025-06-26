from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool

from tools.search_tools import web_search, news_search, namu_search
from utils.prompt_loader import get_prompt, prompt_loader
from utils.message_formatter import stream_and_print

load_dotenv()


def create_research_agent():
    """Research Agent를 생성합니다. 프롬프트는 파일에서 동적으로 로드됩니다."""
    research_prompt = get_prompt("research_agent")
    
    # 슈퍼바이저 패턴에 맞게 프롬프트 수정
    enhanced_prompt = research_prompt + """
    
    IMPORTANT: 리서치 작업 완료 후 반드시 응답 마지막에 '[RESEARCH_COMPLETE]' 태그를 추가하세요.
    이는 슈퍼바이저가 다음 단계로 진행할 수 있도록 하는 신호입니다.
    """
    
    return create_react_agent(
        model="openai:gpt-4.1-mini",
        tools=[
            Tool.from_function(web_search, name="WebSearch",
                               description="General Web Search. Search the web for general information."),
            Tool.from_function(news_search, name="NewsSearch",
                               description="News Search. Search the web for the latest news."),
            Tool.from_function(namu_search, name="NamuSearch",
                               description="나무위키 Search. Search the web for the latest information. ")
        ],
        prompt=enhanced_prompt,
        name="research_agent",
    )


def reload_research_agent():
    """
    프롬프트를 다시 로드하여 Research Agent를 재생성합니다.
    서비스 운영 중 프롬프트 업데이트 시 호출하세요.
    """
    global research_agent
    print("Reloading research agent with updated prompt...")
    research_agent = create_research_agent()
    print("Research agent reloaded successfully!")
    return research_agent


def get_available_prompts():
    """사용 가능한 프롬프트 목록을 반환합니다."""
    return prompt_loader.list_available_prompts()


# Research Agent 인스턴스 생성
research_agent = create_research_agent()

# 테스트 실행
if __name__ == "__main__":
    stream_and_print(
        research_agent,
        [{"role": "user", "content": "이란 전쟁 중 미국의 역할"}]
    )