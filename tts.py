import wave
import io
import re
import numpy as np
from piper import PiperVoice

class SparkTTS:
    def __init__(self):
        print("Loading bilingual Piper TTS models...")
        #self.voice_zh = PiperVoice.load("models/zh_CN-huayan-medium.onnx")
        self.voice_zh = PiperVoice.load("models/zh_CN-xiao_ya-medium.onnx")
        self.voice_en = PiperVoice.load("models/en_US-lessac-medium.onnx")

    def _contains_chinese(self, text: str) -> bool:
        """
        Check if the text contains Chinese characters.
        """
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def synthesize(self, text: str) -> bytes:
        """
        Synthesizes text into 22050Hz PCM audio bytes.
        Dynamically mixes English and Chinese voices.
        """
        # Split text into English and non-English chunks.
        # This matches sequences of English words, spaces, and apostrophes.
        chunks = re.split(r"([a-zA-Z]+(?:[\s'][a-zA-Z]+)*)", text)
        
        audio_bytes = b""
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
                
            # If the chunk is purely English letters and spaces/apostrophes
            if re.fullmatch(r"[a-zA-Z\s']+", chunk):
                print(f"Synthesizing English segment: '{chunk}'")
                voice = self.voice_en
            else:
                print(f"Synthesizing Chinese/Punctuation segment: '{chunk}'")
                voice = self.voice_zh
                
            try:
                audio_stream = voice.synthesize(chunk)
                audio_bytes += b"".join(a.audio_int16_bytes for a in audio_stream)
            except Exception as e:
                print(f"TTS Error on chunk '{chunk}': {e}")
                
        return audio_bytes
