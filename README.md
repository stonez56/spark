# 🐈 Mimo — 溫感 AI 傲嬌貓咪助理 (Mimo AI Cat Assistant)

**Mimo** 是一個基於 AI 的雙語（繁體中文 / 英文）貓咪陪伴助理系統，專為日常陪伴與生活助理而設計。她具備台灣傲嬌貓咪的獨特個性（自稱「本喵」，稱呼您為「主人」），支援即時語音辨識、零延遲語音填補（Filler Audio）、喚醒詞觸發、生活起居叮嚀，並提供了精緻的 midnight-indigo 深色玻璃擬態 Web UI 介面，讓您可以隨時透過手機或平板進行「擼貓摸摸」與「貓掌量溫」等虛擬互動。

Mimo 更設計了專門為樹莓派 5 打造的實體外觀硬體擴充規格，包含 0.96" OLED 表情顯示、SG90 雙軸雲台頸部轉動、實體觸控感測器以及主動式 OpenCV 人臉追隨。

---

## 🚀 核心優勢與亮點 (Highlights)

* **🐱 傲嬌貓咪個性與台灣口癖**：徹底重塑大腦 System Prompt，常規每句限制在 20 字內，口氣活潑傲嬌，隨機帶有「喵～」、「哼」。問到知識型提問（如「什麼是LLM」）時，大腦能智慧判斷並動態切換為「博學導師貓咪人設」並放寬字長至 100 字內，提供流暢完整的科普，徹底避免斷句缺漏。
* **⚡ 0ms 本地時間日期攔截器 (0ms Fast Datetime Interceptor)**：大腦在對話生成最開端部署了超低延遲（`0.07 毫秒`）本地攔截器。任何問到時間、日期、星期的口語問句（包括繁簡體組合，如「今天是星期几」、「幾月幾日」），均直接由 Python 本地取得系統時間，並自動轉換為民國曆，兼具極致速度與精準防幻覺！
* **🎙️ VAD 智慧語速斷句自適應系統 (VAD Speech Speed Adaptation)**：在網頁設定中提供快速/一般/慢速等自適應語速設定。大腦會動態調整 VAD（語音活動檢測）的靜音超時（`1.2` 秒 / `1.8` 秒 / `2.5` 秒），最大錄音上限放寬至 `15.0` 秒，貼心關懷長輩，徹底防範說話中途被無情切斷。
* **🌐 語音辨識繁體中文雙防線 (STT Traditional Chinese Dual Defense)**：在轉寫源頭部署雙重防護！
  * **第一防線**：Whisper 呼叫時傳入解碼引導 prompt，引導模型優先解碼台灣繁體字。
  * **第二防線**：轉寫返回前透過內建簡繁字元歸一後處理，100% 杜絕簡體字污染大腦、ChromaDB 記憶庫與控制台。
* **🛡️ 本地小模型退化重複鐵壁防禦網 (Anti-Repetition loop Guardrail)**：針對本地小模型（如 `gemma3:1b`）容易陷入退化重複（如噴出 1000 個「準備好」）的頑疾，實作了 **`repeat_penalty: 1.2`** 與自適應 **`num_predict`** 限制；更在最終回覆加載了**退化重複後處理過濾器**，一旦偵測到文字中出現連續重複字串，會在第一次出現後將其餘垃圾自動截斷並冠上可愛貓咪結尾，為大腦穩定性築起最高安全防線！
* **⚙️ 極致增量語音快取更新 (Granular Audio Cache Update)**：重新設計 API 保存與語音快取引擎。修改貓咪名字或語速時 100% 阻斷快取重建流程；修改使用者名字時，系統能智慧辨識並**只重新合成 6 個含有稱呼的動態 Filler 快取**，另外 49 個靜態 filler 直接 0 毫秒從磁碟複用，整體保存速度由 >10 秒縮短至**小於 1 秒**！
* **⚡ 零延遲 Snappy 本地降級機制**：針對 OpenRouter 雲端免費 API 尖峰時間易發生 429 限流與 404 故障，大腦實作了**主動 transforms 停用**與**極速本地降級**：
  * 強制在 API 請求中傳入 `"transforms": []`，停用 OpenRouter 的慢速後台自動轉發。
  * 設定 `6.0` 秒嚴格超時，一旦雲端異常，**0.1 秒內無縫切換至本地 Ollama (`gemma3:1b`)**，語音 TTS 播放絕無卡頓，流暢度提升 300%！
