# ✦ Spark — AI 長者陪伴機器人

**Spark** 是一個基於 AI 的雙語（繁體中文 / 英文）長者陪伴系統，專為在家中陪伴老人而設計。它具備即時語音辨識、零延遲語音填補、喚醒詞觸發，以及主動提醒（吃藥、喝水等）等功能，並提供 Web UI 讓家屬隨時透過手機或平板管理設定。

---

## 系統需求 (System Requirements)

| 項目 | 建議規格 |
|---|---|
| 作業系統 | Ubuntu 22.04 / Raspberry Pi OS (64-bit) |
| Python | 3.11 或 3.13 |
| RAM | 最低 4GB，建議 8GB |
| GPU | 選配（有 GPU 會加速 STT 與 TTS） |
| 麥克風 | 任何 USB 麥克風或 3.5mm 接孔麥克風 |
| 喇叭 | 任何 USB 喇叭或 3.5mm 喇叭 |

---

## 安裝步驟 (Installation)

### 1. 安裝 Ollama（本地 LLM）
```bash
curl -fsSL https://ollama.com/install.sh | sh
# 拉取建議的本地模型
ollama pull gemma4:e2b      # 主要對話模型 (推薦)
ollama pull moondream       # 視覺分析模型（看照片功能）
```

### 2. 複製專案並建立虛擬環境
```bash
git clone <your-repo-url> spark
cd spark

# 使用 uv（推薦）
pip install uv
uv venv
source .venv/bin/activate

# 或使用 venv
python -m venv .venv
source .venv/bin/activate
```

### 3. 安裝 Python 相依套件
```bash
pip install -r requirements.txt
```

### 4. 設定環境變數
```bash
cp .env.example .env
nano .env  # 或用任何文字編輯器
```

在 `.env` 中填入以下內容：
```env
# 選填：OpenRouter API 金鑰（使用雲端模式時需要）
OPENROUTER_APIKEY=sk-or-xxxxxxxxxxxxxxxxxx

# 選填：Hugging Face Token（避免匿名下載速率限制）
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxx
```

