"""
TTS (Text-to-Speech) 패키지

Google Gemini TTS API를 사용한 음성 생성 기능을 제공합니다.
"""

from .tts_gemini import GeminiTTSGenerator, get_tts_generator

__all__ = [
    "GeminiTTSGenerator",
    "get_tts_generator"
] 