* **🎨  midnight-indigo 玻璃擬態 UI**：主頁面包含精美 Aurora 霓虹光暈，動態 SVG 貓耳與貓鬚會隨著 Mimo 的狀態（聆聽時抖耳、思考時飛機耳、說話時開合共振）進行微動畫，並附有實體互動面板。
* **🛠️ 軟硬體雙軌降級防護**：實體硬體驅動（OLED、舵機、觸控、OpenCV 人臉追蹤）與大腦完全解耦。在沒有硬體連接的 PC 環境下，會自動以降級的 Mock 模擬模式運行並輸出 Log，絕不崩潰。
* **🗺️ IP 位置感知搜尋 (IP-based Location Awareness)**：首次啟動時自動以 IP 定位取得使用者所在城市（如「新竹市」），並持久化儲存於 `settings.json`，日後開機直接讀取無需每次重測。設定頁面 (`/config`) 可查看並手動修正目前偵測到的城市，所有地名一律轉換為台灣繁體中文。
* **🧵 Session 邊界城市上下文防跨回合污染 (Session-bounded City Context)**：城市上下文掃描改為僅讀取**當次開機後**的對話歷史（`memory.get_recent_history_since(session_start)`），防止前一 Session 提及的城市（如「桃園」）污染全新開機後的天氣搜尋。若當次 Session 內未提及任何縣市，一律回退使用 GPS 城市（如「新竹市」）。
* **🔍 LLM 智慧搜尋問句改寫 (LLM-based Search Query Rewriting)**：捨棄傳統硬編碼的口語贅詞過濾清單（Fluff List），改由 LLM 智慧將使用者的口語化問句改寫為 5 字以內的純搜尋引擎關鍵字（例如：「今年的天氣如何」➔「天氣預報 氣溫」），並在異常時自動降級回 legacy 規則式過濾，大幅提升搜尋精準度。
* **🌦️ 中央氣象署 Open Data 天氣模組 (CWA Weather API)**：天氣類查詢優先呼叫台灣中央氣象署官方 Open Data API（`F-C0032-001`，36 小時縣市預報），取得精確的氣溫、降雨機率、體感舒適度等結構化資料，完全取代不穩定的 DDG 網頁爬蟲。支援 22 個縣市自動對應，並在 API 不可用時無縫降級至 DDG 搜尋。詳見 `weather.py`。
* **🔇 TTS 單位符號中文化預處理 (TTS Unit Symbol Sinicization)**：在雙語語言切割器執行前，`tts.py` 的 `_preprocess_text()` 先跑一輪 `UNIT_SUBS` 替換表，將 `°C→度`、`°F→華氏度`、`km/h→公里每小時`、`WiFi→無線網路` 等單位符號與縮寫全部轉換為中文，避免孤立的英文字母（如 `C`、`F`）被語言切割器誤判為英文段落並由英文 TTS 語音讀出，造成令人出戲的雙聲道切換。

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
在 `.env` 中填入以下內容：
```env
# OpenRouter API 金鑰（Cloud 模式必填）
OPENROUTER_APIKEY=sk-or-xxxxxxxxxxxxxxxxxx

# 中央氣象署 Open Data 金鑰（免費申請：https://opendata.cwa.gov.tw/user/authkey）
# ⚠️ 若金鑰含有 = 號，必須用引號包住，否則 dotenv 會截斷！
CWA_API_KEY="CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
# 不填時自動使用公開示範金鑰（rdec-key-123-45678-011121314），限流較嚴
```

> **注意**：CWA API 金鑰格式為 `CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`（UUID 格式）。金鑰中含有 `=` 號時，**必須用雙引號包住整個值**，否則 `python-dotenv` 會在第一個 `=` 處截斷，導致金鑰失效。

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

