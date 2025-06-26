"""
LGraph Multi-Agent System - Agents Package

Korean Podcast Production Multi-Agent Pipeline:

1. research_agent: 주제 관련 정보 수집 및 리서치
   - 웹 검색, 뉴스 검색, 나무위키 검색 도구 활용
   - 신뢰할 수 있는 정보 소스로부터 데이터 수집

2. story_narrative_agent: 팟캐스트 내러티브 구성
   - 리서치 결과를 기반으로 한국어 팟캐스트 스크립트 생성
   - 청취자 친화적인 스토리텔링 구조화

3. tts_agent: TTS 최적화 에이전트
   - 내러티브 스크립트를 TTS 엔진에 최적화
   - 자연스러운 음성 합성을 위한 텍스트 전처리

4. super_agent: 멀티 에이전트 슈퍼바이저
   - 전체 파이프라인 오케스트레이션
   - 에이전트 간 작업 순서 조정 및 결과 통합
"""

from .research_agent import create_research_agent, reload_research_agent, research_agent
from .story_agent import create_story_agent, reload_story_agent, story_agent
from .story_narrative_agent import create_story_narrative_agent, reload_story_narrative_agent, story_narrative_agent
from .tts_agent import create_tts_agent, reload_tts_agent, tts_agent
from .super_agent import supervisor

__all__ = [
    # Research Agent
    'create_research_agent',
    'reload_research_agent', 
    'research_agent',
    
    # Story Agent
    'create_story_agent',
    'reload_story_agent',
    'story_agent',
    
    # Story Narrative Agent
    'create_story_narrative_agent',
    'reload_story_narrative_agent',
    'story_narrative_agent',
    
    # TTS Agent
    'create_tts_agent', 
    'reload_tts_agent',
    'tts_agent',
    
    # Multi-Agent Supervisor
    'supervisor'
] 