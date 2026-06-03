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
        segments, info = self.model.transcribe(
            audio_float32, 
            beam_size=3,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt="幫我寫一封信，元智大學，元培科技大學，提醒我，搜尋，本喵，小白，微軟，訂閱費，寫信，拍照，設定鬧鐘，記得，中華民國，民國。以下是繁體中文的對話，使用台灣繁體字形，避免簡體字。"
        )
        
        text = ""
        for segment in segments:
            text += segment.text + " "
            
        raw_text = text.strip()
        
        # 雙重防線：透過大腦的簡繁轉換工具進行後處理轉換，確保 100% 繁體字形
        try:
            from brain import clean_traditional_chinese
            cleaned_text = clean_traditional_chinese(raw_text)
            
            # 過濾 Whisper 的 initial_prompt 幻覺
            hallucinations = [
                "以下是繁體中文的對話",
                "使用台灣繁體字形",
                "避免簡體字形",
                "避免簡體字",
                "避免簡體",
                "繁體中文的對話"
            ]
            for h in hallucinations:
                cleaned_text = cleaned_text.replace(h, "")
            
            # 清理因過濾殘留的標點符號與空白
            cleaned_text = cleaned_text.strip(" ，。,澎、！!？? \t\n")
            
            # 過濾語音末尾的幻覺數字「４」或「4」（非與其他數字相連、且非時間/日期後置詞時）
            import re
            cleaned_text = re.sub(r'(?<!\d)(?<![一二三四五六七八九十百分點時日月年])([4４])$', '', cleaned_text.strip()).strip()
            
            return cleaned_text
        except Exception:
            return raw_text

