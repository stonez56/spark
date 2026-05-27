"""
Spark Configuration
===================
Switch between LOCAL (Ollama) and CLOUD (OpenRouter) LLM backends here.

LLM_MODE options:
  "local"  - Uses Ollama running locally (gemma3:1b, moondream)
  "cloud"  - Uses OpenRouter API with free cloud models

OpenRouter Free Tier Limits:
  - 50 requests/day  (increases to 1,000/day if you add $10+ credits)
  - 20 requests/minute
  - Failed requests still count toward the daily quota!
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────
# MAIN SWITCH: "local" or "cloud"
# ──────────────────────────────────────────
LLM_MODE = "local"

# ──────────────────────────────────────────
# LOCAL (Ollama) settings
# ──────────────────────────────────────────
LOCAL_TEXT_MODEL   = "llama3.2:3b"
#LOCAL_TEXT_MODEL   = "gemma4:e2b"
LOCAL_VISION_MODEL = "moondream"

# ──────────────────────────────────────────
# CLOUD (OpenRouter) settings
# ──────────────────────────────────────────
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_APIKEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")

# ── Cloud TEXT & VISION models (using OpenRouter API) ──────────────────
CLOUD_TEXT_MODEL   = "deepseek/deepseek-v4-flash"
CLOUD_VISION_MODEL = "moondream"
