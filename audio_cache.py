import os
import json
import random
import numpy as np
import settings_manager

# ── Constants ─────────────────────────────────────────────────────────────────
CACHE_DIR  = os.path.join(os.path.dirname(__file__), "audio_cache_data")
META_PATH  = os.path.join(CACHE_DIR, "meta.json")
SAMPLE_RATE = 22050               # must match piper TTS output sample rate
SILENCE_PAD_SECS = 0.8           # natural "thinking" pause after filler
WAKE_SILENCE_SECS = 1.0          # pause after wake-ack before recording starts

_CACHE: dict[str, list[bytes]] = {}

# ── Filler text corpus ─────────────────────────────────────────────────────────

def _make_silence(seconds: float) -> bytes:
    """Return `seconds` worth of silent PCM (int16, mono)."""
    n_samples = int(SAMPLE_RATE * seconds)
    return np.zeros(n_samples, dtype=np.int16).tobytes()


def get_fillers(patient_name: str) -> dict[str, list[str]]:
    return {
        # ── Immediate wake-word acknowledgement (played before recording) ──
        "wake_word_ack": [
            "喵？找本喵有什麼事？",
            f"{patient_name}，本喵在聽喔！",
            "喵～叫本喵幹嘛？",
            "嗯？有事找本喵喵？",
            "找本喵做什麼喵？",
        ],
        # ── Intent fillers (played while LLM is thinking) ──────────────────
        "chat": [
            "讓本喵想想喵...",
            "哼，這題要本喵動腦筋呢...",
            "稍等喵，本喵正在思考...",
            "收到收到，等本喵一下喵...",
            "哼哼，本喵動腦中...",
        ],
        "search_web": [
            "本喵上網幫你查查喵...",
            "等等，本喵爬網頁去...",
            "稍等喵，本喵上網找找...",
            "本喵上網問問看喵...",
            f"{patient_name}稍等，本喵查找中...",
        ],
        "take_photo": [
            "本喵睜大貓眼看看喵...",
            "讓本喵仔細瞧瞧...",
            "喵，本喵看清楚了...",
            "本喵正用肉球鏡頭觀察中...",
            "好的好的，本喵來分析一下喵...",
        ],
        "health_query": [
            f"{patient_name}，本喵幫你查健康紀錄喵...",
            "健康最重要喵，本喵幫你查查...",
            "稍等喵，翻一下你以前的健康紀錄...",
            "收到，本喵正在查健康資料喵...",
            "讓本喵來翻查舊紀錄喵...",
        ],
        "reminiscence": [
            "哇，真的嗎喵...",
            "嗯嗯，後來呢？喵...",
            "原來是這樣呀喵...",
            "聽起來很有趣喵...",
            "本喵在聽喔喵...",
        ],
        "daily_checkin": [
            "本喵記在小本本上了喵！",
            "哼哼，本喵知道啦！",
            "聽起來很不錯喵！",
            "好的好的，本喵記在心裡喵！",
            "喵～本喵收到啦！",
        ],
        "praise_affirmation": [
            "哇塞！不愧是本喵的奴才！",
            "太棒了吧喵！",
            "厲害厲害，給奴才拍拍貓爪！",
            "哎喲，不愧是本喵看上的人類！",
            "做得太棒了喵！",
        ],
        "emotional_support": [
            "別難過喵，本喵大腿借你躺一下...",
            "給你一個暖呼呼的貓咪大抱抱...",
            "別擔心喵，本喵會一直陪著你的...",
            "秀秀喵，有本喵在不用怕...",
            "哼哼，本喵一直都在這陪你喵...",
        ],
        "pet_cat": [
            "呼嚕呼嚕...好舒服喵...",
            "喵嗚...奴才摸得真舒服...",
            "哼，特准你繼續摸本喵喵...",
            "再摸一下下，就一下下喔喵...",
            "呼嚕...本喵很滿意喵！",
        ],
        "temp_analysis": [
            "量體溫是吧？伸出你的手喵！",
            "讓本喵用粉紅肉球探探你的額頭...",
            "體溫量測中，乖乖別動喵！",
            "本喵正讀取你的靈魂溫度喵...",
            "別亂動，本喵量體溫中喵...",
        ],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pcm_path(intent: str, idx: int) -> str:
    return os.path.join(CACHE_DIR, f"{intent}_{idx}.pcm")


def _load_meta() -> dict:
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_meta(data: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _cache_is_valid(patient_name: str, fillers: dict) -> bool:
    """Return True if disk cache matches current settings and all files exist."""
    meta = _load_meta()
    if meta.get("patient_name") != patient_name:
        return False
    # Check every expected file exists
    for intent, phrases in fillers.items():
        for idx in range(len(phrases)):
            if not os.path.exists(_pcm_path(intent, idx)):
                return False
    return True


# ── Public API ────────────────────────────────────────────────────────────────

def initialize(tts):
    """
    Load filler audio cache from disk if valid; otherwise synthesise and persist.
    Wake-word ack phrases get NO silence pad.  All other fillers get SILENCE_PAD_SECS appended.
    """
    global _CACHE
    settings     = settings_manager.load_settings()
    patient_name = settings.get("patient_name", "阿公")
    fillers      = get_fillers(patient_name)

    silence_pad  = _make_silence(SILENCE_PAD_SECS)

    if _cache_is_valid(patient_name, fillers):
        # ── Fast path: load from disk ──────────────────────────────────────
        print("[AudioCache] Loading filler audios from disk cache...")
        new_cache: dict[str, list[bytes]] = {}
        for intent, phrases in fillers.items():
            new_cache[intent] = []
            for idx in range(len(phrases)):
                with open(_pcm_path(intent, idx), "rb") as f:
                    new_cache[intent].append(f.read())
        _CACHE = new_cache
        total = sum(len(v) for v in _CACHE.values())
        print(f"[AudioCache] Loaded {total} filler audios from cache.")
        return

    # ── Slow path: synthesise and save ────────────────────────────────────
    print("\n[AudioCache] Synthesizing filler audios (this may take a few seconds)...")
    os.makedirs(CACHE_DIR, exist_ok=True)
    new_cache = {}

    for intent, phrases in fillers.items():
        new_cache[intent] = []
        for idx, phrase in enumerate(phrases):
            audio_bytes = tts.synthesize(phrase)

            # Append silence pad to every intent EXCEPT wake-word ack
            if intent != "wake_word_ack":
                audio_bytes = audio_bytes + silence_pad

            # Persist to disk
            with open(_pcm_path(intent, idx), "wb") as f:
                f.write(audio_bytes)

            new_cache[intent].append(audio_bytes)

    _CACHE = new_cache
    _save_meta({"patient_name": patient_name})
    total = sum(len(v) for v in _CACHE.values())
    print(f"[AudioCache] Successfully cached {total} filler audios to disk.")


def regenerate(tts):
    """Force re-synthesis (called when settings change)."""
    # Invalidate meta so _cache_is_valid returns False
    _save_meta({})
    initialize(tts)


def get_random_filler(intent: str) -> bytes | None:
    """Return a random pre-synthesised PCM bytes blob for the given intent."""
    if intent in _CACHE and _CACHE[intent]:
        return random.choice(_CACHE[intent])
    return None
