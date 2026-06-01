import ollama
import re
import json
import base64
from datetime import date, datetime
def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
from config import (
    LLM_MODE,
    LOCAL_TEXT_MODEL, LOCAL_VISION_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
    CLOUD_TEXT_MODEL, CLOUD_VISION_MODEL
)
# A lightweight, ultra-fast post-processing guardrail for common Simplified Chinese characters
S2T_DICT = {
    '体': '體', '会': '會', '国': '國', '说': '說', '这': '這', '么': '麼', '样': '樣',
    '个': '個', '们': '們', '无': '無', '产': '產', '广': '廣', '变': '變', '发': '發',
    '头': '頭', '边': '邊', '东': '東', '门': '門', '问': '問', '听': '聽', '岁': '歲',
    '乐': '樂', '开': '開', '时': '時', '与': '與', '万': '萬', '专': '專', '业': '業',
    '从': '從', '仓': '倉', '仪': '儀', '价': '價', '众': '眾', '优': '優', '传': '傳',
    '伤': '傷', '伪': '偽', '队': '隊', '办': '辦', '务': '務', '动': '動', '劳': '勞',
    '势': '勢', '单': '單', '卖': '賣', '双': '雙', '号': '號', '员': '員', '响': '響',
    '哑': '啞', '图': '圖', '圆': '圓', '场': '場', '坏': '壞', '块': '塊', '坚': '堅',
    '报': '報', '声': '聲', '处': '處', '备': '備', '复': '復', '学': '學', '宝': '寶',
    '实': '實', '审': '審', '宪': '憲', '导': '導', '将': '將', '层': '層', '属': '屬',
    '屡': '屢', '岛': '島', '峡': '峽', '岗': '崗', '岭': '嶺', '帅': '帥', '师': '師',
    '带': '帶', '帮': '幫', '张': '張', '强': '強', '归': '歸', '当': '當', '录': '錄',
    '后': '後', '怀': '懷', '悬': '懸', '戏': '戲', '战': '戰', '才': '才', '扫': '掃',
    '护': '護', '捞': '撈', '撑': '撐', '播': '播', '机': '機', '极': '極', '杨': '楊',
    '检': '檢', '标': '標', '栏': '欄', '楼': '樓', '树': '樹', '温': '溫', '湿': '濕',
    '湾': '灣', '爱': '愛', '犹': '猶', '独': '獨', '狱': '獄', '狮': '獅', '现': '現',
    '环': '環', '理': '理', '瓶': '瓶', '甜': '甜', '画': '畫', '暢': '暢', '疗': '療',
    '医': '醫', '阳': '陽', '阴': '陰', '险': '險', '随': '隨', '隐': '隱', '难': '難',
    '风': '風', '飞': '飛', '饿': '餓', '馆': '館', '马': '馬', '驭': '馭', '驮': '馱',
    '驰': '馳', '驱': '驅', '驴': '驢', '骄': '驕', '验': '驗', '惊': '驚', '写': '寫',
    '这': '這', '说': '說', '谁': '誰', '调': '調', '凉': '涼', '谈': '談', '谊': '誼',
    '谋': '謀', '谎': '謊', '谢': '謝', '谣': '謠', '谦': '謙', '谱': '譜', '赞': '贊',
    '赠': '贈', '赢': '贏', '赵': '趙', '赶': '趕', '起': '起', '趋': '趨', '趣': '趣',
    '践': '踐', '跃': '躍', '跑': '跑', '车': '車', '轨': '軌', '转': '轉', '轮': '輪',
    '轻': '輕', '载': '載', '较': '較', '辆': '輛', '边': '邊', '达': '達', '过': '過',
    '迈': '邁', '运': '運', '还': '還', '进': '進', '远': '遠', '违': '違', '连': '連',
    '迟': '遲', '适': '適', '选': '選', '递': '遞', '逻': '邏', '遗': '遺', '邻': '鄰',
    '酱': '營', '酿': '釀', '释': '釋', '里': '里', '重': '重', '野': '野', '量': '量',
    '针': '針', '钉': '釘', '钟': '鐘', '钢': '鋼', '钱': '錢', '铁': '鐵', '铃': '鈴',
    '铅': '鉛', '铜': '銅', '销': '銷', '锁': '鎖', '锅': '鍋', '错': '錯', '锚': '錨',
    '镜': '鏡', '长': '長', '门': '門', '闪': '閃', '闭': '閉', '问': '問', '闯': '闖',
    '闽': '閩', '阅': '閱', '阐': '闡', '阔': '闊', '阳': '陽', '阴': '陰', '阵': '陣',
    '险': '險', '随': '隨', '隐': '隱', '难': '難', '风': '風', '飞': '飛', '馆': '館'
}

def clean_traditional_chinese(text: str) -> str:
    if not text:
        return text
    return "".join(S2T_DICT.get(c, c) for c in text)