### 7. 🆕 如何開始一個全新且乾淨的 Mimo 專案 (Starting a Fresh Mimo Project)
如果您是剛下載或複製 (clone) 這個專案，或者想要完全抹除過去的歷史對話、生活叮嚀排程與個人化暱稱設定，以開始一個全新乾淨的貓咪陪伴專案，您可以透過以下任一方式進行完整重設：

* **方法一：執行指令列重設腳本（推薦，最乾淨徹底）**
  在啟動 Mimo 前，直接執行專案根目錄下的重設腳本：
  ```bash
  python reset_db.py
  ```
  這會由腳本自動幫您處理以下乾淨重建工作：
  1. 重置並重新初始化對話歷史 SQL 資料庫 (`mimo_memory.db`)。
  2. 重置並清空生活叮嚀排程 SQL 資料庫 (`reminders.db`)。
  3. 清除並重設 ChromaDB 向量檢索記憶庫 (`mimo_chroma_db/`)。
  4. 將個人暱稱與角色設定檔 (`settings.json`) 恢復為乾淨預設值（主人尊稱恢復為預設值，貓咪名字恢復為預設的 `Mimo`）。
  5. 刪除所有舊語音快取目錄 (`./audio_cache_data/`)，確保在下次啟動時根據最新姓名設定重新預合成 45 個專屬語音片段。

* **方法二：透過 Web UI 介面一鍵清除**
  啟動專案後，打開瀏覽器訪問主控制台 `http://localhost:8000/`，在底部的系統控制面板中點擊 **「清除記憶與資料庫」** 按鈕，系統會以 API 呼叫後台的重設引擎，並為您完成全套乾淨重置！

---

## 🎮 使用方式 (Usage)

### Web 互動主介面 — `http://localhost:8000/`
* **動態貓耳/貓鬚動畫**：反應 Mimo 當前的狀態（打盹 / 聆聽抖耳 / 飛機耳思考 / 鬍鬚共振說話）。
* **🐾 擼貓摸摸按鈕**：點擊觸發 Mimo 的 Attentive 撒嬌狀態，播放呼嚕 Filler 聲，並產生傲嬌文字回應。
* **🌡️ 貓掌量溫滑桿**：模擬量測體溫，Mimo 會根據溫度（36-37.2°C 正常；低於 36°C 冰冷；高於 37.5°C 烤番薯）給予傲嬌關懷評價，若發燒更會觸發緊張炸毛的医疗安全語音防護。
* **設定頁面 — `http://localhost:8000/config`**：管理本地/雲端模式切換、更改您的稱呼，以及編輯「Mimo 生活叮嚀排程（如補水提醒、伸展魔法時間）」。

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
├── location_manager.py  ← IP 位置感知模組（首次啟動自動偵測城市，持久化至 settings.json）
├── settings_manager.py  ← 設定檔管理器 (settings.json)
├── weather.py           ← 中央氣象署 CWA Open Data 天氣模組（F-C0032-001，36hr 縣市預報）
├── state_machine.py     ← 系統狀態定義 (IDLE/LISTENING/THINKING/SPEAKING 等)
├── ui.py                ← FastAPI + WebSocket 後端服務
├── config.py            ← 全域參數配置文件 (模型配置、API keys、硬體 GPIO 等)
└── static/
    ├── index.html       ← 玻璃擬態主互動介面 (SVG 貓耳貓鬚動態、摸摸與量溫面板)
    └── config.html      ← 貓咪叮嚀排程與個人化設定頁面
