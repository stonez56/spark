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
#LOCAL_TEXT_MODEL   = "llama3.2:3b"
LOCAL_TEXT_MODEL   = "gemma4:e2b"
LOCAL_VISION_MODEL = "moondream"

# ──────────────────────────────────────────
# CLOUD (OpenRouter) settings
# ──────────────────────────────────────────
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_APIKEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ── Cloud TEXT models (ranked by quality/latency for voice) ──────────────────
#
#   RECOMMENDED:
#   "qwen/qwen3-30b-a3b:free"                        - Qwen3 30B MoE ✓ FAST (~3B active), top multilingual/Chinese
#   "mistralai/mistral-small-3.1-24b-instruct:free"  - Mistral 24B ✓ excellent instruction following
#
#   GOOD:
#   "meta-llama/llama-3.1-8b-instruct:free"          - Llama 3.1 8B ✓ great balance
#   "meta-llama/llama-3.2-3b-instruct:free"          - Llama 3.2 3B ✓ fastest, basic quality
#
#   POWERFUL (higher latency ~2-4s):
#   "deepseek/deepseek-r1-0528:free"                 - DeepSeek R1 671B MoE ✓ best reasoning
#
#   AVOID (rejects system messages):
#   "google/gemma-3-4b-it:free"                      - Gemma 4B ✗
#
CLOUD_TEXT_MODEL = "mistralai/mistral-small-3.1-24b-instruct:free"

# ── Cloud VISION models ──────────────────────────────────────────────────────
#
#   "google/gemma-3-27b-it:free"                     - Gemma3 27B multimodal ✓ large & capable
#   "qwen/qwen2.5-vl-72b-instruct:free"              - Qwen2.5-VL 72B ✓ BEST free vision, top OCR & analysis
#   "meta-llama/llama-3.2-11b-vision-instruct:free"  - Llama 3.2 11B Vision ✓ solid, fast
#   "nvidia/llama-3.1-nemotron-nano-vl-8b-v1:free"   - Nemotron VL 8B ✓ video+doc intelligence
#
CLOUD_VISION_MODEL = "qwen/qwen2.5-vl-72b-instruct:free"
