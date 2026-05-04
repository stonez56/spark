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
            "我在！",
            f"{patient_name}，我在這喔！",
            "有聽到喔！",
            "馬上來！",
            "嗯，我在！",
        ],
        # ── Intent fillers (played while LLM is thinking) ──────────────────
        "chat": [
            f"{patient_name}，我來想想喔...",
            "好喔，收到！",
            "嗯... 讓我想一下喔...",
            "好的，沒問題！",
            "我在這，等我一下下喔...",
        ],
        "search_web": [
            "稍等我一下，我幫您上網查查...",
            "我來找找看最新的資料喔...",
            "這題問我就對了，我查一下喔...",
            "好喔，我馬上幫您上網問問看...",
            f"{patient_name}稍等喔，我正在查...",
        ],
        "take_photo": [
            "我來仔細看看...",
            "眼睛睜大看...",
            "嗯，我看到囉，讓我分析一下...",
            "稍等我一下，我看一下照片喔...",
            "好的，我來幫您看看這是什麼...",
        ],
        "health_query": [
            f"{patient_name}，我幫您查一下紀錄喔...",
            "好喔，關於您的健康資訊，我來看看...",
            "健康最重要了，稍等我一下喔...",
            "我來翻一下您之前的紀錄喔...",
            "收到，我正在查您的健康資料...",
        ],
        "reminiscence": [
            "哇，真的嗎...",
            "嗯嗯，後來呢？",
            "原來是這樣呀...",
            "聽起來好有意思喔...",
            "我都不知道耶，您多說一點...",
        ],
        "daily_checkin": [
            "收到！紀錄下來囉...",
            "好喔，小星知道啦！",
            "嗯嗯，聽起來很棒呢！",
            "哇，真不錯！",
            "好的好的，記在心裡了喔！",
        ],
        "praise_affirmation": [
            "哇塞！",
            "真厲害！",
            "太棒了吧！",
            "哎喲，給您拍拍手！",
            "好棒喔！",
        ],
        "emotional_support": [
            "乖啦，我在這裡陪您喔...",
            "秀秀喔，不要難過...",
            "沒事沒事，小星會一直陪著您的...",
            "給您一個大擁抱喔...",
            "別擔心，我一直都在喔...",
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
