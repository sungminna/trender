import os
import wave
import asyncio
from datetime import datetime
from typing import Optional, Tuple
from google import genai
from google.genai import types
from config import settings

class GeminiTTSGenerator:
    """Google Gemini TTS API를 사용한 음성 생성기"""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY is not configured in your .env file or environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash-preview-tts"
        
        # 기본 설정
        self.default_voice = "Kore"  # 한국어에 적합한 음성
        self.sample_rate = 24000
        self.channels = 1
        self.sample_width = 2
    
    def _save_wave_file(self, filename: str, pcm_data: bytes) -> dict:
        """PCM 데이터를 WAV 파일로 저장합니다."""
        try:
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.sample_width)
                wf.setframerate(self.sample_rate)
                wf.writeframes(pcm_data)
            
            # 파일 정보 반환
            file_size = os.path.getsize(filename)
            duration = len(pcm_data) // (self.sample_rate * self.channels * self.sample_width)
            
            return {
                "file_size": file_size,
                "duration": duration,
                "sample_rate": self.sample_rate,
                "channels": self.channels
            }
        except Exception as e:
            raise Exception(f"WAV 파일 저장 실패: {str(e)}")
    
    def generate_single_speaker_audio(
        self, 
        text: str, 
        output_path: str,
        voice_name: Optional[str] = None
    ) -> dict:
        """단일 화자 음성을 생성합니다."""
        try:
            voice = voice_name or self.default_voice
            
            print(f"🎙️ Gemini TTS 음성 생성 시작...")
            print(f"   - 모델: {self.model_name}")
            print(f"   - 음성: {voice}")
            print(f"   - 텍스트 길이: {len(text)} 문자")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice,
                            )
                        )
                    ),
                )
            )
            
            # 오디오 데이터 추출
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # WAV 파일로 저장
            file_info = self._save_wave_file(output_path, audio_data)
            
            print(f"✅ 음성 생성 완료: {output_path}")
            print(f"   - 파일 크기: {file_info['file_size']:,} bytes")
            print(f"   - 재생 시간: {file_info['duration']} 초")
            
            return {
                "success": True,
                "file_path": output_path,
                "file_info": file_info,
                "voice_used": voice,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Gemini TTS 음성 생성 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "file_path": output_path
            }
    
    def generate_multi_speaker_audio(
        self, 
        text: str, 
        output_path: str,
        speaker_configs: list
    ) -> dict:
        """다중 화자 음성을 생성합니다."""
        try:
            print(f"🎙️ Gemini TTS 다중 화자 음성 생성 시작...")
            print(f"   - 화자 수: {len(speaker_configs)}")
            
            # 화자 설정 구성
            speaker_voice_configs = []
            for config in speaker_configs:
                speaker_voice_configs.append(
                    types.SpeakerVoiceConfig(
                        speaker=config['speaker'],
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=config['voice_name'],
                            )
                        )
                    )
                )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                            speaker_voice_configs=speaker_voice_configs
                        )
                    )
                )
            )
            
            # 오디오 데이터 추출
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # WAV 파일로 저장
            file_info = self._save_wave_file(output_path, audio_data)
            
            print(f"✅ 다중 화자 음성 생성 완료: {output_path}")
            
            return {
                "success": True,
                "file_path": output_path,
                "file_info": file_info,
                "speakers_used": [config['speaker'] for config in speaker_configs],
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Gemini TTS 다중 화자 음성 생성 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "file_path": output_path
            }
    
    def get_available_voices(self) -> list:
        """사용 가능한 음성 목록을 반환합니다."""
        return [
            {"name": "Zephyr", "style": "Bright"},
            {"name": "Puck", "style": "Upbeat"},
            {"name": "Charon", "style": "Informative"},
            {"name": "Kore", "style": "Firm"},
            {"name": "Fenrir", "style": "Excitable"},
            {"name": "Leda", "style": "Youthful"},
            {"name": "Orus", "style": "Firm"},
            {"name": "Aoede", "style": "Breezy"},
            {"name": "Callirrhoe", "style": "Easy-going"},
            {"name": "Autonoe", "style": "Bright"},
            {"name": "Enceladus", "style": "Breathy"},
            {"name": "Iapetus", "style": "Clear"},
            {"name": "Umbriel", "style": "Easy-going"},
            {"name": "Algieba", "style": "Smooth"},
            {"name": "Despina", "style": "Smooth"},
            {"name": "Erinome", "style": "Clear"},
            {"name": "Algenib", "style": "Gravelly"},
            {"name": "Rasalgethi", "style": "Informative"},
            {"name": "Laomedeia", "style": "Upbeat"},
            {"name": "Achernar", "style": "Soft"},
            {"name": "Alnilam", "style": "Firm"},
            {"name": "Schedar", "style": "Even"},
            {"name": "Gacrux", "style": "Mature"},
            {"name": "Pulcherrima", "style": "Forward"},
            {"name": "Achird", "style": "Friendly"},
            {"name": "Zubenelgenubi", "style": "Casual"},
            {"name": "Vindemiatrix", "style": "Gentle"},
            {"name": "Sadachbia", "style": "Lively"},
            {"name": "Sadaltager", "style": "Knowledgeable"},
            {"name": "Sulafat", "style": "Warm"}
        ]


# 전역 인스턴스
tts_generator = None

def get_tts_generator() -> GeminiTTSGenerator:
    """TTS 생성기 인스턴스를 반환합니다."""
    global tts_generator
    if tts_generator is None:
        tts_generator = GeminiTTSGenerator()
    return tts_generator


if __name__ == "__main__":
    # 테스트 코드
    generator = get_tts_generator()
    
    test_text = "안녕하세요! 이것은 한국어 텍스트-투-스피치 테스트입니다."
    test_output = "/tmp/test_tts.wav"
    
    result = generator.generate_single_speaker_audio(test_text, test_output)
    print(f"테스트 결과: {result}") 