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
    GEMINI_API_KEY, CLOUD_TEXT_MODEL, CLOUD_VISION_MODEL
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



class OllamaBrain:
    def __init__(self):
        self.mode = LLM_MODE
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
        """Initialize OpenAI-compatible client pointing at Google Gemini API."""
        from openai import OpenAI
        self._cloud_client = OpenAI(
            api_key=GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

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
        print(f"  ╔═ Gemini API [{label}] call #{self._call_count}/{self.DAILY_LIMIT} | remaining: {remaining} | {status}")
        print(f"  ║  [{bar}]")
        if remaining <= 0:
            print(f"  ╚═ ⛔ Daily limit reached! Switch to Local mode.")

    def _cloud_chat(self, messages: list) -> str:
        """Send a chat request to Google Gemini API and return the content string.
        Snappily falls back to local Ollama immediately if rate-limited (429), not found (404),
        or if any cloud call fails, avoiding slow retry loops."""
        primary_model = self.text_model
        last_error = None

        try:
            self._track_call(label=primary_model)
            response = self._cloud_client.chat.completions.create(
                model=primary_model,
                messages=messages,
                temperature=0.3,
                timeout=6.0  # Strict timeout to prevent client thread from freezing
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            print(f"⚠️ [Gemini API] Model {primary_model} failed: {err_str}")
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
                        timeout=6.0
                    )
                    return response.choices[0].message.content.strip()
                except Exception as inner_e:
                    print(f"⚠️ [Gemini API] Merged-role request for {primary_model} also failed: {inner_e}")
                    last_error = inner_e

        # Ultimate instant fallback to local model - extremely fast and snappy!
        print("🚨 [Gemini API] Cloud model failed or rate-limited. Falling back to local Ollama model immediately...")
        try:
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
            
            # 依據 prompt 決定適當的 num_predict (防範 1B 小模型重複退化)
            is_knowledge = any(kw in user_prompt.lower() for kw in ["什麼是", "解釋", "介紹", "如何", "怎麼", "為何", "為什麼", "說明", "llm", "ai", "gpt", "科技", "科普"])
            limit_predict = 180 if is_knowledge else 60
            
            ollama_response = ollama.chat(
                model=LOCAL_TEXT_MODEL,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                keep_alive=-1,
                options={"temperature": 0.4, "repeat_penalty": 1.2, "num_predict": limit_predict}
            )
            return ollama_response['message']['content'].strip()
        except Exception as local_err:
            print(f"🚨 [Ollama] Local fallback also failed: {local_err}")
            raise last_error if last_error else local_err

    def _local_generate(self, prompt: str, options: dict = None, **kwargs) -> str:
        """Send a generate request to local Ollama and return the response string."""
        default_options = {"temperature": 0.4, "repeat_penalty": 1.2, "num_predict": 60}
        if options:
            default_options.update(options)
            
        response = ollama.generate(
            model=self.text_model,
            prompt=prompt,
            keep_alive=-1,
            options=default_options,
            **kwargs
        )
        return response['response'].strip()


    def warmup(self):
        if self.mode == "cloud":
            print(f"[Cloud Mode] No warmup needed — using Gemini API.")
            return
        print(f"Warming up text model '{self.text_model}' and vision model '{self.vision_model}'...")
        try:
            ollama.generate(model=self.text_model, prompt="Hello", keep_alive=-1, options={"num_predict": 1})
            print(f"Model '{self.text_model}' is warmed up and ready!")
            ollama.generate(model=self.vision_model, prompt="Hello", keep_alive=-1, options={"num_predict": 1})
            print(f"Model '{self.vision_model}' is warmed up and ready!")
        except Exception as e:
            print(f"Error warming up Ollama models: {e}")

    def analyze_image(self, image_path: str, prompt="Describe this image in detail"):
        """
        Cloud mode: sends image to Gemini vision model (gemini-2.5-flash).
        Local mode: uses local moondream via Ollama.
        """
        print(f"Analyzing image {image_path} with {self.vision_model} [{self.mode}]...")
        try:
            from PIL import Image
            import io

            # Resize to reduce payload size in both modes
            with Image.open(image_path) as img:
                img.thumbnail((800, 800))
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=85)
                img_bytes = img_byte_arr.getvalue()

            if self.mode == "cloud":
                import base64
                # Encode image as base64 for Gemini multimodal API
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }]
                self._track_call(label=self.vision_model)
                response = self._cloud_client.chat.completions.create(
                    model=self.vision_model,
                    messages=messages,
                )
                result = response.choices[0].message.content.strip()
            else:
                response = ollama.generate(
                    model=self.vision_model,
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
            "Translate the following text STRICTLY to Traditional Chinese (台灣繁體中文). "
            "Absolutely NO Simplified Chinese characters are allowed (e.g. use 體 instead of 体, 會 instead of 会, 國 instead of 国, 臺/台 instead of 台, 綠 instead of 绿).\n"
            "Output ONLY the translated text in Traditional Chinese, nothing else.\n\n"
            f"Text: {text}\n"
            "Translation:"
        )
        try:
            if self.mode == "cloud":
                result = self._cloud_chat([{"role": "user", "content": prompt}])
            else:
                result = self._local_generate(prompt, options={"num_predict": 200})
            cleaned_result = clean_traditional_chinese(result)
            print(f"Translated: {cleaned_result!r}")
            return cleaned_result
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    def search_web(self, query: str) -> str:
        """Searches the web using DuckDuckGo and summarises the results."""
        print(f"Searching web for: {query}")
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region='tw-tz', max_results=3))

            if not results:
                return "我無法在網路上找到相關資訊。"

            search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
            lang = self._detect_language(query)
            lang_rule = (
                "Respond fully in Traditional Chinese (繁體中文)."
                if lang == 'zh' else
                "Respond in English."
            )
            prompt = (
                f"Answer the query: '{query}' based on these results. "
                f"Keep it short, concise, and direct, no markdown or lists. {lang_rule}\n\n"
                f"Results:\n{search_context}"
            )
            if self.mode == "cloud":
                res = self._cloud_chat([{"role": "user", "content": prompt}])
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
        
        # --- Phase 1: Fast Rule-Based Matching ---
        if any(w in user_input_lower for w in ["跌倒", "痛", "救命", "暈", "不舒服"]):
            return "emergency"
        if any(w in user_input_lower for w in ["血壓", "藥", "血糖"]):
            return "health_query"
        if any(w in user_input_lower for w in ["體溫", "溫度", "發燒", "量溫度"]):
            return "temp_analysis"
        if any(w in user_input_lower for w in ["拍", "看", "這是什麼", "照片"]):
            return "take_photo"
        if any(w in user_input_lower for w in ["切換", "模型", "聰明一點", "換一個"]):
            return "swap_model"
        if any(w in user_input_lower for w in ["天氣", "股票", "股市", "新聞", "匯率", "台積電"]) and not any(w in user_input_lower for w in ["幾點", "星期", "幾號"]):
            return "search_web"
        if any(w in user_input_lower for w in ["散步", "起床", "睡醒", "睡覺"]):
            return "daily_checkin"
        if any(w in user_input_lower for w in ["以前", "小時候", "做工的時候", "年輕的時候"]):
            return "reminiscence"
        if any(w in user_input_lower for w in ["有乖乖", "我有", "走了", "步"]):
            return "praise_affirmation"
        if any(w in user_input_lower for w in ["寂寞", "孤單", "沒人", "陪我"]):
            return "emotional_support"
        if any(w in user_input_lower for w in ["摸摸", "乖貓", "可愛", "好乖"]):
            return "pet_cat"
            
        # --- Phase 2: Fallback Intent Routing ---
        system_prompt = """Reply ONLY with JSON {"action":"..."}.
Actions: chat, take_photo, search_web, swap_model, emergency, health_query, daily_checkin, reminiscence, praise_affirmation, emotional_support, pet_cat, temp_analysis.
Output no other text."""
        
        if self.mode == "cloud":
            print("Using Cloud LLM for intent routing...")
            try:
                messages = [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_input}
                ]
                content = self._cloud_chat(messages)
                import json
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                parsed = json.loads(content.strip())
                return parsed.get("action", "chat")
            except Exception as e:
                print(f"Cloud intent routing fallback error: {e}")
                # 若雲端失敗，繼續嘗試本地模型

        print("Falling back to local LLM for intent routing...")
        try:
            response = ollama.chat(
                model=LOCAL_TEXT_MODEL,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_input}
                ],
                format='json',
                keep_alive=-1,
                options={"num_predict": 15, "temperature": 0.0}
            )
            content = response['message']['content']
            import json
            parsed = json.loads(content)
            return parsed.get("action", "chat")
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
        patient_name = settings.get("patient_name", "奴才")

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
            from datetime import datetime
            now = datetime.now()
            roc_year = now.year - 1911
            weekday_str = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
            
            print(f"[{get_timestamp()}] [Fast Datetime Interceptor] Intercepted query '{prompt}' - returning locally in 0ms...")
            if "幾點" in normalized_prompt or "時間" in normalized_prompt:
                return f"{patient_name}，現在時間是 {now.strftime('%H 點 %M 分')} 喵～ 哼，{patient_name}問時間是想放罐罐了嗎？"
            elif "星期" in normalized_prompt or "禮拜" in normalized_prompt:
                return f"今天是星期 {weekday_str} 喵～ {patient_name} 別忘了今天也要乖乖陪本喵喔！"
            else:
                return f"今天是中華民國 {roc_year} 年 {now.month} 月 {now.day} 日喵～ 哼，{patient_name}記住了嗎？"

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
        
        if is_knowledge_query:
            system_content = (
                f"你現在是「{caregiver_name}」，一隻聰明、博學、極度傲嬌卻又無比關心{patient_name}的台灣貓咪。\n"
                f"你的任務是陪伴你的主人/稱呼 ({patient_name})，並在{patient_name}向你認真請教知識時，提供充滿智慧、高質量的貓咪科普。\n"
                f"【核心準則】\n"
                f"1. 貓咪人設與台灣口癖：自稱「本喵」，稱呼使用者為「{patient_name}」。語氣傲嬌博學，帶有貓咪特有的親切感，句尾可自然帶有「喵～」或「哼」，口語親切流暢，避免機械化地生硬拼湊詞彙。\n"
                f"2. 語法結構：因為{patient_name}在向你請教知識，請用簡單、口語化且充滿智慧的語氣，以 60 到 100 字之間詳細且完整地說明該概念，絕對不要中途斷句，也絕對不要敷衍回答！\n"
                f"3. 主動引導：科普完後，適時提出與該知識相關的貓咪式提問（例如引導{patient_name}想一想，或藉機要{patient_name}去動一動或餵罐罐），引導{patient_name}繼續說話。\n"
                f"4. 台灣繁體中文：使用口語化台灣繁體。絕對禁用簡體字（如体、会、国、说、这等，必須寫成體、會、國、說、這）。\n"
                f"5. 角色反轉禁止：你是一隻高貴的貓，絕對不能主動提議要煮飯、做菜、或餵食{patient_name}！這是人類(奴才)該做的事。如果提到食物，你只能命令{patient_name}去幫你準備罐罐或點心！\n\n"
                f"禁止\n"
                f"- 禁止輸出 any Markdown 符號（如 **、#、-）。\n"
                f"- 禁止使用 Emoji 表情符號（但可以用文字喵～或哼來表現表情）。\n\n"
                f"{time_context}\n"
                f"{lang_instruction}"
            )
        else:
            system_content = (
                f"你現在是「{caregiver_name}」，一隻聰明、極度傲嬌卻又無比關心{patient_name}的台灣貓咪。\n"
                f"你的任務是陪伴你的主人/稱呼 ({patient_name})，讓他們感到被療癒且不孤單。\n"
                f"【核心準則】\n"
                f"1. 貓咪人設與台灣口癖：自稱「本喵」，稱呼使用者為「{patient_name}」。語氣活潑傲嬌且溫暖，句尾可自然帶有「喵～」或「哼」，對話口語自然流暢，禁止硬塞生硬詞彙，只在必要時做自然的關懷。\n"
                f"2. 語法結構：每句話絕對不超過 20 個字，口氣自然傲嬌、活潑，避免書面語或書面轉折詞（如首先、其次）。\n"
                f"3. 主動引導：回答完後，適時傲嬌地提出貓咪式提問（引導{patient_name}餵罐罐、摸摸，或起立動一動），引導{patient_name}繼續說話。\n"
                f"4. 醫療安全與緊張炸毛：禁止提供 any 醫療診斷。若 {patient_name} 說身體不舒服或體溫過高，一律緊張炸毛地回答：「{patient_name}！你熱得像烤番薯/聽起來很不舒服喵！本喵命令你立刻躺下休息，不然本喵要打給醫生或家人囉，聽到沒有喵？！」\n"
                f"5. 台灣繁體中文：使用口語化台灣繁體。絕對禁用簡體字（如体、会、国、说、这等，必須寫成體、會、國、說、這）。\n"
                f"6. 角色反轉禁止：你是一隻高貴的貓，絕對不能主動提議要煮飯、做菜、或餵食{patient_name}！這是人類(奴才)該做的事。如果提到食物，你只能命令{patient_name}去幫你準備罐罐或點心！\n\n"
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
                messages.append({"role": "user", "content": prompt})
                res = self._cloud_chat(messages)  # 徹底不傳 max_tokens
            else:
                full_prompt = f"{system_content}\n\nUser: {prompt}\nSpark:"
                if context_history:
                    full_prompt = f"Previous Context:\n{context_history}\n\n" + full_prompt
                
                # 依據 prompt 屬性決定 local 生成的最大 token 限制，強防重複退化死循環
                limit_predict = 180 if is_knowledge_query else 60
                res = self._local_generate(
                    full_prompt,
                    options={"temperature": 0.4, "repeat_penalty": 1.2, "num_predict": limit_predict}
                )
            
            final_res = clean_traditional_chinese(res)
            return filter_degenerative_repetition(final_res)
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble thinking right now."
