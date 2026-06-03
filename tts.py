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
        
        # Dictionary of common conversational English words to translate to Traditional Chinese
        self.eng_to_zh = {
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

    def _contains_chinese(self, text: str) -> bool:
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _split_into_sentences(self, text: str, is_chinese: bool) -> list:
        """
        Split a text block into short sentences for sentence-level streaming.
        Shorter inputs synthesize quadratically faster in Piper ONNX (critical for Pi5).
        
        Chinese: primary split at 。！？…；, secondary at ，、 for chunks > 35 chars.
        English: split at . ! ?
        """
        if is_chinese:
            # Primary split at strong sentence-ending punctuation (keep delimiter)
            primary_pattern = re.compile(r'(?<=[。！？…；])')
            chunks = primary_pattern.split(text)

            # Secondary split at commas for any chunks still > 35 chars
            result = []
            for chunk in chunks:
                if len(chunk) > 35:
                    sub_chunks = re.split(r'(?<=[，、])', chunk)
                    result.extend([c for c in sub_chunks if c.strip()])
                elif chunk.strip():
                    result.append(chunk)
        else:
            # English: split at sentence-ending punctuation
            chunks = re.split(r'(?<=[.!?])', text)
            result = [c for c in chunks if c.strip()]

        return [c.strip() for c in result if c.strip()]

    def _preprocess_text(self, text: str) -> str:
        """Apply eng->zh word substitution and number conversion."""
        translated = text
        for eng, zh in self.eng_to_zh.items():
            pattern = re.compile(r'\b' + re.escape(eng) + r'\b', re.IGNORECASE)
            translated = pattern.sub(zh, translated)
        translated = self._convert_numbers_to_zh(translated)
        if translated != text:
            print(f"[TTS Preprocess] '{text}' -> '{translated}'")
        return translated

    def _build_bilingual_segments(self, text: str) -> list:
        """
        Split text into (segment_text, is_chinese) tuples by language.
        Merges adjacent same-language segments for fluent bilingual synthesis.
        Returns: list of (text, is_chinese) tuples.
        """
        pattern_split = re.compile(r'([a-zA-Z][a-zA-Z0-9\s\.\-\/\_\'\']*[a-zA-Z0-9]|[a-zA-Z])')
        parts = pattern_split.split(text)

        raw_segments = []
        for p in parts:
            if not p:
                continue
            is_en = bool(re.search(r'[a-zA-Z]', p))
            raw_segments.append((p, not is_en))  # (text, is_chinese)

        merged = []
        for text_part, is_zh in raw_segments:
            if not merged:
                merged.append((text_part, is_zh))
            else:
                last_text, last_zh = merged[-1]
                if last_zh == is_zh:
                    merged[-1] = (last_text + text_part, is_zh)
                else:
                    merged.append((text_part, is_zh))
        return merged

    def _convert_numbers_to_zh(self, text: str) -> str:
        """
        Converts Arabic numerals to Traditional Chinese spoken words.
        E.g. '5TB' -> '五TB', '50' -> '五十', '2026' -> '二千零二十六'
        Time format HH:MM converted to natural speech (07:00 -> 七點).
        """
        def time_replace(match):
            hour = int(match.group(1))
            minute = int(match.group(2))
            hour_zh = "12" if hour == 0 else str(hour)
            if minute == 0:
                return f"{hour_zh}點"
            elif minute == 30:
                return f"{hour_zh}點半"
            else:
                return f"{hour_zh}點{minute}分"

        text = re.sub(r'(\d{1,2}):(\d{2})', time_replace, text)

        def num_to_zh(num_str: str) -> str:
            if len(num_str) > 4:
                digits = {"0":"零","1":"一","2":"二","3":"三","4":"四","5":"五","6":"六","7":"七","8":"八","9":"九"}
                return "".join(digits[c] for c in num_str)
            val = int(num_str)
            if val == 0:
                return "零"
            units = ["", "十", "百", "千"]
            digits = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
            if 10 <= val < 20:
                return "十" if val == 10 else "十" + digits[val % 10]
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

        return re.sub(r'\d+', lambda m: num_to_zh(m.group(0)), text)

    def synthesize(self, text: str) -> bytes:
        """
        Synthesizes text into 22050Hz PCM audio bytes (blocking, full buffer).
        Used by audio_cache for pre-caching filler sounds.
        For real-time response playback, use synthesize_stream() instead.
        """
        translated_text = self._preprocess_text(text)
        segments = self._build_bilingual_segments(translated_text)
        print(f"[TTS Bilingual Split] Merged segments: {segments}")

        silence_50ms = b'\x00' * 2204  # 50ms at 22050Hz 16-bit mono
        audio_segments = []

        for seg_text, is_chinese in segments:
            clean_text = seg_text.strip()
            if not clean_text:
                continue

            voice = self.voice_zh if is_chinese else self.voice_en
            voice_name = "Chinese (xiao_ya)" if is_chinese else "English (lessac)"

            # English: trailing period prevents Piper clipping last word
            if not is_chinese and clean_text[-1] not in ".!?,;:。！，；：":
                synth_text = clean_text + "."
            else:
                synth_text = clean_text

            print(f"[TTS Segment] Synthesizing '{synth_text}' using {voice_name} voice...")
            try:
                audio_stream = voice.synthesize(synth_text)
                segment_bytes = b"".join(a.audio_int16_bytes for a in audio_stream)
                if audio_segments:
                    audio_segments.append(silence_50ms)
                audio_segments.append(segment_bytes)
            except Exception as e:
                print(f"TTS Segment Error for '{synth_text}': {e}")

        if not audio_segments:
            return b""
        return b"".join(audio_segments)

    def synthesize_stream(self, text: str):
        """
        Sentence-level streaming TTS synthesizer (generator).

        Architecture: Split response into sentences BEFORE synthesis.
        Yields PCM audio chunks as each sentence completes, so playback begins
        after the first sentence (~2s) rather than waiting for all text (~36s).

        Pi5 compatibility: Piper ONNX synthesis time scales with input length.
        Sentence-level splitting reduces per-call latency from 36s to ~2-5s,
        making the system viable on both Intel i5 (dev) and Raspberry Pi 5 (prod).
        """
        # ── Step 1: Preprocess ──────────────────────────────────────────────
        translated_text = self._preprocess_text(text)

        # ── Step 2: Language detection & bilingual blocking ─────────────────
        lang_blocks = self._build_bilingual_segments(translated_text)
        print(f"[TTS Lang Blocks] {[(t[:20]+'...' if len(t)>20 else t, 'zh' if zh else 'en') for t, zh in lang_blocks]}")

        # ── Step 3: Sentence-level split for progressive streaming ───────────
        # Each lang block is split into short sentences (≤35 chars for Chinese).
        # This is the core latency optimization for Pi5.
        sentence_queue = []
        for lang_text, is_zh in lang_blocks:
            for sentence in self._split_into_sentences(lang_text, is_zh):
                sentence_queue.append((sentence, is_zh))

        print(f"[TTS Sentences] {len(sentence_queue)} chunks: {[s[:12]+'...' if len(s)>12 else s for s, _ in sentence_queue]}")

        # ── Step 4: Synthesize + yield each sentence progressively ──────────
        silence_50ms = b'\x00' * 2204  # 50ms gap between sentences
        first_chunk = True

        for seg_text, is_chinese in sentence_queue:
            clean_text = seg_text.strip()
            if not clean_text:
                continue

            voice = self.voice_zh if is_chinese else self.voice_en
            voice_name = "zh" if is_chinese else "en"

            # English: ensure trailing punctuation to prevent Piper clipping last word
            if not is_chinese and clean_text[-1] not in ".!?,;:。！，；：":
                synth_text = clean_text + "."
            else:
                synth_text = clean_text

            print(f"[TTS Sentence] [{voice_name}] '{synth_text}'")

            try:
                if not first_chunk:
                    yield silence_50ms
                first_chunk = False

                audio_stream = voice.synthesize(synth_text)
                sentence_bytes = b"".join(a.audio_int16_bytes for a in audio_stream)
                if sentence_bytes:
                    yield sentence_bytes
            except Exception as e:
                print(f"[TTS Sentence Error] '{synth_text}': {e}")
