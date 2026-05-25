# Mimo — AI Companion Robot (Tsundere Cat)

Critical context for OpenCode sessions in this repository. 
Note: The project was formerly known as "Spark" (an elderly care robot) but has been officially refactored into "Mimo" (an arrogant, tsundere, but caring AI cat for the owner/奴才).

## Running the System

```bash
python main.py
```

- First run: Loads faster-whisper, warms up Ollama, synthesizes 45 audio fillers (10-30s)
- Subsequent runs: Loads cached audio from `./audio_cache_data/` for faster startup

## LLM Modes

Edit `config.py` to switch:
- `LLM_MODE = "local"` (default) — uses Ollama (gemma3:1b / llama3.2:3b + moondream)
- `LLM_MODE = "cloud"` — uses OpenRouter API (free tier: 50 req/day)

Recommended models in `config.py`:
- Local: `gemma3:1b`
- Cloud text: `qwen/qwen3-next-80b-a3b-instruct:free` (per MimoPRD for optimal T-Chinese)
- Cloud vision: `qwen/qwen2.5-vl-72b-instruct:free`

## Architecture

```
main.py              # Entry point, audio orchestrator, reminder scheduler
├── brain.py         # LLM calls, intent routing, vision, translation
├── tts.py           # Piper TTS (bilingual)
├── stt.py           # faster-whisper (speech-to-text)
├── audio_cache.py  # Zero-latency filler audio cache
├── memory.py       # ChromaDB vector memory (mimo_chroma_db)
├── state_machine.py # IDLE/LISTENING/THINKING/SPEAKING/PETTING/ANGRY
└── ui.py           # FastAPI + WebSocket on port 8000
```
## Language & Persona
- Default language is T-Chinese (台灣繁體中文)
- Always reply and provide text in T-Chinese.
- Persona: Mimo (本喵), an arrogant but caring cat. The user is the owner (主人/奴才). DO NOT refer to the user as "長者" (elderly).

## Intent Routing

Uses a Hybrid Intent Router (Rule-based -> Cloud Gemini/Qwen fallback -> Local Ollama fallback). Classifies user input into:
- `chat`, `search_web`, `take_photo`, `swap_model`
- `emergency`, `health_query`, `daily_checkin`
- `reminiscence`, `praise_affirmation`, `emotional_support`
- `pet_cat`, `temp_analysis`

## Key Quirks

1. **Audio fillers**: Synthesized on first run, cached to `./audio_cache_data/` as `.pcm` files. Re-generated when `owner_name` changes.
2. **Wake word**: Uses openwakeword (`alexa` model by default in `main.py:30`)
3. **Listening timeout**: Auto-stops after 4 seconds of audio (`main.py:138`)
4. **Cloud API limit**: 50 requests/day on free tier — tracked in `brain.py`
5. **Chinese date format**: Converted to ROC era in prompts (`brain.py`)

## Web UI

- Main: `http://localhost:8000/`
- Config: `http://localhost:8000/config`

## Environment Setup

```bash
cp .env.example .env
# Add OPENROUTER_APIKEY if using cloud mode
# Add HF_TOKEN to avoid rate limit warnings
```

## Dependencies

Core: `fastapi`, `uvicorn`, `websockets`, `faster-whisper`, `piper-tts`, `ollama`, `openwakeword`, `chromadb`, `openai`

## No Test Suite

This repo has no automated tests. Manual verification via:
```bash
python main.py  # Run system
# Interact via Web UI or microphone
```