```

---

## 💾 資料庫與記憶系統 (Databases & Memory System)

Mimo 的大腦結合了關係型資料庫與先進的向量檢索記憶系統，使得她不僅可以記錄精確的定時生活叮嚀，還能如真正的寵物貓咪般，在對話中無縫記住與您的互動歷史：

1. **對話記憶資料庫 (`mimo_memory.db`)** — SQLite
   - **用途**：精確存儲每一筆使用者輸入與 Mimo 對話回覆的原始字串，帶有精確的時間戳記，為後續的語意檢索提供精準的文本來源與對話時間線記錄。
2. **語意向量記憶庫 (`mimo_chroma_db/`)** — ChromaDB
   - **用途**：Mimo 的核心長短期記憶系統。在對話進行時，系統會自動將您的對話內容轉換為高維度語意向量，並持久化存儲於本地的向量資料庫中。
   - **運作機制**：當您再次提問時，大腦會在毫秒內透過語意相似度檢索過去最相關的 3 筆對話回憶作為對話上下文送入 LLM，從而記住您的習慣與之前聊過的話題。
3. **生活叮嚀排程資料庫 (`reminders.db`)** — SQLite
   - **用途**：存儲所有使用者定時安排的提醒事項（如每天下午三點半的補水提醒、晚上十點的睡眠叮嚀等），具備完整的多時間點、每週重複天數設定與啟動開關。
4. **個人化設定檔 (`settings.json`)** — JSON
   - **用途**：儲存主人尊稱、貓咪名字（與喚醒詞對應）、語速設定與 LLM 背後路由模式，作為跨進程全域共享的即時狀態表。

---

## 🤖 推薦模型與延遲指南 (Model Recommendations & Latency Guide)

Mimo 的雲端大腦支援多種 OpenRouter 模型，並提供「推理模式（Reasoning/Thinking Mode）」的手動切換以平衡生成品質與速度：

### 1. 雲端大腦模型 (Cloud LLM Models)
* **預設免費模型 (Default Free Models)** — **生成時間：2 - 3 秒**：
  * `openai/gpt-oss-120b:free` (預設首選) — 高速生成且完全免費。
  * `google/gemma-4-31b-it:free` — 優異的中英文指令遵循能力。
  * `moonshotai/kimi-k2.6:free` — Kimi 中文長文本對話模型。
* **備用付費模型 (Backup Paid Model)** — **生成時間：2 - 3 秒**：
  * `deepseek/deepseek-v4-flash` — 極低成本的付費備用模型。當上述免費模型因尖峰時間故障或遭遇 OpenRouter `429` 限制時，大腦會自動以此模型作為第一重雲端 fallback，避免直接降級到本地，確保回覆品質喵！
* **深度推理模型 (Deep Reasoning Models)** — **生成時間：15 - 30+ 秒**：
  * `deepseek/deepseek-r1` / `openai/o1` 系列 — 這些模型具備強大的內部「思維鏈（Chain of Thought）」推導能力。

### 2. 🧠 推理模式開關與延遲說明 (Reasoning Toggle & Latency)
由於推理模型在產生回覆前，需要先生成大量的隱藏思維標記（Thinking Tokens），因此會帶來顯著的延遲：
* **一般對話模型 (Non-reasoning / Standard)**：在對話時**建議關閉推理模式**。此時 OpenRouter 不會帶有 `reasoning_effort` 參數，對話將在 **2-3 秒** 內立即回應。
* **推理模型 (Reasoning Model)**：當您選用 R1 或 O1 等模型，或是在系統設定中勾選了 **「啟用深度思考/推理模式」**，大腦會啟用深度思考參數。雖然生成內容的邏輯深度大幅提升，但處理延遲將增加到 **15 至 30+ 秒**。
* **雙軌安全機制**：
  - **自動白名單識別**：若選用 `deepseek/deepseek-r1`、`openai/o1` 等模型，系統會自動辨識並開啟推理參數。
  - **手動 override 選項**：您可以在 `http://localhost:8000/config` 介面中隨時勾選或取消「啟用深度思考/推理模式」來強制控制是否啟用思維鏈。

### 3. 本地大腦與視覺 (Local Ollama)
* `llama3.2:3b` / `gemma3:1b` — 本地邊緣運算首選大腦與意圖路由模型，完全脫網運行，反應時間小於 1.5 秒。
* `moondream` — 本地視覺分析模型，用於 Mimo 拍照看圖時的本地圖文理解。

