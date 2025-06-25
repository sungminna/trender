"""
프롬프트 관리 시스템 사용 예제

이 파일은 프롬프트를 동적으로 관리하는 방법을 보여줍니다.
서비스 운영 중에도 프롬프트를 업데이트하고 즉시 반영할 수 있습니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from super_agent import research_agent, reload_research_agent, get_available_prompts
from utils.prompt_loader import get_prompt, prompt_loader


def demonstrate_prompt_management():
    """프롬프트 관리 시스템 데모"""
    
    print("=== 프롬프트 관리 시스템 데모 ===\n")
    
    # 1. 사용 가능한 프롬프트 목록 조회
    print("1. 사용 가능한 프롬프트 목록:")
    available_prompts = get_available_prompts()
    for prompt in available_prompts:
        print(f"   - {prompt}")
    print()
    
    # 2. 특정 프롬프트 내용 확인
    print("2. research_agent 프롬프트 내용 (첫 200자):")
    prompt_content = get_prompt("research_agent")
    print(f"   {prompt_content[:200]}...")
    print()
    
    # 3. 프롬프트 강제 리로드
    print("3. 프롬프트 강제 리로드:")
    updated_prompt = get_prompt("research_agent", force_reload=True)
    print("   프롬프트가 리로드되었습니다.")
    print()
    
    # 4. 에이전트 리로드
    print("4. Research Agent 리로드:")
    reload_research_agent()
    print()
    
    # 5. 간단한 쿼리 테스트
    print("5. 업데이트된 에이전트로 간단한 테스트:")
    print("   (실제 쿼리는 주석 처리되어 있습니다)")
    # 실제 사용 시에는 아래 주석을 해제하세요
    # for chunk in research_agent.stream({"messages": [{"role": "user", "content": "안녕하세요"}]}):
    #     print(chunk)
    print()


def live_update_example():
    """실시간 업데이트 예제"""
    print("=== 실시간 프롬프트 업데이트 예제 ===")
    print()
    print("프롬프트 파일을 수정한 후 다음 함수들을 호출하세요:")
    print()
    print("1. 프롬프트 파일만 리로드:")
    print("   get_prompt('research_agent', force_reload=True)")
    print()
    print("2. 에이전트 전체 리로드:")
    print("   reload_research_agent()")
    print()
    print("3. 모든 프롬프트 리로드:")
    print("   prompt_loader.reload_all()")
    print()


def monitoring_example():
    """프롬프트 모니터링 예제"""
    print("=== 프롬프트 파일 모니터링 ===")
    print()
    
    # 프롬프트 파일들의 상태 확인
    prompts = get_available_prompts()
    for prompt_name in prompts:
        file_path = prompt_loader._get_file_path(prompt_name)
        if file_path.exists():
            mtime = os.path.getmtime(file_path)
            import datetime
            mod_time = datetime.datetime.fromtimestamp(mtime)
            print(f"   {prompt_name}: 최종 수정 시간 = {mod_time}")
        else:
            print(f"   {prompt_name}: 파일을 찾을 수 없음")
    print()


if __name__ == "__main__":
    demonstrate_prompt_management()
    live_update_example()
    monitoring_example()
    
    print("=== 사용법 요약 ===")
    print("1. prompts/ 폴더에 .md 파일로 프롬프트 저장")
    print("2. get_prompt('파일명') 으로 프롬프트 로드")
    print("3. 파일 수정 후 reload_research_agent() 호출하여 반영")
    print("4. 서비스 중단 없이 프롬프트 업데이트 가능!") 