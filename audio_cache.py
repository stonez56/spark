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
            f"哇塞！不愧是本喵的{patient_name}！",
            "太棒了吧喵！",
            f"厲害厲害，給{patient_name}拍拍貓爪！",
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
            f"喵嗚...{patient_name}摸得真舒服...",
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


# ── Public API ────────────────────────────────────────────────────────────────

def initialize(tts):
    """
    Load filler audio cache from disk granularly.
    Only synthesises and overwrites files that actually contain patient_name
    when the name changes. Static filler files are always preserved and reused.
    """
    global _CACHE, _PURR_PAD
    if '_PURR_PAD' not in globals():
        _PURR_PAD = b''
    if not _PURR_PAD:
        print("[AudioCache] Generating purring sound effect (呼嚕聲)...")
        _PURR_PAD = tts.synthesize("呼嚕呼嚕... 呼嚕呼嚕... 呼嚕呼嚕... 呼嚕呼嚕...")
        
    settings     = settings_manager.load_settings()
    patient_name = settings.get("patient_name", "奴才")
    fillers      = get_fillers(patient_name)
    meta         = _load_meta()
    old_name     = meta.get("patient_name", "")
    name_changed = (old_name != patient_name)

    os.makedirs(CACHE_DIR, exist_ok=True)
    new_cache: dict[str, list[bytes]] = {}

    print(f"[AudioCache] Granular initializing fillers (Owner: '{patient_name}' | Name Changed: {name_changed})...")
    
    total_loaded = 0
    total_synthesized = 0

    for intent, phrases in fillers.items():
        new_cache[intent] = []
        for idx, phrase in enumerate(phrases):
            pcm_fpath = _pcm_path(intent, idx)
            
            # 判斷這句是否包含動態稱呼
            is_dynamic = (patient_name in phrase)
            
            # 決定是否重新合成該特定音訊檔：
            # 1. 該 pcm 檔在磁碟上不存在
            # 2. 或者：這是一個動態句子，且使用者姓名發生了變更
            need_synth = (not os.path.exists(pcm_fpath)) or (is_dynamic and name_changed)
            
            if need_synth:
                audio_bytes = tts.synthesize(phrase)
                if intent != "wake_word_ack":
                    audio_bytes = audio_bytes + _PURR_PAD
                with open(pcm_fpath, "wb") as f:
                    f.write(audio_bytes)
                new_cache[intent].append(audio_bytes)
                total_synthesized += 1
            else:
                with open(pcm_fpath, "rb") as f:
                    audio_bytes = f.read()
                new_cache[intent].append(audio_bytes)
                total_loaded += 1

    _CACHE = new_cache
    _save_meta({"patient_name": patient_name})
    print(f"[AudioCache] Loaded {total_loaded} static files, synthesized {total_synthesized} dynamic files.")


def regenerate(tts):
    """Force re-synthesis (called when settings change)."""
    initialize(tts)


def get_random_filler(intent: str) -> bytes | None:
    """Return a random pre-synthesised PCM bytes blob for the given intent."""
    if intent in _CACHE and _CACHE[intent]:
        return random.choice(_CACHE[intent])
    return None