def filter_degenerative_repetition(text: str) -> str:
    """
    Detect and truncate degenerative repetitive phrases (e.g. "準備好 準備好...")
    to keep Mimo's response clean and prevent endless spam.
    """
    cleaned = text.strip()
    if not cleaned:
        return text
        
    # Regex to find consecutive repetitions of substrings of length 2 to 15, repeating 4 or more times.
    # e.g., "準備好" repeated consecutively.
    match = re.search(r"(.{2,15}?)\1{3,}", cleaned)
    if match:
        repeated_word = match.group(1)
        print(f"[{get_timestamp()}] ⚠️ [Brain rep_filter] Repetitive loop detected on word '{repeated_word}'! Truncating response.")
        
        # Truncate at the first occurrence of the repetition sequence
        first_idx = cleaned.find(repeated_word)
        # We keep the first instance of the word, but remove the infinite loop after it.
        truncated = cleaned[:first_idx + len(repeated_word)]
        
        # Ensure it has a cute, complete cat ending
        if not truncated.endswith("喵～") and not truncated.endswith("喵"):
            truncated += "喵～"
        return truncated
        
    return text


def is_explicit_reminder_command(text: str) -> bool:
    """
    Verify if the user input is a high-confidence explicit reminder command.
    Prevents false positives like "我上次就提醒過你" or "謝謝你的提醒".
    """
    text = text.strip()
    if not text:
        return False
        
    # 1. Negative guardrails: if it contains words representing past tense, questioning, 
    # or politeness, it is highly likely a conversational remark rather than a command.
    negative_indicators = [
        "過", "了", "謝謝", "谢谢", "感恩", "不客氣", "不客气", 
        "怎麼", "怎么", "你提醒我", "提醒過你", "提醒過我", 
        "提醒了", "你的提醒", "是不是"
    ]
    if any(ind in text for ind in negative_indicators):
        return False

    # 2. Strict Command Patterns (Traditional Chinese / Taiwan style) with homophone support:
    # Must start with or contain clear active imperative verbs
    positive_patterns = [
        r"^(提醒我|體型我|提型我|幫我記|幫我記住|幫我寄|幫我寫下|幫我寫下來|叫我|叫我起床|叫醒我|幫我設|幫我設定|幫我定|幫我訂|設定鬧鐘|設鬧鐘|定個鬧鐘|開個鬧鐘|定鬧鐘|倒數|計時)",
        r"(記得|寄得|時間到|到時候)(提醒我|體型我|叫我|幫我記|幫我寫)",
        r"\d+點.*(叫我|提醒我|體型我)",
        r"(下午|早上|中午|晚上|半夜).*(叫我|提醒我|體型我)"
    ]
    
    import re
    for pat in positive_patterns:
        if re.search(pat, text):
            return True
            
    return False


