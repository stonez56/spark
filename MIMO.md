# 🐈 Mimo 實體貓咪助理硬體與系統規格書 (System & Hardware Specification)

本規格書定義了 **Mimo（溫感 AI 傲嬌貓咪助理）** 的實體硬體配置、接線圖、頭部舵機雲台動態姿態以及系統大腦的容錯架構。

---

## 👁️ 核心視覺方案：主動式人臉偵測與物理追隨
為了給使用者提供最具生物感與真實感的陪伴體驗，Mimo 捨棄了低精度、高延遲且接線複雜的超音波距離感測器（如 HC-SR04），改為採用 **Pi Camera** 結合 **OpenCV** 的高效人臉跟隨方案：
1. **主動驚喜喚醒 (Active Wakeup)**：在 `IDLE`（打盹）狀態下，Mimo 會以低功耗模式（每 1.5 秒擷取一張 320x240 影格）運行人臉檢測。一旦畫面中出現使用者的臉，Mimo 會立刻主動變更為 `ATTENTIVE` 狀態，亮起 OLED 愛心眼，並歪頭說話跟使用者打招呼。
2. **人臉物理跟隨 (Active Gimbal Tracking)**：利用 OpenCV 計算出臉部在畫面中的座標偏移量，微調左右（Pan）與上下（Tilt）舵機角度，使相機（貓咪的眼睛）隨時鎖定並面對使用者。
3. **語音即時拍照 (Zero-Conflict Camera)**：OpenCV 的相機影格讀取背景線程將獨佔並共享 Camera。當使用者語音指令要求「拍張照片」時，系統不需要調用外部 `libcamera-still` 命令行，而是直接從 OpenCV 抓取最新影格存為 `./1.jpg` 送交 AI 分析。這徹底避免了硬體資源衝突，實現流暢的一體化視覺。

---

## 🛠️ 實體硬體配置 (Hardware Mapping)

| 硬體元件 | 專案角色與定位 | 連接方式與驅動建議 | 選擇原因與優勢 |
| :--- | :--- | :--- | :--- |
| **樹莓派 5 (8GB)** | **核心大腦 (Main Brain)** | USB-C 5V 5A 供電 | 負責本地 Ollama、Whisper 語音辨識與 OpenCV 背景人臉跟隨運算。 |
| **0.96" OLED (SSD1306)** | **貓咪實體臉部表情** | I2C 介面 (VCC, GND, SDA, SCL) | 渲染 128x64 像素表情（隨狀態切換眨眼、愛心眼、說話口形等）。 |
| **Pi Camera (IMX219)** | **眼睛、視覺分析與追蹤** | CSI 軟排線固定於雲台上 | 兼顧實時人臉追隨輸入與語音拍照的高清影像抓取。 |
| **SG90 舵機雙軸雲台** | **主動式「頸部」** | GPIO PWM (GPIO 18 / 19) | 接收 OpenCV 的反饋偏置，做出平滑的左右轉頭與上下點頭動作。 |
| **Touch Sensor (觸碰)** | **頭頂「擼貓」感測器** | GPIO 數位輸入 (GPIO 17) | 貼於貓咪頭頂，碰觸時中斷人臉追蹤，觸發撒嬌歪頭與播放呼嚕聲。 |
| **USB 喇叭** | **語音嘴巴 (Audio Out)** | USB Plug & Play 直插 | 提供無延遲的 Piper 語音播放，免去複雜音訊接線。 |

---

## 📐 實體硬體接線圖 (Wiring Architecture)

