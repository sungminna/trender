from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool
from langgraph.graph import StateGraph
import inspect

from tools.search_tools import web_search, news_search, namu_search
from utils.prompt_loader import get_prompt, prompt_loader
from utils.message_formatter import stream_and_print

load_dotenv()

# Patch StateGraph.add_node for older langgraph versions that don't accept the `input_schema` kwarg
_original_add_node = StateGraph.add_node  # type: ignore[attr-defined]
if "input_schema" not in inspect.signature(_original_add_node).parameters:
    def _add_node_compat(self, *args, **kwargs):  # type: ignore[override]
        # Silently drop the `input_schema` argument if present
        kwargs.pop("input_schema", None)
        return _original_add_node(self, *args, **kwargs)

    StateGraph.add_node = _add_node_compat  # type: ignore[assignment]

def create_research_agent():
    """
    Research Agent 생성
    
    역할:
    - 사용자 요청 주제에 대한 포괄적 정보 수집
    - 다양한 검색 도구를 활용한 신뢰성 있는 데이터 확보
    - 수집된 정보의 구조화 및 분석
    
    Tools:
    - WebSearch: 일반 웹 검색
    - NewsSearch: 최신 뉴스 검색  
    - NamuSearch: 나무위키 한국어 정보 검색
    
    Returns:
        LangGraph ReactAgent instance
    """
    research_prompt = get_prompt("research_agent")
    
    # 슈퍼바이저 연동을 위한 완료 신호 추가
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
    Research Agent 프롬프트 재로드
    - 서비스 운영 중 프롬프트 업데이트 적용
    """
    global research_agent
    print("Reloading research agent with updated prompt...")
    research_agent = create_research_agent()
    print("Research agent reloaded successfully!")
    return research_agent


def get_available_prompts():
    """사용 가능한 프롬프트 목록 반환"""
    return prompt_loader.list_available_prompts()


# Research Agent 인스턴스 생성
research_agent = create_research_agent()

if __name__ == "__main__":
    """테스트 실행"""
    stream_and_print(
        research_agent,
        [{"role": "user", "content": "이란 전쟁 중 미국의 역할"}]
    )