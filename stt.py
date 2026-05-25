import numpy as np
from faster_whisper import WhisperModel

class SparkSTT:
    def __init__(self, model_size="base"):
        print(f"Loading faster-whisper model '{model_size}'...")
        # compute_type="int8" is good for speed/memory on CPU
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_data: np.ndarray, sample_rate=16000):
        """
        Transcribes numpy audio array. 
        faster-whisper expects float32 array in [-1.0, 1.0].
        """
        # Convert int16 to float32
        audio_float32 = audio_data.astype(np.float32) / 32768.0
        
        print("Transcribing audio...")
        # 加上繁體 initial_prompt，強烈引導 Whisper 輸出台灣繁體中文
        segments, info = self.model.transcribe(
            audio_float32, 
            beam_size=5,
            initial_prompt="以下是繁體中文的對話，使用台灣繁體字形，避免簡體字。"
        )
        
        text = ""
        for segment in segments:
            text += segment.text + " "
            
        raw_text = text.strip()
        
        # 雙重防線：透過大腦的簡繁轉換工具進行後處理轉換，確保 100% 繁體字形
        try:
            from brain import clean_traditional_chinese
            cleaned_text = clean_traditional_chinese(raw_text)
            return cleaned_text
        except Exception:
            return raw_text
