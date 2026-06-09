import numpy as np
from faster_whisper import WhisperModel
import prompts

class SparkSTT:
    def __init__(self, model_size="base"):
        print(f"Loading faster-whisper model '{model_size}'...")
        # compute_type="int8" is good for speed/memory on CPU
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def get_dynamic_prompt(self, chat_history=None):
        base_prompt = prompts.STT_BASE_PROMPT
        extra_keywords = []
        try:
            import location_manager
            loc = location_manager.get_location()
            city = loc.get("city", "")
            district = loc.get("district", "")
            
            if city:
                extra_keywords.append(city)
            if district:
                extra_keywords.append(district)
                
            # Localized landmarks based on Taiwan locations (especially Taipei/Shilin/Yuanshan area)
            if "台北" in city or "新北" in city or "士林" in district:
                extra_keywords.extend(["圓山", "圓山大飯店", "圓山捷運站", "士林夜市", "台北市", "新北市"])

            # Extract words from chat_history if provided
            if chat_history:
                import re
                stop_words = {
                    "這個", "那個", "什麼", "什麼是", "怎麼", "如何", "為何", "為什麼", "這樣", "那樣",
                    "本喵", "主人", "奴才", "你們", "我們", "他們", "自己", "一個", "一些", "一下", "一次",
                    "可以", "幫我", "需要", "不要", "不用", "可以嗎", "好嗎", "好的", "哼", "喵", "喵～",
                    "的", "了", "在", "是", "我", "你", "他", "她", "它", "們", "這", "那", "都", "不", "也"
                }
                for user_input, spark_response in chat_history:
                    for text in [user_input, spark_response]:
                        if text:
                            parts = re.split(r'[^\w\u4e00-\u9fff]+', text)
                            for p in parts:
                                p = p.strip()
                                if 2 <= len(p) <= 8 and p not in stop_words and re.match(r'^[\u4e00-\u9fff]+$', p):
                                    extra_keywords.append(p)

            # Fetch dynamically cached context keywords from SQLite
            try:
                from memory import MimoMemory
                memory = MimoMemory()
                cached_keywords = memory.get_context_keywords(limit=25)
                if cached_keywords:
                    extra_keywords.extend(cached_keywords)
            except Exception as e:
                print(f"Error fetching cached keywords for STT: {e}")
            
            # De-duplicate extra_keywords preserving order
            seen = set()
            unique_keywords = []
            for kw in extra_keywords:
                if kw not in seen:
                    seen.add(kw)
                    unique_keywords.append(kw)
            extra_keywords = unique_keywords[:30]
            
            if extra_keywords:
                location_prompt = "，".join(extra_keywords) + "。"
                return location_prompt + base_prompt, extra_keywords
        except Exception as e:
            print(f"Error generating dynamic prompt: {e}")
            
        return base_prompt, []

    def transcribe(self, audio_data: np.ndarray, sample_rate=16000, chat_history=None):
        """
        Transcribes numpy audio array. 
        faster-whisper expects float32 array in [-1.0, 1.0].
        """
        # Convert int16 to float32
        audio_float32 = audio_data.astype(np.float32) / 32768.0
        
        print("Transcribing audio...")
        dynamic_prompt, extra_keywords = self.get_dynamic_prompt(chat_history=chat_history)
        if extra_keywords:
            print(f"STT Dynamic Keywords injected: {extra_keywords}")
        
        segments, info = self.model.transcribe(
            audio_float32, 
            beam_size=3,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=dynamic_prompt
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
            
            # 過濾單個無意義的英文字母與全形字母幻覺（如「Ｇ」、「G」、「A」、「B」等，常見於停頓或呼吸處）
            cleaned_text = re.sub(r'\s*\b[gGaAbBcCdD]\b\s*', ' ', cleaned_text).strip()
            cleaned_text = re.sub(r'\s*[ＧＡＢＣＤｇａｂｃｄ]\s*', '', cleaned_text).strip()
            
            # 過濾語音中無意義的孤立全形「０」幻覺（例如詞間停頓被 Whisper 誤判的全形零，排除小數與數字相連情況，安全保留半形0）
            import re
            cleaned_text = re.sub(r'\s*(?<![\d\.．點点])[０](?![\s]*[\d\.．點点])\s*', '', cleaned_text).strip()

            # 過濾語音末尾的幻覺數字「４」或「4」（非與其他數字相連、且非時間/日期後置詞時）
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
                
            return cleaned_text
        except Exception:
            return raw_text
