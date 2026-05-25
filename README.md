# 🐈 Mimo — 溫感 AI 傲嬌貓咪助理 (Mimo AI Cat Assistant)

**Mimo** 是一個基於 AI 的雙語（繁體中文 / 英文）貓咪陪伴助理系統，專為日常陪伴與生活助理而設計。她具備台灣傲嬌貓咪的獨特個性（自稱「本喵」，稱呼您為「奴才」），支援即時語音辨識、零延遲語音填補（Filler Audio）、喚醒詞觸發、生活起居叮嚀，並提供了精緻的 midnight-indigo 深色玻璃擬態 Web UI 介面，讓奴才隨時能透過手機或平板進行「擼貓摸摸」與「貓掌量溫」等虛擬互動。

Mimo 更設計了專門為樹莓派 5 打造的實體外觀硬體擴充規格，包含 0.96" OLED 表情顯示、SG90 雙軸雲台頸部轉動、實體觸控感測器以及主動式 OpenCV 人臉追隨。

---

## 🚀 核心優勢與亮點 (Highlights)

* **🐱 傲嬌貓咪個性與台灣口癖**：徹底重塑大腦 System Prompt，每句限制在 20 字內，口氣活潑傲嬌，隨機帶有「喵～」、「哼」，問到時間日期會自動轉換為中華民國紀年（ROC era）。
* **⚡ 零延遲 Snappy 本地降級機制**：針對 OpenRouter 雲端免費 API 尖峰時間易發生 429 限流與 404 故障，大腦實作了**主動 transforms 停用**與**極速本地降級**：
  * 強制在 API 請求中傳入 `"transforms": []`，停用 OpenRouter 的慢速後台自動轉發。
  * 設定 `6.0` 秒嚴格超時，一旦雲端異常，**0.1 秒內無縫切換至本地 Ollama (`gemma3:1b`)**，語音 TTS 播放絕無卡頓，流暢度提升 300%！
* **🎨  midnight-indigo 玻璃擬態 UI**：主頁面包含精美 Aurora 霓虹光暈，動態 SVG 貓耳與貓鬚會隨著 Mimo 的狀態（聆聽時抖耳、思考時飛機耳、說話時開合共振）進行微動畫，並附有實體互動面板。
* **🛠️ 軟硬體雙軌降級防護**：實體硬體驅動（OLED、舵機、觸控、OpenCV 人臉追蹤）與大腦完全解耦。在沒有硬體連接的 PC 環境下，會自動以降級的 Mock 模擬模式運行並輸出 Log，絕不崩潰。

---

## 🛠️ 系統需求 (System Requirements)

| 項目 | 建議規格 |
|---|---|
| 作業系統 | Ubuntu 22.04 / Raspberry Pi OS (64-bit) |
| Python | 3.10 至 3.12 |
| RAM | 最低 4GB，建議 8GB (特別是在樹莓派上執行本地 LLM 時) |
| 語音輸入 | 任何 USB 麥克風 |
| 語音輸出 | 任何 USB 喇叭或 3.5mm 音訊裝置 |
| 硬體擴充 | 樹莓派 5、SSD1306 OLED (I2C)、SG90 舵機雲台、GPIO 觸控板、Pi Camera (選配，詳見 [MIMO.md](MIMO.md)) |

---

## 💾 安裝步驟 (Installation)

### 1. 安裝 Ollama（本地運行大腦）
```bash
curl -fsSL https://ollama.com/install.sh | sh
# 拉取建議的本地模型
ollama pull gemma3:1b       # 本地主要對話與意圖路由模型 (推薦)
ollama pull moondream       # 本地視覺分析模型（拍照看圖功能）
```

### 2. 複製專案並建立虛擬環境
```bash
git clone <your-repo-url> spark
cd spark

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
nano .env  # 填入您的 Key
```
在 `.env` 中填入以下內容（若使用 Cloud 模式）：
```env
# OpenRouter API 金鑰
OPENROUTER_APIKEY=sk-or-xxxxxxxxxxxxxxxxxx
```

