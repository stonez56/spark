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

def generate_authentic_cat_purr(duration_secs: float, sample_rate: int = 22050) -> bytes:
    """
    Mathematically synthesise a highly realistic, soothing, low-frequency cat purr/breathing sound.
    Uses amplitude modulation, laryngeal gating simulation, and low-pass filtered noise.
    """
    t = np.linspace(0, duration_secs, int(sample_rate * duration_secs), endpoint=False)
    
    # 1. Fundamental hum (Low frequency 26.2 Hz matching typical cat laryngeal oscillation)
    fundamental_freq = 26.2
    fundamental = np.sin(2 * np.pi * fundamental_freq * t)
    harmonic1 = 0.4 * np.sin(2 * np.pi * (fundamental_freq * 2) * t)
    harmonic2 = 0.15 * np.sin(2 * np.pi * (fundamental_freq * 3) * t)
    hum = fundamental + harmonic1 + harmonic2
    
    # 2. Laryngeal muscle gating modulation (26 Hz amplitude modulation / chatter tremolo)
    gating_mod = 0.5 * (1.0 + np.sin(2 * np.pi * 26.0 * t))
    purr_carrier = hum * gating_mod
    
    # 3. Soft, warm breathing airflow (low-pass filtered white noise)
    noise = np.random.normal(0, 0.1, len(t))
    # Simple low-pass filter (exponential moving average) to create deep brownian-like rumble
    alpha = 0.05
    filtered_noise = np.zeros_like(noise)
    current = 0.0
    for i in range(len(noise)):
        current = alpha * noise[i] + (1 - alpha) * current
        filtered_noise[i] = current
        
    # Combine purr carrier and warm air rumble
    raw_purr = purr_carrier + 0.12 * filtered_noise
    
    # 4. Respiration (Breathing) Cycle (Inhale/Exhale modulation at 0.3 Hz, ~3.3 sec per breath)
    breath_cycle = 0.3
    breath_envelope = 0.5 + 0.5 * np.sin(2 * np.pi * breath_cycle * t)
    
    # Apply breath envelope to purr
    purr_signal = raw_purr * breath_envelope
    
    # 5. Normalise and scale to comfortable, low-volume purring level (-12dB to -18dB)
    purr_signal = purr_signal / np.max(np.abs(purr_signal))
    purr_signal = purr_signal * 0.18  # Soft, intimate volume
    
    # Convert to 16-bit PCM
    pcm_data = (purr_signal * 32767).astype(np.int16)
    return pcm_data.tobytes()


def initialize(tts):
    """
    Load filler audio cache from disk granularly.
    Only synthesises and overwrites files that actually contain patient_name
    when the name changes. Static filler files are always preserved and reused.
    """
    global _CACHE, _PURR_PAD
    os.makedirs(CACHE_DIR, exist_ok=True)
    purr_fpath = os.path.join(CACHE_DIR, "purr_pad.pcm")
    
    # Self-healing: if cached purr pad is the old Piper TTS format (not matching our 154350 byte DSP size), delete it
    expected_size = 154350
    if os.path.exists(purr_fpath) and os.path.getsize(purr_fpath) != expected_size:
        print("[AudioCache] Overwriting obsolete human-voice purr file with premium natural DSP cat rumble.")
        try:
            os.remove(purr_fpath)
        except Exception:
            pass

    if os.path.exists(purr_fpath):
        print("[AudioCache] Loaded cached purring sound effect (呼嚕聲) from disk.")
        with open(purr_fpath, "rb") as f:
            _PURR_PAD = f.read()
    else:
        print("[AudioCache] Generating mathematically synthesised natural cat purring/breathing sound effect...")
        _PURR_PAD = generate_authentic_cat_purr(3.5)
        with open(purr_fpath, "wb") as f:
            f.write(_PURR_PAD)
        
    settings     = settings_manager.load_settings()
    patient_name = settings.get("patient_name", "主人")
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
