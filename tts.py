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
        Translates common conversational English words to Traditional Chinese,
        while preserving technical brand names and acronyms.
        Synthesizes using a single voice model to ensure natural and continuous speech.
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

        # Print translation details if any substitutions were made
        if translated_text != text:
            print(f"[TTS Translation] Translated English words: '{text}' -> '{translated_text}'")

        # Determine which voice model to use for the entire text to maintain continuous speech.
        # If the text contains any Chinese characters, use Chinese voice for the entire string.
        if self._contains_chinese(translated_text):
            print(f"Synthesizing entire text using Chinese voice: '{translated_text}'")
            voice = self.voice_zh
        else:
            print(f"Synthesizing entire text using English voice: '{translated_text}'")
            voice = self.voice_en

        try:
            audio_stream = voice.synthesize(translated_text)
            return b"".join(a.audio_int16_bytes for a in audio_stream)
        except Exception as e:
            print(f"TTS Error: {e}")
            return b""