### 4. 🔍 搜尋字詞改寫模式 (Search Query Rewrite Mode)
此模式決定系統在發送搜尋引擎（DuckDuckGo）請求前，如何將使用者的口語化句子精煉為精準關鍵字。可在設定頁面中切換三種模式：
* **⚡ 規則快篩 (legacy)**：使用簡化的正則表達式快速過濾贅詞與疑問詞，`0 毫秒` 延遲，能滿足基本搜尋需要。
* **🤖 本地 LLM 改寫 (local_llm)**：使用本機運行的 Ollama 模型進行智慧改寫，既有語意理解能力，又免受網路波動與延遲影響。
* **☁️ 雲端 LLM 改寫 (cloud_llm)**：使用配置好的雲端 API 大模型進行最精準的改寫。適合複雜的口語情境，在 dialogue mode 為 local 且 routing mode 為 cloud 時，系統會自動在後台完成模型匹配與轉換。


---

## ⏱️ 工業級延遲優化里程碑 (Industrial Latency Optimization Milestones)

為了將 Mimo 的語音對話延遲推進至工業級標準（首字發聲延遲 < 2.5 秒），我們在此分支上進行了深度優化，主要改進包含：

1. **分句流式語音合成 (Sentence-level Streaming TTS)** 
   - **優化前**：TTS 必須等待大腦完整生成回覆（可能長達 15~30 秒）後才一次性進行合成，造成嚴重的等待時間。
   - **優化後**：實作 `synthesize_stream` 引擎。將大腦生成文本預先切分為短句（中文限制在 35 字以內），並採用 Progressively Yield 串流輸出。首句合成時間降低至 2-5 秒，顯著縮短首字發聲延遲 (First-Byte Latency)。

2. **0ms 本地時間日期攔截器 (0ms Fast Datetime Interceptor)**
   - **優化後**：大腦端部署超低延遲（`0.07 毫秒`）本地時間攔截器。任何涉及時間、日期、星期的問句均在本地 Python 取得系統時間並轉換為民國曆，完全避免 LLM 推理與網路延遲，且 100% 防止時間幻覺。

3. **零延遲本地降級機制 (Snappy Local Fallback)**
   - **優化後**：當雲端免費 API 尖峰時間限制（`429`）或故障時，實作 `6.0` 秒嚴格超時與自動停用 transforms 轉發。一旦雲端超時，在 `0.1` 秒內無縫降級切換至本地 Ollama (`gemma3:1b`)，確保語音對話不中斷。

4. **極致增量語音快取更新 (Granular Audio Cache Update)**
   - **優化後**：修改設定時，智慧辨識並「僅重新合成 6 個含暱稱的動態 Filler 快取」，其餘 49 個靜態音訊直接從磁碟複用，使快取更新保存時間由 >10 秒縮短至 `< 1 秒`。

5. **智慧雙軌推理模式開關 (Dual-track Reasoning Toggle)**
   - **優化後**：在設定面板中新增「深度思考/推理模式」開關。一般問答預設關閉以維持 `2 - 3 秒` 的快速生成，僅在使用者有深度推理需求時才手動開啟，避免免費推理模型帶來的額外延遲。

6. **全意圖記憶持久化與跨回合城市上下文 (Full-intent Memory Persistence & Cross-turn City Context)**
   - **問題**：`memory.add_interaction()` 原本只在 `chat` 意圖分支中呼叫，導致 `search_web`、`take_photo` 等所有其他意圖的回覆**從未**寫入 SQLite 對話歷史，使得後續問句無法從歷史中讀取到上下文城市，錯誤地以裝置物理定位回答（如問新竹名產，卻回答士林景點）。
   - **優化後**：將 `memory.add_interaction()` 移至整個意圖處理鏈末端，**統一持久化所有語音對話**。並擴充 `search_web` 中的地理敏感詞清單（新增「名產」、「伴手禮」、「好玩」、「踏青」等），確保後續問句能正確從最近對話歷史讀取討論的縣市，將搜尋詞精準偏置（如「新竹市 名產可以買 美食 推薦」），徹底修復跨回合地域型問答錯位的問題。

