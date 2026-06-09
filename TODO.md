# 🐈 Mimo 系統優化與修復待辦清單 (TODO)

本文件專為接手的 AI 助理設計，用以銜接 **Mimo (原 Spark) 實體貓咪助理** 的端到端語音延遲優化與系統穩定度修復工作。

---

## 📌 當前分支與專案狀態
* **當前活躍分支**：`feature/lightweight-intent`
* **最新提交 (Commit)**：`afa86f9` (修復並發寫入鎖衝突)
* **當前代碼狀態**：工作區乾淨，已解決 Web UI 靜默卡死在 `Thinking` 的問題，並完成了 Phase 1 的意圖路由本地化。

---

## 🛠️ 已完成的修改與修復 (Completed)

1. **本地輕量意圖路由 (0ms Intent Router)**：
   * 檔案：[brain.py](file:///home/user/spark/brain.py)
   * 功能：實作正則關鍵字攔截（覆蓋 12 種核心意圖）。若未匹配，在本地透過啟發式規則（如問句特徵、長度大於 12 字等）自動分流至 `search_web` 或 `chat`。
   * 控制開關：於 `settings.json` 中由 `"intent_fallback_to_llm"` 決定是否在本地攔截失敗時退回 LLM。本地模式預設為 `False` 以減輕 Pi5 CPU 開銷。

2. **ASR 幻覺零過濾 (ASR "０" Filter)**：
   * 檔案：[stt.py](file:///home/user/spark/stt.py)
   * 功能：修復 Whisper 在說話停頓時易產生孤立全形 `０` 的問題。使用正則後置/前置斷言過濾孤立全形 `０`，同時安全保留合法的半形/全形小數與數字。

3. **WebSocket 並發寫入安全化與佇列監控**：
   * 檔案：[ui.py](file:///home/user/spark/ui.py)
   * 功能：將 `monitor_state_queue`、`monitor_tts_queue`、`monitor_transcript_queue` 中會阻塞單執行緒事件循環的 `Queue.get()` 重構為非阻塞 `get_nowait()` 配合 `asyncio.sleep`。
   * 寫入鎖：引入 `asyncio.Lock` 協程鎖（存於 `websocket.scope["write_lock"]`），並包裹所有對 WebSocket 的發送操作（`_safe_send_text`、`_safe_send_bytes`），徹底解決了「巨大思考填充音發送時，並發發送 state 狀態更新導致 Starlette 拋出 write 異常，進而將用戶端移出廣播集合導致網頁永久卡死在 Thinking」的嚴重 Bug。

4. **前端防禦性 Exception 捕捉**：
   * 檔案：[static/index.html](file:///home/user/spark/static/index.html)
   * 功能：將 `ws.onmessage` 與 `playAudio` 包裝在 `try...catch` 中，一旦前端 JS 發生例外，會主動發送 POST 請求至 `/api/debug-log` 打回終端機主控台，杜絕前端無聲崩潰。

---

## 🚀 下一步待辦清單 (TODO for Next Step)

### 1. 合併與開分支
* [ ] 將目前分支 `feature/lightweight-intent` 安全合併回 `mimo` 分支。
* [ ] 以 `mimo` 為基準開闢新的改進分支：`feature/asr-whisper-cpp`。

### 2. ASR 語音識別優化 (遷移至 whisper.cpp)
* [ ] **引入 whisper.cpp Python 綁定**：
  * 當前系統使用的是 `faster-whisper-base`。雖然在 CPU 上運作，但在 Pi5 8GB 上仍有約 1.2s ~ 1.5s 的轉錄延遲。
  * 請評估並安裝 `whisper.cpp` 的 Python 綁定（例如 `whisper-cpp-pybind` 或透過 ctypes 載入編譯好的共享庫）。
  * 載入極輕量且高準確度的 `whisper-tiny` 或 `whisper-tiny-q5` 量化模型。
* [ ] **ARM Neon 編譯器硬體加速**：
  * 在 Raspberry Pi 5 64-bit OS 上編譯 `whisper.cpp` 底層庫時，啟用 **ARM Neon** 優化指令集，將轉錄延遲壓縮至 **300ms 左右** 的工業級標準。

### 3. TTS 合成優化 (ONNX 線程調優)
* [ ] **調優 [tts.py](file:///home/user/spark/tts.py) 的 ONNX 執行執行緒數**：
  * 在 [tts.py](file:///home/user/spark/tts.py) 的 `SparkTTS` 初始化 ONNX Session 時，調整 `SessionOptions`：
    ```python
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4  # 發揮 Pi5 的 4 核心硬體效能
    ```
  * 驗證這是否能加速 Piper TTS 語音合成流的產出速度。

### 4. 系統綜合驗證
* [ ] **手動驗證**：
  * 執行 `python main.py` 並開啟網頁介面。
  * 測試「喚醒詞 -> 播放 wake_word_ack -> 進入 Listening 錄音 -> 進入 Thinking 播放 filler -> 串流播放 TTS -> 結束退回 Idle」的完整語音交互迴圈，確保轉錄字詞準確且無延遲卡頓。
