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

    def _convert_numbers_to_zh(self, text: str) -> str:
        """
        Converts all sequences of Arabic numerals in the text to Traditional Chinese spoken words.
        E.g. '5TB' -> '五TB', '50' -> '五十', '2026' -> '二千零二十六'
        """
        def num_to_zh(num_str: str) -> str:
            if len(num_str) > 4:
                digits = {"0":"零", "1":"一", "2":"二", "3":"三", "4":"四", "5":"五", "6":"六", "7":"七", "8":"八", "9":"九"}
                return "".join(digits[c] for c in num_str)
            
            val = int(num_str)
            if val == 0:
                return "零"
                
            units = ["", "十", "百", "千"]
            digits = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
            
            if 10 <= val < 20:
                if val == 10:
                    return "十"
                return "十" + digits[val % 10]
                
            res = ""
            temp = val
            unit_idx = 0
            while temp > 0:
                d = temp % 10
                if d > 0:
                    res = digits[d] + units[unit_idx] + res
                elif d == 0 and res and not res.startswith("零"):
                    res = "零" + res
                temp //= 10
                unit_idx += 1
            return res.rstrip("零")

        def replace_match(match):
            return num_to_zh(match.group(0))

        return re.sub(r'\d+', replace_match, text)

    def synthesize(self, text: str) -> bytes:
        """
        Synthesizes text into 22050Hz PCM audio bytes.
        Translates common conversational English words to Traditional Chinese,
        while preserving technical brand names and acronyms.
        Synthesizes using bilingual Piper TTS voices (xiao_ya and lessac)
        with smooth transitions, number conversion, and trailing punctuation.
        """
        # Dictionary of common conversational English words to translate to Traditional Chinese
        ENG_TO_ZH = {
            "comfortable": "舒服",
            "owner": "主人",
            "happy": "快樂",
            "sad": "難過",
            "yes": "是的",
            "no": "不是",
            "ok": "好的",
            "okay": "好的",
            "hello": "你好",
            "sorry": "抱歉",
            "thank you": "謝謝",
            "thanks": "謝謝",
            "cat": "貓咪",
            "dog": "狗狗",
            "friend": "朋友",
            "love": "愛",
            "family": "家人",
            "good": "好",
            "morning": "早上好",
            "night": "晚安",
            "sleep": "睡覺",
            "food": "食物",
            "water": "水",
            "eat": "吃",
            "drink": "喝",
            "play": "玩",
            "tired": "累",
            "cold": "冷",
            "hot": "熱",
            "beautiful": "美麗",
            "cute": "可愛",
            "smart": "聰明",
            "silly": "傻瓜",
            "angry": "生氣",
            "hungry": "肚子餓",
        }

        # Apply translations for common English words (case-insensitive with word boundaries)
        translated_text = text
        for eng, zh in ENG_TO_ZH.items():
            pattern = re.compile(r'\b' + re.escape(eng) + r'\b', re.IGNORECASE)
            translated_text = pattern.sub(zh, translated_text)

        # Convert Arabic numerals to Traditional Chinese spoken characters to assist Chinese voice synthesis
        translated_text = self._convert_numbers_to_zh(translated_text)

        # Print translation details if any substitutions were made
        if translated_text != text:
            print(f"[TTS Translation] Preprocessed text: '{text}' -> '{translated_text}'")

        # ── 雙語混讀分段與合併處理引擎 (Bilingual Segmenter & Audio Concatenator) ──
        # 使用正則表達式切分出英文單字/品牌詞區塊（如 "Google AI Pro"、"ChatGPT Plus"、"TB"）
        pattern_split = re.compile(r'([a-zA-Z][a-zA-Z0-9\s\.\-\/\_\'\’]*[a-zA-Z0-9]|[a-zA-Z])')
        parts = pattern_split.split(translated_text)
        
        raw_segments = []
        for p in parts:
            if not p:
                continue
            is_en = bool(re.search(r'[a-zA-Z]', p))
            raw_segments.append((p, not is_en))
            
        # 合併同語系的相鄰分段以保持發音連貫流暢
        merged_segments = []
        for text_part, is_zh in raw_segments:
            if not merged_segments:
                merged_segments.append((text_part, is_zh))
            else:
                last_text, last_zh = merged_segments[-1]
                if last_zh == is_zh:
                    merged_segments[-1] = (last_text + text_part, is_zh)
                else:
                    merged_segments.append((text_part, is_zh))

        print(f"[TTS Bilingual Split] Merged segments: {merged_segments}")

        # 50ms of silence at 22050Hz, 16-bit mono
        # 22050 samples/sec * 0.05 sec = 1102 samples
        # 1102 samples * 2 bytes = 2204 bytes of zero
        silence_50ms = b'\x00' * 2204

        audio_segments = []
        for seg_text, is_chinese in merged_segments:
            clean_text = seg_text.strip()
            # Skip empty segments
            if not clean_text:
                continue
                
            voice = self.voice_zh if is_chinese else self.voice_en
            voice_name = "Chinese (xiao_ya)" if is_chinese else "English (lessac)"
            
            # Prepare text for synthesis
            if not is_chinese:
                # English segment: Append a trailing period if it doesn't end with standard punctuation
                # to prevent the Piper model from cutting off the final word abruptly.
                if clean_text and not clean_text[-1] in ".!?,;:。！，；：":
                    synth_text = clean_text + "."
                else:
                    synth_text = clean_text
            else:
                synth_text = clean_text
                
            print(f"[TTS Segment] Synthesizing '{synth_text}' using {voice_name} voice...")
            
            try:
                audio_stream = voice.synthesize(synth_text)
                segment_bytes = b"".join(a.audio_int16_bytes for a in audio_stream)
                
                # If there are already segments, append a 50ms silence block for smooth transition
                if audio_segments:
                    audio_segments.append(silence_50ms)
                    
                audio_segments.append(segment_bytes)
            except Exception as e:
                print(f"TTS Segment Error for '{synth_text}': {e}")

        if not audio_segments:
            return b""
            
        return b"".join(audio_segments)
