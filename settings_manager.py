import json
import os

SETTINGS_FILE = 'settings.json'

def get_default_caregiver_name():
    try:
        from config import WAKE_WORD
        import os
        if WAKE_WORD.endswith(".onnx"):
            # Extract name without extension (e.g., '小白' from 'models/小白.onnx')
            return os.path.splitext(os.path.basename(WAKE_WORD))[0]
        return "Mimo"
    except Exception:
        return "Mimo"

DEFAULT_SETTINGS = {
    "patient_name": "主人",
    "caregiver_name": get_default_caregiver_name(),
    "speaking_speed": "normal",
    "dialogue_mode": "local",
    "routing_mode": "local",
    "offload_local_llm": True,
    "cloud_text_model": "openai/gpt-oss-120b:free",
    "cloud_use_reasoning": False,
    "search_rewrite_mode": "legacy"
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Merge with defaults to ensure keys exist
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception as e:
        print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
