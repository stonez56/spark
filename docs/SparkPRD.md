

## **1\. 專案概述**

Spark 是一個部署於 Raspberry Pi 5 的在地化 AI 語音助理，旨在模仿朋友間的日常互動。系統具備語音喚醒、語音轉文字 (STT)、大語言模型處理 (LLM)、文字轉語音 (TTS) 以及**視覺表情回饋系統**，並具備長期記憶能力。尤於這個 AI Agent robot 會在台灣使用, 所以它要能聽的懂繁體中文和英文, 能用繁體中文和英文回答.

## **2\. 硬體規格**

* **主機**: Raspberry Pi 5 (8GB RAM)  
* **作業系統**: Raspberry Pi OS 64-bit (Bookworm)  
* **顯示器**: 5 吋觸控顯示器 (建議 DSI 介面)  
* **輸入**: USB 麥克風 (支援多陣列收音尤佳)  
* **輸出**: 3.5mm/USB 喇叭 或 藍牙音響  
* **儲存**: 256GB NVMe SSD  
* **電源**: 5V 5A USB-C 電源 (因應螢幕與 RPi 5 功耗)

## **3\. 軟體架構與組件 (Software Stack)**

| 功能 | 技術/函式庫 | 說明 |
| :---- | :---- | :---- |
| **喚醒詞偵測** | openWakeWord | 支援自定義喚醒詞，採 TFLite 格式 |
| **語音轉文字 (STT)** | Whisper (faster-whisper) | 採 base 或 small 模型 |
| **對話大腦 (LLM)** | Ollama | 使用 Llama 3.2 (3B) 模型，預計 Context Window 32KB |
| **長期記憶** | SQLite \+ ChromaDB | 混合儲存策略，支援結構化資料與語意檢索 |
| **文字轉語音 (TTS)** | Piper | 離線高品質 TTS，支援串流輸出 |
| **表情系統 (UI)** | Python Pygame 或 Web/SVG | 渲染動態表情 (Face Expressions) |
| **系統整合** | Python 3.11+ | 以非同步 (asyncio) 方式管理各組件調度 |

## **4\. 功能需求與詳細流程**

### **4.1 互動流程與表情變化**

0. **熱機**: 第一次開機時，會先進行熱機，把語言模型事先載入記憶體中並且設定 OLLAMA_KEEP_ALIVE=-1 (這樣 Model 不會offload)
1. **等待狀態**: 顯示 **Idle (眨眼、平和)** 表情。  
2. **喚醒**: 偵測到喚醒詞，發出提示音，表情切換為 **Listening (興奮/關注)**。  
3. **收音與轉文字**: 表情切換為 **Attentive (傾聽)**。  
4. **推論與記憶檢索**: 表情切換為 **Thinking (思考/旋轉眼睛)**。  
5. **語音輸出**: Piper 唸出文字，表情同步切換為 **Speaking (說話/動嘴)**。  
6. **閒置觸發**: 長時間未互動，表情切換為 **Bored (無聊)** 或 **Yawn (打哈欠)**。

### **4.2 表情矩陣 (Expression Matrix)**

* **Smile**: 好友般的微笑。  
* **Laugh**: 聽到幽默內容時的開懷大笑。  
* **Bore**: 提醒使用者互動。  
* **Angry**: 當使用者給予負面回饋或特定關鍵字時觸發。  
* **Thinking**: 顯示正在處理資料庫或 LLM 請求。

### **4.3 喚醒詞模型訓練/轉換 (openWakeWord)**

* **自定義流程**:  
  1. 使用 Piper Sample Generator 產生「Spark」發音樣本。  
  2. 使用 openWakeWord 的訓練腳本生成 .onnx 模型並轉為 .tflite。

### **4.4 長期記憶機制**

* **機制**: 採用「混合儲存策略」。  
  * **短期記憶**: 最近 5-10 輪對話保存在 Prompt Context 中。  
  * **長期記憶儲存**:  
    * **SQLite**: 存放結構化的對話紀錄（包含時間戳、使用者 ID、對話摘要）。  
    * **ChromaDB**: 存放 Embedding 向量數據，支援高品質的語意檢索。  
* **檢索流程 (RAG)**:  
  1. **Session 啟動**: 使用者開啟新 Session 或提出新問題。  
  2. **向量比對**: 首先檢索 **ChromaDB** 以尋找與當前話題相關的歷史 Embedding。  
  3. **細節撈取**: 根據檢索到的 ID，從 **SQLite** 中撈出原始的對話摘要或事實細節。  
  4. **上下文組合**: 將撈出的記憶資訊與當前問題組合成「增強版 Context Memory」提供給 LLM 模型進行推論。

## **5\. 技術規格與限制**

* **模型與參數設定**:  
  * **主模型**: Ollama Llama 3.2 (3B)  
  * **Context Window**: 32KB  
  * **Embedding 模型**: all-MiniLM-L6-v2 (用於 ChromaDB 語意搜尋)  
* **延遲目標 (體感效能指標)**:  
  * **喚醒與視覺反饋**: \< 100ms (確保偵測到喚醒詞時表情立即切換)  
  * **語音轉文字 (STT)**: \< 1.2s (針對 3-5 秒短句)  
  * **記憶檢索 (RAG)**: \< 500ms (ChromaDB 向量比對 \+ SQLite 查詢)  
  * **首句出聲延遲 (Streaming TAT)**: \< 2.5s (從使用者停止說話到第一句語音產出)  
* **並行處理與系統調度**:  
  * **Multiprocessing (多程序)**: 核心系統與 5 吋螢幕 UI 表情渲染程序完全隔離，避免 LLM 推論時造成畫面卡頓。  
  * **Threading (多執行緒)**:  
    * Thread 1: 負責麥克風串流與 openWakeWord 實時監聽。  
    * Thread 2: 負責 LED 狀態燈與音訊播放緩衝控制。  
  * **Asyncio (異步 I/O)**: 管理 Ollama 的串流 API 請求與 Piper 文字轉語音的生產者/消費者管線。  
* **記憶體配置規劃 (8GB RAM)**:  
  * 預留 2GB 給系統核心與緩衝區。  
  * 分配 4GB 給 Ollama 3B 模型常駐。  
  * 剩餘 2GB 供 Whisper、ChromaDB 及 UI 進程調度。

## **6\. SSD 開發階段 (Phases)**

1. **Phase 1**: 環境基礎建設 (Ollama, Piper, Whisper 安裝)。  
2. **Phase 2**: **UI 與表情控制模組開發 (與系統狀態機對接)**。  
3. **Phase 3**: 喚醒詞模型訓練與 TFLite 整合。  
4. **Phase 4**: 核心邏輯整合與長期記憶實作。  
5. **Phase 5**: 硬體組裝與散熱最佳化。