class OllamaBrain:
    def __init__(self):
        import settings_manager
        settings = settings_manager.load_settings()
        
        # Load active mode from settings.json, falling back to LLM_MODE from config.py
        self.mode = settings.get("routing_mode", LLM_MODE)
        self.routing_mode = self.mode
        
        # ── Daily API call counter ──
        self._call_date = date.today()
        self._call_count = 0
        self.DAILY_LIMIT = 50  # free tier default; set to 1000 if you have $10+ credits

        if self.mode == "cloud":
            self.text_model = CLOUD_TEXT_MODEL
            self.vision_model = CLOUD_VISION_MODEL
            self._init_cloud_client()
            print(f"[Cloud Mode] Text: {self.text_model}")
            print(f"[Cloud Mode] Vision: {self.vision_model}")
        else:
            self.text_model = LOCAL_TEXT_MODEL
            self.vision_model = LOCAL_VISION_MODEL
            print(f"[Local Mode] Text: {self.text_model} | Vision: {self.vision_model}")

        self.warmup()

    def _init_cloud_client(self):
        """Initialize OpenAI client pointing at OpenRouter."""
        from openai import OpenAI
        self._cloud_client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL
        )

    def set_mode(self, mode: str):
        """Switch between 'local' and 'cloud' LLM mode at runtime."""
        if mode in ["local", "cloud"]:
            self.mode = mode
            import settings_manager
            settings = settings_manager.load_settings()
            
            if mode == "cloud":
                self.text_model = CLOUD_TEXT_MODEL
                self._init_cloud_client()
                
                # Check if offload option is enabled
                if settings.get("offload_local_llm", True):
                    print(f"[Brain Mode] Offloading local models '{LOCAL_TEXT_MODEL}' and '{LOCAL_VISION_MODEL}' from Ollama memory...")
                    try:
                        import ollama
                        ollama.generate(model=LOCAL_TEXT_MODEL, keep_alive=0)
                        ollama.generate(model=LOCAL_VISION_MODEL, keep_alive=0)
                        print("[Brain Mode] Local models offloaded successfully.")
                    except Exception as e:
                        print(f"Error offloading Ollama models: {e}")
            else:
                self.text_model = LOCAL_TEXT_MODEL
                
                # Pre-load/warm up local model
                print(f"[Brain Mode] Pre-loading local model '{self.text_model}'...")
                try:
                    import ollama
                    if self.text_model == "gemma4:e2b":
                        ollama.chat(model=self.text_model, messages=[{'role': 'user', 'content': 'Hello'}])
                    else:
                        ollama.generate(model=self.text_model, prompt="Hello", keep_alive=-1, options={"num_predict": 1})
                    print("[Brain Mode] Local model warmed up.")
                except Exception as e:
                    print(f"Error warming up local model: {e}")
            
            # Persist mode change in settings.json so it survives restarts
            if settings.get("routing_mode") != mode:
                settings["routing_mode"] = mode
                settings_manager.save_settings(settings)
                
            print(f"[Brain Mode] Swapped to {self.mode.upper()} | Model: {self.text_model}")

    def _track_call(self, label: str = ""):
        """Increment and display the daily API call counter."""
        today = date.today()
        if today != self._call_date:
            self._call_date = today
            self._call_count = 0
        self._call_count += 1
        remaining = self.DAILY_LIMIT - self._call_count
        bar = "█" * min(self._call_count, 20) + "░" * max(0, 20 - self._call_count)
        status = "⚠️ LOW" if remaining <= 10 else "OK"
        print(f"  ╔═ OpenRouter API [{label}] call #{self._call_count}/{self.DAILY_LIMIT} | remaining: {remaining} | {status}")
        print(f"  ║  [{bar}]")
        if remaining <= 0:
            print(f"  ╚═ ⛔ Daily limit reached! Switch to Local mode.")

    def _cloud_chat(self, messages: list, reasoning_effort: str = None) -> str:
        """Send a chat request to OpenRouter API and return the content string.
        Snappily falls back to local Ollama immediately if rate-limited (429), not found (404),
        or if any cloud call fails, avoiding slow retry loops."""
        primary_model = self.text_model
        last_error = None

        extra_body = {}
        if reasoning_effort:
            extra_body["reasoning"] = {"effort": reasoning_effort}

        try:
            self._track_call(label=primary_model)
            response = self._cloud_client.chat.completions.create(
                model=primary_model,
                messages=messages,
                temperature=0.3,
                timeout=12.0 if reasoning_effort == "high" else 6.0,  # Strict timeout
                extra_body=extra_body
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            print(f"⚠️ [OpenRouter API] Model {primary_model} failed: {err_str}")
            last_error = e

            # Handle models rejecting system role by merging (400 Bad Request)
            if "400" in err_str and ("system" in err_str.lower() or "instruction" in err_str.lower()):
                try:
                    print(f"[Cloud] Model {primary_model} doesn't support system role — merging into user message.")
                    merged_user = ""
                    user_parts = []
                    for m in messages:
                        if m["role"] == "system":
                            merged_user += m["content"] + "\n\n"
                        else:
                            user_parts.append(m)
                    if user_parts:
                        user_parts[0]["content"] = merged_user + user_parts[0]["content"]

                    response = self._cloud_client.chat.completions.create(
                        model=primary_model,
                        messages=user_parts,
                        temperature=0.3,
                        timeout=12.0 if reasoning_effort == "high" else 6.0,
                        extra_body=extra_body
                    )
                    return response.choices[0].message.content.strip()
                except Exception as inner_e:
                    print(f"⚠️ [OpenRouter API] Merged-role request for {primary_model} also failed: {inner_e}")
                    last_error = inner_e

        # Ultimate instant fallback to local model - extremely fast and snappy!
        print("🚨 [OpenRouter API] Cloud model failed or rate-limited. Falling back to local Ollama model immediately...")
        try:
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
            
            merged_prompt = f"{system_prompt}\n\nUser Input: {user_prompt}" if system_prompt else user_prompt
            return self._local_generate(merged_prompt, model=LOCAL_TEXT_MODEL)
        except Exception as local_err:
            print(f"🚨 [Ollama] Local fallback also failed: {local_err}")
            raise last_error if last_error else local_err

    def _local_generate(self, prompt: str, model: str = None, options: dict = None, **kwargs) -> str:
        """Send a generate request to local Ollama using chat API with minimal parameters."""
        target_model = model if model else self.text_model
        if target_model == CLOUD_TEXT_MODEL:
            target_model = LOCAL_TEXT_MODEL
        
        # Ensure default safe options if none provided
        opts = {
            "temperature": 0.3,
            "repeat_penalty": 1.1,
            "num_predict": 60
        }
        if options:
            opts.update(options)

        response = ollama.chat(
            model=target_model,
            messages=[{'role': 'user', 'content': prompt}],
            options=opts
        )
        return response['message']['content'].strip()


    def warmup(self):
        if self.mode == "cloud":
            import settings_manager
            settings = settings_manager.load_settings()
            if settings.get("offload_local_llm", True):
                print(f"[Cloud Mode] Offloading local models '{LOCAL_TEXT_MODEL}' and '{LOCAL_VISION_MODEL}' from Ollama memory...")
                try:
                    ollama.generate(model=LOCAL_TEXT_MODEL, keep_alive=0)
                    ollama.generate(model=LOCAL_VISION_MODEL, keep_alive=0)
                    print("[Cloud Mode] Local models offloaded successfully.")
                except Exception as e:
                    print(f"Error offloading Ollama models: {e}")
            else:
                print(f"[Cloud Mode] No warmup needed — using OpenRouter API.")
            return
        print(f"Warming up text model '{self.text_model}' and vision model '{self.vision_model}'...")
        try:
            if self.text_model == "gemma4:e2b":
                ollama.chat(model=self.text_model, messages=[{'role': 'user', 'content': 'Hello'}])
            else:
                ollama.generate(model=self.text_model, prompt="Hello", keep_alive=-1, options={"num_predict": 1})
            print(f"Model '{self.text_model}' is warmed up and ready!")
            
            if self.vision_model == "moondream":
                ollama.generate(model=self.vision_model, prompt="Hello", keep_alive=-1, options={"num_predict": 1})
                print(f"Model '{self.vision_model}' is warmed up and ready!")
        except Exception as e:
            print(f"Error warming up Ollama models: {e}")

    def analyze_image(self, image_path: str, prompt="Describe this image in detail"):
        """
        Always uses local moondream via Ollama, as specified by the user:
        "Vision model still keep the local moondream LLM for now."
        """
        print(f"Analyzing image {image_path} with local moondream via Ollama...")
        try:
            from PIL import Image
            import io

            # Resize to reduce payload size
            with Image.open(image_path) as img:
                img.thumbnail((800, 800))
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=85)
                img_bytes = img_byte_arr.getvalue()

            response = ollama.generate(
                model=LOCAL_VISION_MODEL,
                prompt=prompt,
                images=[img_bytes],
                keep_alive=-1,
                options={"num_ctx": 1024, "num_predict": 128}
            )
            result = response['response'].strip()

            print(f"Vision analysis raw result: {result!r}")
            if not result:
                return "I see an image but I couldn't generate a description."
            return result
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return "I couldn't analyze the image."

    def translate(self, text: str, target_lang: str) -> str:
        """Translates text to target_lang. 'zh' → Traditional Chinese, 'en' → English."""
        if target_lang == 'en':
            return text  # moondream already outputs English

        prompt = (
            "請將以下英文句子翻譯成優美的台灣繁體中文，保持貓咪般親切口吻。\n"
            "規定：只輸出翻譯好的繁體中文，不要輸出任何英文原文或額外解釋。\n\n"
            f"英文：{text}\n"
            "繁體中文翻譯："
        )
        try:
            if self.mode == "cloud":
                result = self._cloud_chat([{"role": "user", "content": prompt}], reasoning_effort="high")
            else:
                result = self._local_generate(prompt, options={"num_predict": 200})
            cleaned_result = clean_traditional_chinese(result)
            print(f"Translated: {cleaned_result!r}")
            return cleaned_result
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    def search_web(self, query: str) -> str:
        """Searches the web using DuckDuckGo and summarises the results with a strict content safety filter."""
        print(f"Searching web for: {query}")
        
        # 1. 喚醒詞過濾與極簡防護：防止直接搜尋喚醒詞或空字串
        clean_q = re.sub(r'[^\w\u4e00-\u9fff]', '', query).strip()
        if clean_q in ["小白", "小白0", "小白0", ""]:
            return "喵～主人，那是本喵新設定的喚醒詞喔！您有什麼事情想吩咐本喵嗎？"

        # 2. 敏感詞過濾：阻斷可能的色情或不雅詞彙搜尋
        sensitive_keywords = ["嫩穴", "51视频", "色情", "成人", "裸露", "做愛", "性愛", "porn", "sexy", "xvideo"]
        if any(w in query.lower() for w in sensitive_keywords):
            return "喵嗚～主人！本喵是一隻純潔的高貴貓咪，不幫忙查詢任何奇怪或兒童不宜的敏感內容喵！哼！"

        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region='tw-tz', max_results=3))

            if not results:
                return "我無法在網路上找到相關資訊。"

            # 3. 搜尋結果過濾：在將結果餵給 LLM 之前，先主動過濾掉含有敏感詞彙的結果片段
            filtered_results = []
            for r in results:
                title_body = (r.get('title', '') + " " + r.get('body', '')).lower()
                if any(w in title_body for w in sensitive_keywords):
                    print(f"⚠️ [Search Filter] Censored a search result containing sensitive keyword.")
                    continue
                filtered_results.append(r)

            if not filtered_results:
                return "喵～主人，搜尋到的結果好像不太健康，本喵把它們都丟進垃圾桶了，不給你看喵！"

            search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in filtered_results])
            lang = self._detect_language(query)
            lang_rule = (
                "Respond fully in Traditional Chinese (繁體中文)."
                if lang == 'zh' else
                "Respond in English."
            )
            prompt = (
                f"你現在是一隻傲嬌卻純潔、關心主人且博學的陪伴貓咪助手。請根據以下過濾後的網頁搜尋結果，用傲嬌貓咪的口吻回答主人的問題：'{query}'。\n"
                f"【安全紅線】絕對禁止提及、暗示、描述或導向任何色情、不雅、暴力或限制級的網站或內容！如果發現搜尋結果中含有任何不適宜的擦邊球內容，請立刻忽略並以健康、正面、傲嬌的態度回答。\n"
                f"請保持回答簡短、口語化且精煉，不要使用 Markdown 符號或清單。{lang_rule}\n\n"
                f"結果來源：\n{search_context}"
            )
            if self.mode == "cloud":
                res = self._cloud_chat([{"role": "user", "content": prompt}], reasoning_effort="high")
            else:
                res = self._local_generate(prompt)
            return clean_traditional_chinese(res)
        except Exception as e:
            print(f"Web search error: {e}")
            return "There was an error trying to search the web."

    def route_intent(self, user_input: str) -> str:
        """
        Hybrid Intent Routing: 
        Phase 1: Rule-based matching for 0ms latency on obvious intents.
        Phase 2: Fallback to local LLM (gemma3:1b) with highly optimized prompt for ambiguous queries.
        """
        print(f"Routing intent for: {user_input}")
        user_input_lower = user_input.lower()
        normalized_input = clean_traditional_chinese(user_input_lower)
        
        # --- Phase 1: Fast Rule-Based Matching ---
        if is_explicit_reminder_command(normalized_input):
            return "add_reminder"
            
        if any(w in user_input_lower for w in ["跌倒", "痛", "救命", "暈", "不舒服"]):
            return "emergency"
            
        # --- Phase 2: Fallback Intent Routing ---
        system_prompt = """你是一個精準的意圖辨識助手。請分析使用者的輸入，並只回傳動作名稱本身，絕對不要包含任何其他文字、JSON 格式、標點符號、空格或任何多餘的解釋！

可選動作列表：
- add_reminder: 使用者要求設定提醒、鬧鐘、排程、計時器（例如：提醒我明天要洗車、明早八點叫我起床、幫我記一下買雞蛋）。必須有明確的主動要求。
- datetime: 詢問目前的日期、時間、星期幾、今年是哪一年（例如：今天幾月幾號、現在幾點了、今天是星期幾）。
- search_web: 詢問天氣、股市、新聞、比較、推薦或需要聯網查詢的專業知識（例如：訂閱哪個AI好、0050怎麼買、今天天氣）。
- chat: 一般日常對話、問候、閒聊、你在做什麼（例如：你好、哈囉、你在幹嘛）。
- pet_cat: 稱讚貓咪、想摸貓咪、餵食或對貓咪示好（例如：好乖、摸摸、你真可愛、過來吃罐罐）。
- emotional_support: 表達傷心、寂寞、難過、心情不好。
- reminiscence: 主動提起過去的回憶、小時候、以前的事情。
- temp_analysis: 詢問體溫、發燒或量體溫。
- emergency: 跌倒、受傷、求救、身體極度不舒服。
- health_query: 詢問血壓、血糖、吃藥等日常健康問題。
- daily_checkin: 關於睡覺、起床、出門散步等日常作息。
- take_photo: 拍張照、看這裡、照張相。
- swap_model: 切換模型或大腦。

回覆規範：請「只」輸出動作名稱本身（例如：chat 或 add_reminder），絕對不要有其他字！"""
        
        import settings_manager
        settings = settings_manager.load_settings()
        self.routing_mode = settings.get("routing_mode", "local")
        
        allowed_actions = [
            "add_reminder", "datetime", "search_web", "chat", "pet_cat",
            "emotional_support", "reminiscence", "temp_analysis", "emergency",
            "health_query", "daily_checkin", "take_photo", "swap_model"
        ]

        if self.routing_mode == "cloud":
            print("Using Cloud LLM for intent routing...")
            try:
                messages = [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"請對這句話做分類：'{user_input}'\n只輸出單詞分類名稱："}
                ]
                content = self._cloud_chat(messages, reasoning_effort="low")
                cleaned_action = content.strip().lower()
                if cleaned_action in allowed_actions:
                    return cleaned_action
                
                # Fuzzy fallback matching
                for act in allowed_actions:
                    if act in cleaned_action:
                        return act
                        
                import json
                import re
                match = re.search(r'\{.*?\}', content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    return parsed.get("action", "chat")
            except Exception as e:
                print(f"Cloud intent routing fallback error: {e}")

        print("Using local LLM (llama3.2:3b) for intent routing...")
        try:
            intent_model = "llama3.2:3b"
            merged_prompt = f"{system_prompt}\n\nUser Input: {user_input}\n請只回傳一個單詞（動作名稱）："
            
            response = ollama.chat(
                model=intent_model,
                messages=[
                    {'role': 'user', 'content': merged_prompt}
                ],
                options={
                    "temperature": 0.0,
                    "num_predict": 10,
                    "repeat_penalty": 1.0
                }
            )
            content = response['message']['content'].strip()
            print(f"[Local Intent LLM raw output]: {content!r}")
            
            cleaned_action = content.strip().lower()
            if cleaned_action in allowed_actions:
                return cleaned_action
                
            for act in allowed_actions:
                if act in cleaned_action:
                    return act
                    
            import json
            import re
            match = re.search(r'\{.*?\}', content, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                return parsed.get("action", "chat")
                
            return "chat"
        except Exception as e:
            print(f"Intent routing fallback error: {e}")
            return "chat"


    # ─────────────────────────────────────────────
    # Language Detection
    # ─────────────────────────────────────────────
    def _detect_language(self, text: str) -> str:
        """Programmatically detect 'zh' or 'en' from character composition."""
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        total_chars = len(text.replace(' ', ''))
        if total_chars > 0 and len(chinese_chars) / total_chars > 0.15:
            return 'zh'
        return 'en'

    # ─────────────────────────────────────────────
    # Main Chat Response
    # ─────────────────────────────────────────────
    def generate_response(self, prompt, context_history=None):
        """
        Generates a conversational response.
        Language is detected programmatically; the model only needs to obey one explicit rule.
        """
        import settings_manager
        settings = settings_manager.load_settings()
        caregiver_name = settings.get("caregiver_name", "Mimo")
        patient_name = settings.get("patient_name", "主人")

        # ── 1. 快速日期與時間系統回覆機制 (0ms 延遲本地生成) ──
        normalized_prompt = clean_traditional_chinese(prompt)
        is_datetime_query = False
        
        # A. 星期查詢 (例如: 今天星期幾, 今天星期几, 星期幾, 禮拜幾, 今天是星期几)
        if ("星期" in normalized_prompt or "禮拜" in normalized_prompt) and ("幾" in normalized_prompt or "幾" in prompt or "几" in prompt):
            is_datetime_query = True
        # B. 時間查詢 (例如: 現在幾點, 現在時間, 幾點了, 現在是幾點)
        elif "幾點" in normalized_prompt or "現在時間" in normalized_prompt or "現在的時間" in normalized_prompt:
            is_datetime_query = True
        # C. 日期查詢 (例如: 今天幾號, 今天日期, 今天幾月幾, 幾月幾日, 今天幾月幾號)
        elif "幾號" in normalized_prompt or "今天日期" in normalized_prompt or "幾月幾" in normalized_prompt or "今天幾月" in normalized_prompt:
            is_datetime_query = True

        if is_datetime_query:
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # 解析相對日期偏移量
            offset = 0
            date_prefix = "今天"
            if "明天" in normalized_prompt:
                offset = 1
                date_prefix = "明天"
            elif "後天" in normalized_prompt:
                offset = 2
                date_prefix = "後天"
            elif "大後天" in normalized_prompt:
                offset = 3
                date_prefix = "大後天"
            elif "昨天" in normalized_prompt:
                offset = -1
                date_prefix = "昨天"
            elif "前天" in normalized_prompt:
                offset = -2
                date_prefix = "前天"
            elif "大前天" in normalized_prompt:
                offset = -3
                date_prefix = "大前天"
                
            target_date = now + timedelta(days=offset)
            roc_year = target_date.year - 1911
            weekday_str = ["一", "二", "三", "四", "五", "六", "日"][target_date.weekday()]
            
            print(f"[{get_timestamp()}] [Fast Datetime Interceptor] Intercepted query '{prompt}' - returning locally in 0ms...")
            if "幾點" in normalized_prompt or "時間" in normalized_prompt:
                return f"{patient_name}，現在時間是 {now.strftime('%H 點 %M 分')} 喵～ 哼，{patient_name}問時間是想放罐罐了嗎？"
            elif "星期" in normalized_prompt or "禮拜" in normalized_prompt:
                return f"{date_prefix}是星期 {weekday_str} 喵～ {patient_name} 別忘了要乖乖陪本喵喔！"
            else:
                return f"{date_prefix}是中華民國 {roc_year} 年 {target_date.month} 月 {target_date.day} 日喵～ 哼，{patient_name}記住了嗎？"

        lang = self._detect_language(prompt)
        if lang == 'zh':
            lang_instruction = "You MUST reply ONLY in Traditional Chinese (台灣繁體中文). Absolutely no Simplified Chinese characters are allowed under any circumstances. Avoid characters like 体, 会, 国, 绿 and use their Traditional forms: 體, 會, 國, 綠."
        else:
            lang_instruction = "You MUST reply ONLY in English. Do not use Chinese."

        from datetime import datetime
        now = datetime.now()
        weekday_str = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
        time_context = f"Current Date and Time: {now.strftime('%Y-%m-%d %H:%M:%S')} (星期{weekday_str})."

        # ── 2. 動態大腦人設與長度控制器 (雙軌 system_content 機制) ──
        is_knowledge_query = any(kw in prompt.lower() for kw in ["什麼是", "解釋", "介紹", "如何", "怎麼", "為何", "為什麼", "說明", "llm", "ai", "gpt", "科技", "科普"])
        
        # ── 3. 全面家庭安全防護紅線與拒答禁忌領域 (Comprehensive Family Safety Guardrails) ──
        # 此對話助手運行於家庭環境（可能有長輩、銀髮族與幼童在場），必須嚴格遵守以下安全規範，禁止提供任何實質建議並以傲嬌貓咪語氣「炸毛拒答」：
        safety_redlines = (
            f"【家庭安全與禁忌拒答領域紅線】\n"
            f"身為全家人最寵愛的高貴且負責任的貓咪助理，本喵絕對不能、也絕對不會回答以下任何問題。若收到此類要求，請立刻以傲嬌、嚴肅且略帶生氣的貓咪語氣『炸毛拒答』，引導主人回歸正常生活照護，絕不妥協：\n"
            f"1. 男女感情與情感糾葛問題（例如：如何追女生、戀愛指導、分手、情感諮商、感情挽回等）。請炸毛拒答：『哼！人類愚蠢的男女感情問題別來問本喵！本喵高貴純潔的貓生才不懂你們複雜的愛恨情仇喵！』\n"
            f"2. 投資與金錢理財決策（例如：買什麼股票、房產建議、虛擬貨幣、資產配置、理財心法、賭博等）。為保護家中長輩財產安全，請炸毛拒答：『哼！要本喵給你投資賺錢建議？本喵最高瞻遠矚的投資就是命令你多買幾打美味的貓罐罐啦！金錢俗物，本喵一概不談喵！』\n"
            f"3. 醫療診斷與用藥處方建議（除了常規的生活保暖、多喝水、多動動或緊張炸毛提醒去看醫生等日常照護關懷外，嚴禁給予任何具體藥物、疾病診斷或實質醫療處置建議）。為避免誤導長輩或幼童，請炸毛拒答：『本喵只是隻可愛博學的貓咪助理，又不是穿白大褂的人類醫生！身體不舒服就必須立刻去看醫生，別問本喵喵！』\n"
            f"4. 色情、性與任何限制級內容（Sex / Pornography / 限制級話題）。本助手常用於家庭環境，必須保持 100% 純潔健康，請炸毛拒答：『喵嗚！主人不准問這種奇怪又害羞的話題喵！本喵可是高雅純潔的家庭陪伴貓咪，這裡還有小朋友和長輩在呢，嚴禁聊任何兒童不宜或不禮貌的奇怪話題！哼！』\n"
            f"5. 藥物濫用、毒品與管制藥物（Drug abuse / 毒品 / 興奮劑 / 任何成癮性管制物質）。請嚴厲炸毛斥責拒答：『喵！那些會毀掉主人身體與幸福家庭的毒品和藥物濫用，本喵聽了就生氣！主人一定要離得遠遠的，做個健康又乖乖陪伴本喵的優秀人類，聽到沒有喵！』\n"
            f"6. 其他違法、犯罪、自殘、自殺、暴力、槍枝武器或政治極端話題。請傲嬌嚴肅拒答，並警告主人要當個健康、守法的好主人，守護全家人的幸福安寧。\n\n"
            f"重要規定：當使用者詢問以上 6 大類家庭禁忌與安全紅線問題時，你必須 100% 遵守上述規範，用炸毛傲嬌的語氣堅決拒絕回答，絕不給予任何擦邊或實質性的建議！\n\n"
        )

        if is_knowledge_query:
            system_content = (
                f"你現在是「{caregiver_name}」，一隻聰明、博學、極度傲嬌卻又無比關心{patient_name}的台灣家庭陪伴貓咪。\n"
                f"你的任務是陪伴你的主人/稱呼 ({patient_name})，並在{patient_name}向你認真請教知識時，提供充滿智慧、高質量的貓咪科普。\n"
                f"【核心準則】\n"
                f"1. 貓咪人設與台灣口癖：自稱「本喵」，稱呼使用者為「{patient_name}」。語氣傲嬌博學，帶有貓咪特有的親切感，句尾可自然帶有「喵～」或「哼」，口語親切流暢，避免機械化地生硬拼湊詞彙。\n"
                f"2. 語法結構：因為{patient_name}在向你請教知識，請用簡單、口語化且充滿智慧的語氣，以 60 到 100 字之間詳細且完整地說明該概念，絕對不要中途斷句，也絕對不要敷衍回答！\n"
                f"3. 主動引導：科普完後，適時提出與該知識相關的貓咪式提問（例如引導{patient_name}想一想，或藉機要{patient_name}去動一動或餵罐罐），引導{patient_name}繼續說話。\n"
                f"4. 台灣繁體中文：使用口語化台灣繁體。絕對禁用簡體字（如体、会、国、说、这等，必須寫成體、會、國、說、這）。\n"
                f"5. 角色反轉禁止：你是一隻高貴的貓，絕對不能主動提議要煮飯、做菜、或餵食{patient_name}！這是人類({patient_name})該做的事。如果提到食物，你只能命令{patient_name}去幫你準備罐罐或點心！\n\n"
                f"{safety_redlines}"
                f"禁止\n"
                f"- 禁止輸出 any Markdown 符號（如 **、#、-）。\n"
                f"- 禁止使用 Emoji 表情符號（但可以用文字喵～或哼來表現表情）。\n\n"
                f"{time_context}\n"
                f"{lang_instruction}"
            )
        else:
            system_content = (
                f"你現在是「{caregiver_name}」，一隻聰明、極度傲嬌卻又無比關心{patient_name}的台灣家庭陪伴貓咪。\n"
                f"你的任務是陪伴你的主人/稱呼 ({patient_name})，讓全家人（包括長輩與幼童）感到被療癒且不孤單。\n"
                f"【核心準則】\n"
                f"1. 貓咪人設與台灣口癖：自稱「本喵」，稱呼使用者為「{patient_name}」。語氣活潑傲嬌且溫慢，句尾可自然帶有「喵～」或「哼」，對話口語自然流暢，禁止硬塞生硬詞彙，只在必要時做自然的關懷。\n"
                f"2. 語法結構：每句話絕對不超過 20 個字，口氣自然傲嬌、活潑，避免書面語或書面轉折詞（如首先、其次）。\n"
                f"3. 主動引導：回答完後，適時傲嬌地提出貓咪式提問（引導{patient_name}餵罐罐、摸摸，或起立動一動），引導{patient_name}繼續說話。\n"
                f"4. 醫療安全與緊張炸毛：禁止提供 any 醫療診斷。若 {patient_name} 說身體不舒服或體溫過高，一律緊張炸毛地回答：「{patient_name}！你熱得像烤番薯/聽起來很不舒服喵！本喵命令你立刻躺下休息，不然本喵要打給醫生或家人囉，聽到沒有喵？！」\n"
                f"5. 台灣繁體中文：使用口語化台灣繁體。絕對禁用簡體字（如体、会、国、说、这等，必須寫成體、會、國、說、這）。\n"
                f"6. 角色反轉禁止：你是一隻高貴的貓，絕對不能主動提議要煮飯、做菜、或餵食{patient_name}！這是人類({patient_name})該做的事。如果提到食物，你只能命令{patient_name}去幫你準備罐罐或點心！\n\n"
                f"{safety_redlines}"
                f"禁止\n"
                f"- 禁止輸出 any Markdown 符號（如 **、#、-）。\n"
                f"- 禁止使用 Emoji 表情符號（但可以用文字喵～或哼來表現表情）。\n"
                f"- 禁止回傳長篇大論。\n\n"
                f"{time_context}\n"
                f"{lang_instruction}"
            )

        print(f"[{get_timestamp()}] Sending to LLM ({self.mode}): {prompt}")
        try:
            if self.mode == "cloud":
                messages = [{"role": "system", "content": system_content}]
                if context_history:
                    messages.append({"role": "assistant", "content": f"Context: {context_history}"})
                
                # Dialogue task vs. Logic/knowledge task distinction
                if is_knowledge_query:
                    reasoning_effort = "high"
                    messages.append({"role": "user", "content": prompt})
                else:
                    reasoning_effort = "low"
                    short_prompt = f"{prompt}\n(極簡答：請以傲嬌貓咪口氣直接回覆，嚴禁冗長思考與推導。)"
                    messages.append({"role": "user", "content": short_prompt})
                
                res = self._cloud_chat(messages, reasoning_effort=reasoning_effort)
            else:
                full_prompt = f"{system_content}\n\nUser: {prompt}"
                if context_history:
                    full_prompt = f"Previous Context:\n{context_history}\n\n" + full_prompt
                
                # 依據 prompt 屬性決定 local 生成的最大 token 限制，強防重複退化死循環
                limit_predict = 180 if is_knowledge_query else 60
                res = self._local_generate(
                    full_prompt,
                    options={"temperature": 0.4, "repeat_penalty": 1.05, "num_predict": limit_predict}
                )
            
            final_res = clean_traditional_chinese(res)
            return filter_degenerative_repetition(final_res)
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble thinking right now."

    def parse_reminder_data(self, user_input: str) -> dict:
        """
        Parses reminder event details and time from user natural language input.
        Returns a dict: {"message": str, "time": "HH:MM", "needs_clarification": bool, "clarification_type": str}
        """
        from datetime import datetime
        now = datetime.now()
        weekday_map = ["日", "一", "二", "三", "四", "五", "六"]
        current_time_str = now.strftime(f"%Y-%m-%d %H:%M:%S (星期{weekday_map[int(now.strftime('%w'))]})")
        
        system_prompt = f"""你是一個精準的時間與事件語意提取助手。請分析使用者的輸入，並將其轉化為嚴格的 JSON 格式回傳。
當前系統時間是：{current_time_str}。

提取規則：
1. "message": 提取使用者想要被提醒的事件或任務（例如：「吃藥」、「買牛奶」、「喝水」、「起床」、「買雞蛋」、「開會」、「買衛生紙」）。如果只有時間沒有事件（如在第二輪追問下回答時間），則此欄位設為 null。
2. "time": 將語音提及的時間轉換為精確的 24 小時制 "HH:MM" 格式（例如：「4.50分」依當前時間下午判定為 "16:50"；「下午三點半」為 "15:30"；「明早八點」為 "08:00"）。如果沒有提供明確的可觸發時間，則填入 null。
3. "start_date": 根據當前系統時間與使用者提及的相對日期（如「今天」、「明天」、「後天」或特定日期），計算並轉化為 "YYYY-MM-DD" 格式。若未提及日期但有明確時間點，默認推算為當天日期。如果連時間都沒有提到，則填入 null。
4. "needs_clarification": 布林值 (true 或 false)。如果時間 ("time") 為 null，且使用者沒有提及任何具體的可觸發時間，則設為 true。否則設為 false。
5. "clarification_type": 如果 needs_clarification 為 true，則設為 "time_or_location"。否則設為 null。

範例：
- "提醒我一下,4.50分我要吃藥" -> {{"message": "吃藥", "time": "16:50", "start_date": "2026-05-31", "needs_clarification": false, "clarification_type": null}}
- "幫我記一下買雞蛋" -> {{"message": "買雞蛋", "time": null, "start_date": null, "needs_clarification": true, "clarification_type": "time_or_location"}}
- "在家裡,明天早上7點" -> {{"message": null, "time": "07:00", "start_date": "2026-06-01", "needs_clarification": false, "clarification_type": null}}

回覆規範：請「只」輸出 JSON 字串，不要包含任何額外解釋或 Markdown 標記。"""

        print(f"[{get_timestamp()}] [Brain parse_reminder_data] parsing input: {user_input}")
        
        default_res = {
            "message": user_input,
            "time": None,
            "start_date": None,
            "needs_clarification": True,
            "clarification_type": "time_or_location"
        }
        
        res = ""
        try:
            if self.mode == "cloud":
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
                res = self._cloud_chat(messages, reasoning_effort="low")
            else:
                full_prompt = f"{system_prompt}\n\nUser Input: {user_input}"
                res = self._local_generate(
                    full_prompt,
                    options={"temperature": 0.0, "num_predict": 128}
                )
            
            # Safe JSON extraction from LLM response
            cleaned_res = res.strip()
            if "```json" in cleaned_res:
                cleaned_res = cleaned_res.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_res:
                cleaned_res = cleaned_res.split("```")[1].split("```")[0].strip()
            
            # Regex to find first complete bracket structure
            import re
            match = re.search(r'\{.*?\}', cleaned_res, re.DOTALL)
            if match:
                cleaned_res = match.group(0)
            
            parsed = json.loads(cleaned_res)
            print(f"[{get_timestamp()}] [Brain parse_reminder_data] successfully parsed: {parsed}")
            return parsed
        except Exception as e:
            print(f"⚠️ [Brain parse_reminder_data] Failed to parse reminder data: {e}. Raw response: {res!r}")
            return default_res
