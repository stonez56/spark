import os
import re
import numpy as np
import sherpa_onnx
from sherpa_onnx.online_recognizer import (
    OnlineModelConfig,
    OnlineTransducerModelConfig,
    OnlineRecognizerConfig,
    OnlineRecognizer
)
import prompts

class SparkSTT:
    def __init__(self, model_size=None):
        self.model_dir = "/home/user/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
        self.recognizer = self._load_model()
        self.stream = None
        
        # Load Breeze settings
        import settings_manager
        settings = settings_manager.load_settings()
        self.use_breeze_speech = settings.get("use_breeze_speech", False)

    def _load_model(self):
        print(f"[STT] Loading sherpa-onnx streaming model from {self.model_dir}...")
        return OnlineRecognizer.from_transducer(
            tokens=f"{self.model_dir}/tokens.txt",
            encoder=f"{self.model_dir}/encoder-epoch-99-avg-1.int8.onnx",
            decoder=f"{self.model_dir}/decoder-epoch-99-avg-1.int8.onnx",
            joiner=f"{self.model_dir}/joiner-epoch-99-avg-1.int8.onnx",
            num_threads=1,
            sample_rate=16000,
            feature_dim=80,
            enable_endpoint_detection=False,
            decoding_method="greedy_search",
            model_type="zipformer",
        )

    def reload_settings(self):
        """Reload settings dynamically from settings.json."""
        import settings_manager
        settings = settings_manager.load_settings()
        self.use_breeze_speech = settings.get("use_breeze_speech", False)
        print(f"[STT Settings] Reloaded. use_breeze_speech: {self.use_breeze_speech}")

    def transcribe_breeze(self, audio_data: np.ndarray, sample_rate=16000) -> str:
        """
        [Breeze ASR API Placeholder]
        In the future, this will connect to the Breeze ASR endpoint to transcribe
        Mandarin + English + Taiwanese Hokkien code-switched speech.
        """
        print("[Breeze ASR] Simulating Breeze ASR transcription for mixed language...")
        # Fallback to local Zipformer
        return self.transcribe(audio_data, sample_rate)

    def start_stream(self):
        """Initializes a new streaming ASR stream session."""
        self.stream = self.recognizer.create_stream()

    def process_chunk(self, audio_data: np.ndarray, sample_rate=16000):
        """Feeds a chunk of int16 audio data into the ASR stream and decodes it."""
        if self.stream is None:
            self.start_stream()
        
        # Convert int16 to float32 normalized to [-1.0, 1.0]
        audio_float32 = audio_data.astype(np.float32) / 32768.0
        self.stream.accept_waveform(sample_rate, audio_float32)
        
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

    def get_text(self) -> str:
        """Retrieves the current decoded text hypothesis from the stream."""
        if self.stream is None:
            return ""
        raw_text = self.recognizer.get_result_all(self.stream).text.strip()
        return self._clean_text(raw_text)

    def transcribe(self, audio_data: np.ndarray, sample_rate=16000, chat_history=None):
        """
        Offline compatibility method. Creates a temp stream, 
        transcribes the audio numpy array in one go, and cleans the output.
        """
        temp_stream = self.recognizer.create_stream()
        audio_float32 = audio_data.astype(np.float32) / 32768.0
        temp_stream.accept_waveform(sample_rate, audio_float32)
        
        while self.recognizer.is_ready(temp_stream):
            self.recognizer.decode_stream(temp_stream)
            
        raw_text = self.recognizer.get_result_all(temp_stream).text.strip()
        return self._clean_text(raw_text)

    def _clean_text(self, raw_text: str) -> str:
        if not raw_text:
            return ""

        # 雙重防線：透過大腦的簡繁轉換工具進行後處理轉換，確保 100% 繁體字形
        try:
            from brain import clean_traditional_chinese
            cleaned_text = clean_traditional_chinese(raw_text)
            
            # 清理前後無意義標點
            cleaned_text = cleaned_text.strip(" ，。,澎、！!？? \t\n")
            
            # 過濾單個無意義的英文字母與全形字母幻覺（如「Ｇ」、「G」、「A」等）
            cleaned_text = re.sub(r'\s*\b[gGaAbBcCdD]\b\s*', ' ', cleaned_text).strip()
            cleaned_text = re.sub(r'\s*[ＧＡＢＣＤｇａｂｃｄ]\s*', '', cleaned_text).strip()
            
            # 過濾語音中無意義的孤立全形「０」幻覺
            cleaned_text = re.sub(r'\s*(?<![\d\.．點点])[０](?![\s]*[\d\.．點点])\s*', '', cleaned_text).strip()

            # 過濾語音末尾的幻覺數字「４」或「4」
            cleaned_text = re.sub(r'(?<!\d)(?<![一二三四五六七八九十百分點時日月年])([4４])$', '', cleaned_text.strip()).strip()
            
            # 在地同音字糾錯：「元山」->「圓山」
            try:
                import location_manager
                loc = location_manager.get_location()
                city = loc.get("city", "")
                district = loc.get("district", "")
                if "台北" in city or "新北" in city or "士林" in district:
                    cleaned_text = re.sub(r"元山(?!家電|牌|電器|扇)", "圓山", cleaned_text)
            except Exception as e:
                print(f"Error correcting homophone: {e}")

            if getattr(self, 'use_breeze_speech', False):
                # Taiwanese localized input correction / homophone refinement
                corrections = {
                    r"安抓|安爪|按扎|阿抓|下爪": "按怎",
                    r"姆湯|木湯|母湯": "毋湯",
                    r"戴資|戴志|帶至|代幾|代機": "代誌",
                    r"拍謝|排泄|排誰": "歹勢",
                    r"踹貢|串共": "踹共",
                    r"甲八煤|加包妹|甲霸沒|呷霸沒": "食飽未",
                }
                for pattern, replacement in corrections.items():
                    cleaned_text = re.sub(pattern, replacement, cleaned_text)
                
            return cleaned_text
        except Exception:
            return raw_text