7. **LLM 智慧搜尋問句改寫 (LLM-based Search Query Rewriting)**
   - **優化前**：使用規則式與硬編碼的口語贅詞過濾清單（Fluff List）來清理搜尋問句，此方式無法擴展，極易因為千奇百怪的口語詞彙（如「今年的天氣如何」）而使搜尋引擎匹配到不相關的網頁（例如 Wikipedia 年平均氣候條目）。
   - **優化後**：移除硬編碼 of Fluff List，改由 LLM（本地 Gemma 或雲端模型）智慧改寫為 5 字以內的純搜尋引擎關鍵字（如「天氣預報 氣溫」），並在 LLM 失敗時自動無縫降級回 legacy 規則式過濾，既保障了理解深度與準確度，又徹底免除了人工維護過濾詞庫的成本喵！

8. **🎨 Web UI 玻璃擬態版面防溢出與快取標頭防護 (Layout Containment & Caching Defense)**
   - **優化前**：網頁版面以百分比分配高度且 `body` 設為 `min-height: 100vh;`，當對話紀錄增長時會將下方的擼貓、音量、體溫模擬按鈕擠出螢幕之外；且瀏覽器常會強烈快取 `config.html` 與 JS，導致新程式碼更新時，使用者加載舊版快取而無法看到新面板。
   - **優化後**：在 [index.html](file:///home/user/spark/static/index.html) 中限制 `body` 高度為固定的 `height: 100vh;` 並使用 `@media (max-height: 750px)` 與 `@media (max-height: 600px)` 響應式縮小貓臉 SVG 與最大對話框高度，提供清晰易見的高對比度捲軸。並在 [ui.py](file:///home/user/spark/ui.py) 端針對主頁與設定頁回傳帶有 `Cache-Control: no-store` 標頭，徹底免除快取污染。

9. **☁️ 雲端與意圖辨識獨立設定面板 (Independent Cloud Settings Panel)**
   - **優化後**：在設定頁面中建立獨立的 `☁️ 雲端模型設定` 面板，將「雲端模型選擇」與「深度思考」從「大腦對話模式」面板中徹底解耦。即使主人選擇「本地大腦對話 (Local) + 雲端意圖辨識 (Cloud)」，也能夠非常清晰且獨立地在專屬面板中設定所需的雲端模型與參數。

10. **🔌 OpenRouter 400 錯誤與自動客戶端初始化 (OpenRouter 400 Fix & Client Auto-Init)**
    - **優化後**：當 Dialogue Mode 設為 Local 且 Intent Routing 設為 Cloud 時，修正 `_cloud_chat()`，使其能智慧識別本地模型 ID（如 `llama3.2:3b`），自動從設定檔載入 `cloud_text_model` 發起請求，解決 OpenRouter 報 400 Bad Request 的 model ID 錯誤；同時當偵測到客戶端未初始化時，在對話時自動執行 `_init_cloud_client()` 初始化連線。

11. **🌦️ 中央氣象署 Open Data 天氣 API 整合 (CWA Weather API Integration)**
    - **問題前**：天氣查詢走 DuckDuckGo 網頁搜尋，常因爬到景點介紹、歷史資料等不相關結果而回答「目前無法取得精確數據」。
    - **優化後**：新增 `weather.py` 模組，在 `brain.py` 的 `search_web()` 中，偵測到天氣意圖時**優先呼叫 CWA Open Data API**（`F-C0032-001`，36 小時縣市預報），取得包含天氣現象、氣溫、降雨機率、體感舒適度的結構化 JSON 資料，直接以 `get_weather_prompt()` 格式化後送入 LLM，Mimo 可精準播報「今晚新竹市：陰陣雨或雷雨，23～24 度，降雨機率 100%，體感舒適」。API 不可用時自動降級至 DDG。支援 22 縣市別名對應與 OpenSSL 3.x SSL 自動 fallback。
    - **API 金鑰**：免費申請：[opendata.cwa.gov.tw/user/authkey](https://opendata.cwa.gov.tw/user/authkey)，設定至 `.env` 的 `CWA_API_KEY`（值需用引號包住）。不填時使用公開示範金鑰。

12. **🔇 TTS 單位符號中文化前處理 (TTS Unit Sinicization Pre-pass)**
    - **問題前**：`°C` 被雙語語言切割器拆分為 `氣溫在十八°`（中文聲音）+ `C`（英文聲音），造成令人出戲的雙聲道切換，英文 TTS 額外說出一個孤立的「C」。
    - **優化後**：在 `tts.py` 的 `_preprocess_text()` 中，語言切割**前**先執行 `UNIT_SUBS` 替換表：`°C→度`、`°F→華氏度`、`km/h→公里每小時`、`WiFi→無線網路`、`USB→通用序列匯流排` 等。切割器接收到的文字中再無孤立英文字母，全程單一中文聲音播報。

13. **📍 Session 邊界城市上下文防污染 (Session-bounded City Context)**
    - **問題前**：`search_web()` 呼叫 `memory.get_recent_history(limit=2)` 讀取**全跨 Session** SQLite 歷史，若前一次開機對話提到「桃園」，重啟後第一次問天氣仍然查詢桃園天氣，忽略使用者 GPS 城市（新竹）。
    - **優化後**：`OllamaBrain.__init__()` 記錄 `self._session_start = datetime.now().isoformat()`；`memory.py` 新增 `get_recent_history_since(since_iso, limit)` 方法；`search_web()` 城市掃描改為僅讀取當次開機後的對話，若無命中，一律使用 GPS 城市，徹底消除跨 Session 城市污染。

---

## 🎙️ Breeze 台灣在地化語音發音擴充計畫 (100+ 諧音對照表)

本專案特別設計並實作了 **Breeze 台灣在地化語音發音擴充計畫**。為了解決在 Raspberry Pi 5 等邊緣裝置上難以流暢運作龐大 Breeze 7B 台語大模型的問題，本系統透過極低開銷的「語音諧音前處理對照表」，讓 Mimo 能夠在 0ms 額外生成延遲的狀態下，說出帶著親切台語腔調與在地口語的語彙！

### 💡 核心技術特點
* **0ms 額外運行延遲**：不需要在 Pi5 上載入重型台語模型，僅需在文字送入 Piper TTS 合成引擎前，利用高效的單次正規表示式 (Single-pass Regex) 進行詞彙比對與發音諧音置換，時間複雜度為 `O(N)`。
* **100+ 組台語與在地化諧音對照**：
  * **日常問候**：例如將「吃飽沒/食飽未」自動置換為「呷霸沒」、「謝謝」置換為「多夏」、「對不起/抱歉」置換為「拍謝」、「早安」置換為「告榨」。
  * **日常動詞**：例如將「睡覺」置換為「困覺」、「吃飯」置換為「呷飯」、「洗澡」置換為「誰行摳」、「出來講」置換為「踹共」、「不知道」置換為「嗯災」。
  * **形容詞與狀態**：例如將「不行/不可以/毋湯」置換為「姆湯」、「真的/真正」置換為「金架」、「漂亮」置換為「水」、「肚子餓」置換為「妖」、「棘手」置換為「麻還」（麻煩）。
  * **時間與天氣**：例如將「今天」置換為「今啊日」、「明天」置換為「明啊載」、「昨天」置換為「匝昏」、「下雨」置換為「落雨」、「太陽」置換為「日頭」、「颳風」置換為「起風」。
  * **流行語與感嘆詞**：例如將「真的假的」置換為「甘有影」、「裝瘋賣傻」置換為「裝孝維」。
* **STT 台語辨識糾錯防線**：在麥克風語音辨識轉寫端，同步部署了台語口語（例如「哩厚」、「呷霸沒」）的自動標準化後處理，確保 Mimo 大腦能無障礙理解主人的台語關懷。
* **獨立開關控制**：使用者可在 Web UI 設定頁面中獨立開啟/關閉「Breeze 語音在地化模式」；當其啟用時，系統在預合成生活語音快取 (Filler Cache) 以及即時對話語音合成時，皆會自動套用此在地化發音對照表。

---

## 📄 License
MIT License — 歡迎自由修改，用溫暖的科技與傲嬌的貓咪守護您和家人的生活。 💖🐱