### 5. 下載 Piper TTS 雙語語音模型
Mimo 使用 **Piper TTS** 進行高清晰的中英雙語語音合成：
```bash
mkdir -p models
cd models

# 中文語音 (必要)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/xiao_ya/medium/zh_CN-xiao_ya-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/xiao_ya/medium/zh_CN-xiao_ya-medium.onnx.json

# 英文語音 (必要，用於混合英文單字)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/models/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/models/en_US-lessac-medium.onnx.json

cd ..
```

### 6. 啟動 Mimo
```bash
python main.py
```
首次啟動時，系統會載入 Whisper 語音辨識、預熱 Ollama，並**預合成 45 個貓咪專屬的傲嬌 Filler 語音快取**（儲存於 `./audio_cache_data/`）。第二次開機起將直接讀取快取，實現零延遲啟動！

---

## 🎮 使用方式 (Usage)

### Web 互動主介面 — `http://localhost:8000/`
* **動態貓耳/貓鬚動畫**：反應 Mimo 當前的狀態（打盹 / 聆聽抖耳 / 飛機耳思考 / 鬍鬚共振說話）。
* **🐾 擼貓摸摸按鈕**：點擊觸發 Mimo 的 Attentive 撒嬌狀態，播放呼嚕 Filler 聲，並產生傲嬌文字回應。
* **🌡️ 貓掌量溫滑桿**：模擬量測體溫，Mimo 會根據溫度（36-37.2°C 正常；低於 36°C 冰冷；高於 37.5°C 烤番薯）給予傲嬌關懷評價，若發燒更會觸發緊張炸毛的医疗安全語音防護。
* **設定頁面 — `http://localhost:8000/config`**：管理本地/雲端模式切換、更改奴才的名字，以及編輯「Mimo 生活叮嚀排程（如補水提醒、伸展魔法時間）」。

---

## 🔌 實體硬體與規格 (Hardware Specs)

Mimo 的實體外殼組裝、接線圖、OLED 像素臉部表情繪製規範、雙軸舵機動態姿態（歪頭殺、開心抬頭、打盹垂頭）以及 OpenCV 相機人臉追蹤代碼規格已完全整合至獨立文件：

👉 **詳細實體硬體規格書請點擊閱讀：[MIMO.md](MIMO.md)**

---

## ⚙️ 系統架構 (Architecture)

```
main.py                  ← 主進程，管理 state machine 狀態流與語音編排
├── brain.py             ← AI 大腦：雲端/本地 chat、無縫本地降級、意圖分類
├── tts.py               ← 語音合成引擎（Piper，中文 CN-xiao_ya 與英文 US-amy 混合）
├── stt.py               ← 語音辨識（faster-whisper）
├── audio_cache.py       ← 貓咪專屬 Filler 語音預生成與快取系統
├── memory.py            ← chromaDB 向量對話記憶（mimo_chroma_db）
├── reminders_db.py      ← 叮嚀排程資料庫 (reminders.db, SQLite)
├── settings_manager.py  ← 設定檔管理器 (settings.json)
├── state_machine.py     ← 系統狀態定義 (IDLE/LISTENING/THINKING/SPEAKING 等)
├── ui.py                ← FastAPI + WebSocket 後端服務
├── config.py            ← 全域參數配置文件 (模型配置、API keys、硬體 GPIO 等)
└── static/
    ├── index.html       ← 玻璃擬態主互動介面 (SVG 貓耳貓鬚動態、摸摸與量溫面板)
    └── config.html      ← 貓咪叮嚀排程與個人化設定頁面
```

---

## 🤖 推薦模型 (Model Recommendations)

* **本地模型 (Local Ollama)**:
  * `gemma3:1b` (⭐ 推薦主要大腦及意圖路由模型，速度快、資源佔用極低)
  * `moondream` (本地視覺分析模型)
* **雲端模型 (Cloud OpenRouter)**:
  * `qwen/qwen3-next-80b-a3b-instruct:free` (⭐ 推薦免費大腦模型，Traditional Chinese 遵循能力最強)
  * `meta-llama/llama-3.3-70b-instruct:free` (雲端備用大腦模型)
  * `qwen/qwen2.5-vl-72b-instruct:free` (雲端最強免費視覺分析模型)

---

## 📄 License
MIT License — 歡迎自由修改，用溫暖的科技與傲嬌的貓咪守護您和家人的生活。 💖🐱
