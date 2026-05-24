# Spark — AI Companion Robot for Elderly

Critical context for OpenCode sessions in this repository.

## Running the System

```bash
python main.py
```

- First run: Loads faster-whisper, warms up Ollama, synthesizes 45 audio fillers (10-30s)
- Subsequent runs: Loads cached audio from `./audio_cache_data/` for faster startup

## LLM Modes

Edit `config.py` to switch:
- `LLM_MODE = "local"` (default) — uses Ollama (gemma3:1b + moondream)
- `LLM_MODE = "cloud"` — uses OpenRouter API (free tier: 50 req/day)

Recommended models in `config.py`:
- Local: `gemma3:1b`
- Cloud text: `mistralai/mistral-small-3.1-24b-instruct:free`
- Cloud vision: `qwen/qwen2.5-vl-72b-instruct:free`

## Architecture

```
main.py              # Entry point, audio orchestrator, reminder scheduler
├── brain.py         # LLM calls, intent routing, vision, translation
├── tts.py           # Piper TTS (bilingual)
├── stt.py           # faster-whisper (speech-to-text)
├── audio_cache.py  # Zero-latency filler audio cache
├── memory.py       # ChromaDB vector memory
├── state_machine.py # IDLE/LISTENING/THINKING/SPEAKING
└── ui.py           # FastAPI + WebSocket on port 8000
```

## Intent Routing

Always uses local Ollama for speed (`brain.py:276-293`). Classifies user input into:
- `chat`, `search_web`, `take_photo`, `swap_model`
- `emergency`, `health_query`, `daily_checkin`
- `reminiscence`, `praise_affirmation`, `emotional_support`

## Key Quirks

1. **Audio fillers**: Synthesized on first run, cached to `./audio_cache_data/` as `.pcm` files. Re-generated when `patient_name` changes
2. **Wake word**: Uses openwakeword (`alexa` model by default in `main.py:30`)
3. **Listening timeout**: Auto-stops after 4 seconds of audio (`main.py:138`)
4. **Cloud API limit**: 50 requests/day on free tier — tracked in `brain.py:16-59`
5. **Chinese date format**: Converted to ROC era in prompts (`brain.py:338`)

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