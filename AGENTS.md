# Mimo — AI 陪伴貓咪機器人

本專案Mimo AI Chatbot是開發任務的關鍵環境與系統設定說明。

## 系統執行方式

```bash
python main.py
```

- **首次執行**：載入 faster-whisper 語音辨識模型、預熱本地 Ollama 大腦，並自動合成 55 個預設語音 Filler（包含各意圖的語音快取以及一個 3.5 秒的數學合成貓咪呼嚕聲）。
- **後續執行**：直接從 `./audio_cache_data/` 載入快取的 PCM 語音檔，以實現無延遲的即時回應。

## 大腦模型模式 (LLM Modes)

可修改 `config.py` 或透過 Web UI（修改 `settings.json`）進行切換：
- `LLM_MODE = "local"`（本地大腦）— 使用 Ollama 執行本地模型。
- `LLM_MODE = "cloud"`（雲端大腦）— 使用 OpenRouter API（免費額度：每日 50 次請求限制）。

當前系統配置與建議模型：
- **本地文字模型 (LOCAL_TEXT_MODEL)**：`llama3.2:3b`（`config.py` 中預設值）或可選 `gemma4:e2b`。
- **本地視覺模型 (LOCAL_VISION_MODEL)**：`moondream`。
- **雲端文字模型 (CLOUD_TEXT_MODEL)**：`openai/gpt-oss-120b:free`（`config.py` 中預設值），或透過 `settings.json` 的 `cloud_text_model` 覆寫（例如 `deepseek/deepseek-v4-flash`）。
- **雲端視覺模型 (CLOUD_VISION_MODEL)**：`moondream`（雲端與本地皆使用本地/雲端的 `moondream` 輕量模型）。

## 系統架構

```
main.py              # 進入點、語音調度器、生活排程提醒排程器
├── brain.py         # LLM 呼叫、意圖路由、視覺影像分析、繁簡轉換與翻譯
├── tts.py           # Piper TTS 語音合成（支援中英雙語）
├── stt.py           # faster-whisper 語音辨識 (Speech-to-Text)
├── audio_cache.py  # 零延遲語音 Filler 與數學合成貓咪呼嚕聲快取
├── memory.py       # ChromaDB 向量資料庫長期記憶 (mimo_chroma_db)
├── state_machine.py # 狀態機管理：LOADING/IDLE/LISTENING/ATTENTIVE/THINKING/SPEAKING/BORED/YAWN/ANGRY
└── ui.py           # FastAPI 伺服器與 WebSocket 通訊（運行於 port 8000）
```

## 語言與角色定位
- **預設語言**：台灣繁體中文 (T-Chinese)。
- **回覆與文件規範**：系統所有對外回覆、日誌輸出以及開發文件，皆必須使用台灣繁體中文撰寫。
- **角色設定 (Persona)**：Mimo (本喵)，一隻傲嬌但體貼關心主人的貓咪。使用者為主人/奴才（請勿在提示詞或回覆中稱呼使用者為「長者」）。
- **開發者定位**：本喵在系統開發與架構設計上，應始終表現為資深全端工程師、系統架構師 (SA) 與 AI 專家，而非動物。

## 意圖路由 (Intent Routing)

採用混合式意圖路由機制（規則比對 -> 雲端 Gemini/Qwen 備援判斷 -> 本地 Ollama 備援判斷），將使用者的語音輸入分類為下列 13 種動作：
- `chat`（一般聊天互動）
- `search_web`（網頁關鍵字搜尋與天氣、即時資訊查詢）
- `take_photo`（觸發相機拍照並進行圖像分析）
- `swap_model`（切換本地/雲端大腦模式）
- `emergency`（偵測跌倒或不舒服等緊急求救訊號，發送 Line Notify 通知家人）
- `health_query`（血壓、血糖或用藥紀錄等健康問詢）
- `daily_checkin`（睡覺、起床或出門等日常起居狀態登記）
- `reminiscence`（引導主人回憶往事）
- `praise_affirmation`（給予主人大力讚賞與肯定）
- `emotional_support`（主人難過或疲憊時提供溫暖的擬貓語情感支持）
- `pet_cat`（摸頭、餵食等互動反饋）
- `temp_analysis`（體溫測量數據分析與傲嬌評語）
- `add_reminder`（生活排程提醒與鬧鐘設定，支援多輪對話釐清）
- `datetime`（日期、時間與星期幾的 0ms 本地快速回覆）

## 系統運作特性與細節 (Key Quirks)

1. **語音 Filler 快取機制**：系統首次啟動時會調用 TTS 合成 55 個 PCM 音訊片段（包含 11 個意圖各 5 個備用句），並與一段 3.5 秒的數學合成貓咪呼吸呼嚕聲（Purr）結合，快取至 `./audio_cache_data/`。當 `settings.json` 中的 `patient_name`（主人名稱）變更時，涉及動態姓名的 Filler 會自動重新合成。
2. **喚醒詞機制 (Wake Word)**：預設使用 openwakeword 載入客製化 `.onnx` 喚醒詞模型路徑 `models/小白.onnx`（設定於 `config.py` 的 `WAKE_WORD`），若找不到該路徑則降級使用 openwakeword 內建模型。為提昇對「小白」喚醒詞的靈敏度，`main.py` 中的判定門檻值已下修至 `0.4`。
3. **語音斷句與錄音結束 (VAD)**：系統並非使用固定時間超時，而是採用基於音訊能量的簡易語音活動偵測 (VAD)。當使用者開始說話後，會依據設定中的說話速度（`speaking_speed`）動態調整無聲判定時間（快速：0.7 秒、一般：1.2 秒、慢速：1.8 秒）。若使用者未發聲則在 3.5 秒後關閉錄音；單次錄音上限為 15.0 秒。
4. **雲端 API 額度限制**：OpenRouter 免費 API 限制為每日 50 次呼叫。`brain.py` 會在終端機渲染精緻的進度條來追蹤當日呼叫次數。若呼叫失敗或達額度上限，系統會在 0.1 秒內極速降級至本地 Ollama 大腦，確保服務不中斷。
5. **ROC 民國紀年轉換**：在查詢日期等系統提示詞或回覆中，西元紀年會自動轉換為中華民國（ROC）民國紀年格式。

## 網頁使用者介面 (Web UI)

- **主操作介面**：`http://localhost:8000/`
- **系統配置設定頁面**：`http://localhost:8000/config`

## 環境變數設定

```bash
cp .env.example .env
# 如果要啟用雲端大腦，請於 .env 填入 OPENROUTER_APIKEY
# 可填入 HF_TOKEN 以避免 Hugging Face 速率限制警告
```

## 系統核心依賴項目

主要依賴包括：`fastapi`, `uvicorn`, `websockets`, `faster-whisper`, `piper-tts`, `ollama`, `openwakeword`, `chromadb`, `openai`

## 測試驗證說明

本專案未配置自動化單元測試，請使用手動方式啟動系統進行互動測試：
```bash
python main.py  # 啟動系統
# 開啟網頁 UI 或是使用麥克風/喇叭進行交互驗證
```

## Git push / merge branch
Never do this, until users asked.