```mermaid
graph TD
    subgraph Raspberry Pi 5
        GPIO17[GPIO 17] <-->|Signal| Touch[Touch Sensor 觸控感測器]
        GPIO18[GPIO 18 PWM] <-->|Pan 左右舵機| SG90_Pan[SG90 Pan 舵機]
        GPIO19[GPIO 19 PWM] <-->|Tilt 上下/歪頭| SG90_Tilt[SG90 Tilt 舵機]
        I2C_SDA[I2C SDA / SCL] <-->|SDA/SCL| OLED[0.96 OLED SSD1306]
        CSI[CSI CAM Port] <-->|CSI Ribbon| Cam[Pi Camera IMX219]
        USB1[USB Port] <-->|Audio| USBSpeaker[USB 喇叭]
    end
    Power[USB-C Power Supply] -->|5V 5A| Raspberry Pi 5
```

---

## 📐 實體頭部動態與 OLED 表情定義 (Gimbal & OLED States)

| 系統狀態 (`SparkState`) | OLED 表情設計 (128x64 PIL) | 舵機雲台頭部動作 |
| :--- | :--- | :--- |
| **`LOADING`** | 橫向滾動的加載貓咪，或是 Zzz 熟睡圖案 | 頭部完全垂下（低頭狀態），進入休眠。 |
| **`IDLE`** | 正常睜開的雙眼，每隔 5-10 秒自動進行雙眼眨眼 | 啟用 `FaceTrackerThread`。無人臉時頭部居中，偵測到人臉時進行微幅平滑追隨。 |
| **`LISTENING`** | 眼睛放大、耳朵豎起（大圓眼表情） | 停止追隨，頭部微幅前傾，表示正在認真傾聽使用者說話。 |
| **`THINKING`** | 眼睛變成左右滾動的漩渦狀，或思考圈圈滾動 | 執行 **「萌貓歪頭殺 (Inquisitive Tilt)」**：左右舵機微幅不對稱傾斜 $\pm 8^{\circ}$，模擬貓咪沉思。 |
| **`SPEAKING`** | 貓咪雙眼睜開，嘴部波形隨著時間進行張合動畫 | 頭部微幅左右擺動，使說話語音更具生命感。 |
| **`ATTENTIVE` (擼貓中)** | 眼睛變成大大的 **桃心愛心眼 (Heart Eyes)** | 執行 **「開心抬頭 (Happy Look Up)」**：上下舵機微微仰起，配合網頁呼嚕 Filler 聲撒嬌。 |
| **`ANGRY`** | 雙眼變成倒八字的憤怒眼（半圓形） | 頭部快速左右搖晃（搖頭），以示抗議或傲嬌不滿。 |

---

## 🧠 大腦雙軌降級容錯架構 (Graceful Degradation)

為了確保 Mimo 能在**任何測試平台（包括無硬體連接的 PC 環境）**順暢運作，系統內建強大的雙軌降級容錯機制：

1. **OLED 與 GPIO 驅動捕獲**：
   在導入 `luma.oled` 與 `gpiozero` 時，系統會自動捕獲 `ImportError` 或 `OSError`。如果硬體或庫不存在，系統會無縫轉向 `MockOLEDController` 與 `MockGimbalController`。所有的表情渲染與舵機轉動角度將會以乾淨的 Log 形式輸出，配合網頁 UI 進行表情模擬，絕對不會崩潰。
2. **OpenCV 相機防護**：
   如果系統沒有檢測到 CSI 相機或 USB 攝像頭，OpenCV 背景人臉偵測線程會優雅地寫入日誌並關閉追蹤，但保留 API 級別的 Mock 人臉觸發，保證主語音大腦與 reminder scheduler 依然正常工作。
3. **OpenRouter 429 即時本地降級**：
   當雲端 OpenRouter API 面臨 upstream rate-limited (429) 或 endpoint 404 時，系統會在 0.1 秒內直接降級為本地運行的 Ollama (`gemma3:1b`)。同時，大腦會自動套用 `repeat_penalty: 1.2`、自適應 `num_predict` 長度限制，與後置退化重複過濾器，確保本地小模型在降級運作時維持極高穩定性，絕不發生無限重複死循環！這不僅避免了冗長的網路超時，更能確保 100% 的離線高可用性與可靠度！

