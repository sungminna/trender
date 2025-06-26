import os
from pathlib import Path
from typing import Dict, Optional
import time


class PromptLoader:
    """
    동적 프롬프트 로딩 및 캐싱 시스템
    
    Features:
    - 파일 시스템 기반 프롬프트 관리 (prompts/*.md)
    - 파일 변경 감지를 통한 자동 리로드
    - 메모리 캐싱으로 성능 최적화
    - 운영 중 프롬프트 업데이트 지원
    
    Directory Structure:
    - prompts/research_agent.md
    - prompts/story_narrative_agent.md
    - prompts/tts_gemini_agent.md
    - prompts/super_agent.md
    """
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(__file__).parent.parent / prompts_dir
        self._cache: Dict[str, str] = {}
        self._file_timestamps: Dict[str, float] = {}
        
        # prompts 디렉토리 자동 생성
        self.prompts_dir.mkdir(exist_ok=True)
    
    def _get_file_path(self, prompt_name: str) -> Path:
        """프롬프트 파일 경로 생성 (.md 확장자 자동 추가)"""
        if not prompt_name.endswith('.md'):
            prompt_name += '.md'
        return self.prompts_dir / prompt_name
    
    def _should_reload(self, prompt_name: str) -> bool:
        """파일 변경 감지를 통한 리로드 필요성 판단"""
        file_path = self._get_file_path(prompt_name)
        
        if not file_path.exists():
            return False
            
        current_timestamp = os.path.getmtime(file_path)
        cached_timestamp = self._file_timestamps.get(prompt_name, 0)
        
        return current_timestamp > cached_timestamp
    
    def load_prompt(self, prompt_name: str, force_reload: bool = False) -> Optional[str]:
        """
        프롬프트 로딩 및 캐싱
        
        Args:
            prompt_name: 프롬프트 파일명 (확장자 제외)
            force_reload: 캐시 무시하고 강제 리로드
            
        Returns:
            프롬프트 내용 (파일이 없으면 None)
            
        Caching Strategy:
        - 파일 변경 시간 기반 자동 갱신
        - 메모리 캐시로 성능 최적화
        """
        file_path = self._get_file_path(prompt_name)
        
        if not file_path.exists():
            print(f"Warning: Prompt file '{file_path}' not found")
            return None
        
        # 캐시 유효성 검사
        if not force_reload and prompt_name in self._cache and not self._should_reload(prompt_name):
            return self._cache[prompt_name]
        
        try:
            # 파일 읽기 및 캐시 업데이트
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            self._cache[prompt_name] = content
            self._file_timestamps[prompt_name] = os.path.getmtime(file_path)
            
            print(f"Loaded prompt: {prompt_name}")
            return content
            
        except Exception as e:
            print(f"Error loading prompt '{prompt_name}': {e}")
            return None
    
    def reload_all(self):
        """모든 캐시된 프롬프트 강제 리로드"""
        for prompt_name in list(self._cache.keys()):
            self.load_prompt(prompt_name, force_reload=True)
    
    def list_available_prompts(self) -> list:
        """사용 가능한 프롬프트 파일 목록 반환"""
        if not self.prompts_dir.exists():
            return []
        
        return [f.stem for f in self.prompts_dir.glob("*.md")]


# 전역 인스턴스 (싱글톤 패턴)
prompt_loader = PromptLoader()


def get_prompt(prompt_name: str, force_reload: bool = False) -> str:
    """
    프롬프트 로딩 편의 함수
    
    Args:
        prompt_name: 프롬프트 파일명 (확장자 제외)
        force_reload: 캐시 무시하고 강제 리로드
        
    Returns:
        프롬프트 내용 (파일이 없으면 빈 문자열)
    """
    content = prompt_loader.load_prompt(prompt_name, force_reload)
    return content or "" 