> **如何取得 API 金鑰：**
> - **OpenRouter**：前往 [openrouter.ai](https://openrouter.ai/settings/keys) 免費申請（提供免費額度）
> - **HuggingFace Token**：前往 [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) 申請

### 5. 下載 Piper TTS 語音模型
Spark 使用 **Piper TTS** 進行雙語語音合成。語音模型目錄應放在 `./models/`：

```bash
mkdir -p models
cd models

# 中文語音（必要）
wget https://huggingface.co/rhasspy/piper-voices/blob/main/zh/zh_CN/xiao_ya/medium/zh_CN-xiao_ya-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/blob/main/zh/zh_CN/xiao_ya/medium/zh_CN-xiao_ya-medium.onnx.json

# 英文語音（必要，用於混合語言）
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/models/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/models/en_US-lessac-medium.onnx.json

cd ..
```

### 6. 啟動系統
```bash
python main.py
```

首次啟動時，系統會自動：
1. 載入 faster-whisper 語音辨識模型
2. 預熱本地 Ollama 模型（約需 10-30 秒）
3. 載入雙語 Piper TTS
4. **合成並快取** 45 個語音填補詞（存至 `./audio_cache_data/`）
5. 啟動 Web UI 在 `http://localhost:8000`

> **第二次開機起**，語音快取將從硬碟直接讀取，啟動時間大幅縮短。

---

## 使用方式 (Usage)

### 主對話介面 — `http://localhost:8000/`

這是長者每天面對的畫面，設計上盡量簡潔。

| 元素 | 說明 |
|---|---|
| **小星的臉** | 動態表情動畫，反映系統狀態（待機 / 聆聽 / 思考 / 說話） |
| **對話記錄框** | 顯示長者說的話與小星的回應 |
| **Model 標籤** | 右上角顯示目前使用的模型（Local 或 Cloud） |
| **⚙️ 設定** | 點擊後前往設定頁面 |

**狀態說明：**

| 臉部動畫 | 狀態 | 說明 |
|---|---|---|
| 眨眼（正常） | IDLE | 等待喚醒詞 |
| 眼睛放大 | LISTENING | 正在聆聽長者說話 |
| 眼睛旋轉 | THINKING | AI 正在思考回應 |
| 嘴巴動 | SPEAKING | 正在說話中 |

**語音互動流程：**
1. 說出喚醒詞（預設：**「Hey Jarvis」** 或 **「小星」**）
2. 小星立刻回應「我在！」確認已聽到
3. 說出您想說的話（系統在 4 秒後自動結束錄音）
4. 小星先播放一段「思考中」的填補詞（如「嗯... 讓我想一下喔...」）
5. AI 回答播出

**對話功能範例：**
- 💬 **日常聊天**：「阿公今天心情怎麼樣？」
- 🔍 **查詢網路**：「現在的天氣怎麼樣？」
- 📸 **看照片**：「這張照片裡面有什麼？」
- 🏥 **健康關心**：「阿公，您今天有量血壓了嗎？」
- 🤔 **懷舊聊天**：「您年輕的時候在哪裡工作？」
- 🔄 **切換大腦**：「換成雲端大腦」（切換至 Cloud 模式）

---

### 設定介面 — `http://localhost:8000/config`

家屬可以在此頁面管理所有設定。

#### 🤖 核心模式切換
- **⚡ Local 邊緣運算**：使用機器上的 Ollama，無需網路，回應較快，隱私性高。
- **☁ Cloud 雲端大模型**：使用 OpenRouter 雲端模型，中文理解與推理能力更強。

#### 👤 稱呼設定
- **被照護者稱呼**：填入長者的稱呼（例如：`阿公`、`阿媽`、`王伯伯`）
- **機器人/家屬稱呼**：填入機器人代表的角色名（例如：`小星`、`阿忠`）

> 儲存後系統會自動在背景重新合成 45 個專屬語音，請稍候約 30 秒。

#### ⏰ 醫療級排程提醒

每一個提醒項目支援以下設定：

| 欄位 | 說明 | 範例 |
|---|---|---|
| **提醒內容** | 說出的提醒詞 | `阿公吃高血壓藥囉` |
| **觸發時段** | 多時段，逗號分隔 | `08:00, 13:00, 18:00` |
| **重複星期** | 勾選要觸發的星期幾 | 勾選一、三、五 |
| **開始日期** | 提醒生效的第一天（選填） | `2025-05-01` |
| **結束日期** | 提醒自動停止的日期（選填） | `2025-05-03`（3 天份處方箋）|

---

## 系統架構 (Architecture)

```
main.py                    ← 主程式，管理所有狀態機與 process
├── brain.py               ← AI 大腦：LLM 呼叫、意圖辨識、語言偵測、網路搜尋
├── tts.py                 ← 雙語 TTS 引擎（Piper，自動切換中/英語音）
├── stt.py                 ← 語音辨識（faster-whisper）
├── audio_cache.py         ← 零延遲語音快取系統（硬碟持久化）
├── memory.py              ← 對話記憶（ChromaDB 向量資料庫）
├── reminders_db.py        ← 提醒資料庫 (SQLite)
├── settings_manager.py    ← 設定讀寫 (settings.json)
├── state_machine.py       ← 狀態機（IDLE/LISTENING/THINKING/SPEAKING）
├── ui.py                  ← Web 後端（FastAPI + WebSocket）
├── config.py              ← 全域設定（模型選擇、API keys）
└── static/
    ├── index.html         ← 主對話介面
    └── config.html        ← 設定管理介面
```

### 意圖分類 (Intent Routing)
系統先用本地輕量模型將長者的語音分類為以下意圖之一：

| 意圖 | 說明 |
|---|---|
| `chat` | 一般日常對話 |
| `search_web` | 需要查詢網路資訊 |
| `take_photo` | 請機器人看照片（需攝影機） |
| `health_query` | 健康相關詢問或回報 |
| `reminiscence` | 回憶過去的往事 |
| `daily_checkin` | 日常生活確認（有沒有吃飯等） |
| `praise_affirmation` | 長者說了值得稱讚的事 |
| `emotional_support` | 長者情緒低落，需要安撫 |
| `emergency` | 緊急狀況（跌倒、不舒服）|
| `swap_model` | 切換 Local / Cloud 模型 |

---

## 模型建議 (Model Recommendations)

### 本地模型 (Ollama)
| 模型 | 說明 |
|---|---|
| `gemma4:e2b` | ⭐ 推薦，Google 最新，中文理解佳，速度快 |
| `llama3.2:3b` | 備用，穩定可靠 |

### 雲端模型 (OpenRouter — 免費)
| 模型 | 說明 |
|---|---|
| `mistralai/mistral-small-3.1-24b-instruct:free` | ⭐ 推薦，穩定，中文理解好 |
| `qwen/qwen3-30b-a3b:free` | 最強中文，但有時離線 |
| `deepseek/deepseek-r1-0528:free` | 最強推理，較慢 |
| ~~`google/gemma-3-4b-it:free`~~ | ❌ 不建議，不支援 System Prompt |

---

## 常見問題 (Troubleshooting)

**Q: 系統說「我不太確定該怎麼做」？**
A: 意圖辨識可能誤判。嘗試切換到 Cloud 模式，語意理解會更準確。

**Q: TTS 播放時有奇怪的警告訊息？**
A: 在 `.env` 中加入 `HF_TOKEN=your_token` 可消除此訊息。

**Q: 雲端模式出現 429 錯誤？**
A: 免費模型有每日使用上限（50 次/天）。嘗試切換到其他雲端模型或改用本地模式。

**Q: 每次重開機都要重新合成語音？**
A: 確認 `./audio_cache_data/` 目錄存在且有 `.pcm` 檔案。若「被照護者稱呼」更改過，會自動觸發重新合成。

**Q: 喚醒詞不靈敏？**
A: 確認麥克風音量正常，嘗試在安靜環境下說「Hey Jarvis」。

---

## 資料目錄說明

| 目錄/檔案 | 說明 |
|---|---|
| `./audio_cache_data/` | 快取的語音填補詞（`.pcm` 格式） |
| `./chroma_db/` | 對話記憶向量資料庫 |
| `./models/` | Piper TTS 語音模型（`.onnx` 檔）|
| `./reminders.db` | 提醒設定資料庫（SQLite） |
| `./settings.json` | 被照護者/家屬稱呼設定 |
| `./spark_memory.db` | STT 記憶記錄 |
| `./.env` | API 金鑰（**請勿提交至 Git！**） |

---

## License

MIT License — 歡迎自由使用與修改，並用愛守護您的家人。 ❤️
