import os
from pathlib import Path
from typing import Dict, Optional
import time


class PromptLoader:
    """
    프롬프트 파일을 동적으로 로드하고 관리하는 클래스
    운영 중에도 프롬프트 파일을 업데이트하면 자동으로 반영됩니다.
    """
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(__file__).parent.parent / prompts_dir
        self._cache: Dict[str, str] = {}
        self._file_timestamps: Dict[str, float] = {}
        
        # prompts 디렉토리가 없으면 생성
        self.prompts_dir.mkdir(exist_ok=True)
    
    def _get_file_path(self, prompt_name: str) -> Path:
        """프롬프트 파일 경로를 반환합니다."""
        # .md 확장자가 없으면 추가
        if not prompt_name.endswith('.md'):
            prompt_name += '.md'
        return self.prompts_dir / prompt_name
    
    def _should_reload(self, prompt_name: str) -> bool:
        """파일이 수정되었는지 확인합니다."""
        file_path = self._get_file_path(prompt_name)
        
        if not file_path.exists():
            return False
            
        current_timestamp = os.path.getmtime(file_path)
        cached_timestamp = self._file_timestamps.get(prompt_name, 0)
        
        return current_timestamp > cached_timestamp
    
    def load_prompt(self, prompt_name: str, force_reload: bool = False) -> Optional[str]:
        """
        프롬프트를 로드합니다.
        
        Args:
            prompt_name: 프롬프트 파일명 (확장자 제외)
            force_reload: 강제로 파일을 다시 읽을지 여부
            
        Returns:
            프롬프트 내용 또는 None (파일이 없는 경우)
        """
        file_path = self._get_file_path(prompt_name)
        
        if not file_path.exists():
            print(f"Warning: Prompt file '{file_path}' not found")
            return None
        
        # 캐시된 내용이 있고 파일이 수정되지 않았으면 캐시 반환
        if not force_reload and prompt_name in self._cache and not self._should_reload(prompt_name):
            return self._cache[prompt_name]
        
        try:
            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 캐시 업데이트
            self._cache[prompt_name] = content
            self._file_timestamps[prompt_name] = os.path.getmtime(file_path)
            
            print(f"Loaded prompt: {prompt_name}")
            return content
            
        except Exception as e:
            print(f"Error loading prompt '{prompt_name}': {e}")
            return None
    
    def reload_all(self):
        """모든 캐시된 프롬프트를 다시 로드합니다."""
        for prompt_name in list(self._cache.keys()):
            self.load_prompt(prompt_name, force_reload=True)
    
    def list_available_prompts(self) -> list:
        """사용 가능한 프롬프트 파일 목록을 반환합니다."""
        if not self.prompts_dir.exists():
            return []
        
        return [f.stem for f in self.prompts_dir.glob("*.md")]


# 전역 인스턴스
prompt_loader = PromptLoader()


def get_prompt(prompt_name: str, force_reload: bool = False) -> str:
    """
    프롬프트를 가져오는 편의 함수
    
    Args:
        prompt_name: 프롬프트 파일명 (확장자 제외)
        force_reload: 강제로 파일을 다시 읽을지 여부
        
    Returns:
        프롬프트 내용 (파일이 없으면 빈 문자열)
    """
    content = prompt_loader.load_prompt(prompt_name, force_reload)
    return content or "" 