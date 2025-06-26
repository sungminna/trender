from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain.chat_models import init_chat_model
from langchain_core.messages import convert_to_messages

from .research_agent import create_research_agent
from .story_narrative_agent import create_story_narrative_agent
from .tts_agent import create_tts_agent
from utils.prompt_loader import get_prompt, prompt_loader
from utils.message_formatter import stream_and_print

load_dotenv()


def pretty_print_message(message, indent=False):
    """메시지 출력 포맷팅 헬퍼 함수"""
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return

    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)


def pretty_print_messages(update, last_message=False):
    """에이전트 업데이트 메시지 출력 헬퍼 함수"""
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        # 부모 그래프 업데이트는 출력에서 제외
        if len(ns) == 0:
            return

        graph_id = ns[-1].split(":")[0]
        print(f"🔄 Update from subgraph {graph_id}:")
        print("\n")
        is_subgraph = True

    for node_name, node_update in update.items():
        update_label = f"📋 Update from node {node_name}:"
        if is_subgraph:
            update_label = "\t" + update_label

        print(update_label)
        print("\n")

        messages = convert_to_messages(node_update["messages"])
        if last_message:
            messages = messages[-1:]

        for m in messages:
            pretty_print_message(m, indent=is_subgraph)
        print("\n")


def create_podcast_supervisor():
    """
    한국어 팟캐스트 생성을 위한 멀티 에이전트 슈퍼바이저 생성
    
    Architecture:
    1. Research Agent: 주제 관련 정보 수집 및 분석
    2. Story Narrative Agent: 수집된 정보를 바탕으로 팟캐스트 스크립트 생성
    3. TTS Agent: 생성된 스크립트를 TTS에 최적화
    
    Returns:
        LangGraph supervisor instance
    """
    # 하위 에이전트 인스턴스 생성
    research_agent = create_research_agent()
    story_narrative_agent = create_story_narrative_agent()
    tts_agent = create_tts_agent()
    
    # 슈퍼바이저 프롬프트 동적 로드
    supervisor_prompt = get_prompt("super_agent")

    # 멀티 에이전트 슈퍼바이저 생성
    supervisor = create_supervisor(
        model=init_chat_model("openai:gpt-4.1-mini"),
        agents=[research_agent, story_narrative_agent, tts_agent],
        prompt=supervisor_prompt,
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    
    return supervisor


def reload_supervisor():
    """
    프롬프트 업데이트 시 슈퍼바이저 재로드
    - 하위 에이전트들도 함께 재로드됨
    - 서비스 운영 중 프롬프트 변경 적용을 위해 사용
    """
    global supervisor
    print("Reloading Korean podcast production supervisor with updated prompt...")
    supervisor = create_podcast_supervisor()
    print("Korean podcast production supervisor reloaded successfully!")
    return supervisor


def get_available_prompts():
    """사용 가능한 프롬프트 파일 목록 반환"""
    return prompt_loader.list_available_prompts()


# 슈퍼바이저 인스턴스 생성
supervisor = create_podcast_supervisor()


if __name__ == "__main__":
    """
    테스트 실행부
    - 샘플 요청으로 전체 파이프라인 테스트
    - 서브그래프 스트리밍으로 실시간 진행 상황 모니터링
    """
    test_request = """
    아이폰과 갤럭시의 기술적 비교
    """
    
    print("🎯 Korean Podcast Production Pipeline 시작...")
    print("=" * 20)
    
    try:
        for chunk in supervisor.stream(
            {
                "messages": [
                    {
                        "role": "user", 
                        "content": test_request
                    }
                ]
            },
            subgraphs=True,
        ):
            pretty_print_messages(chunk, last_message=True)
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {str(e)}")
        print("기본 실행 모드로 전환...")
        
        result = supervisor.invoke({
            "messages": [{"role": "user", "content": test_request}]
        })
        print("✅ 실행 완료:")
        print(result)

"""Korean Story Podcast Production Supervisor Agent.
Coordinates Research → Narrative → TTS agents to deliver a 20-minute, TTS-ready Korean script.
Detects `[CALL_RESEARCH:` signals and loops until `[TTS_READY]` script of 6 500-8 500 chars is produced."""