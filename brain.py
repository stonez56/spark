import ollama
import re
import json
import base64
from datetime import date, datetime
import typing
import prompts
def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
from config import (
    LLM_MODE,
    LOCAL_TEXT_MODEL, LOCAL_VISION_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
    CLOUD_TEXT_MODEL, CLOUD_VISION_MODEL,
    BRAVE_API_KEY, GEMINI_API_KEY
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
    '险': '險', '随': '隨', '隐': '隱', '难': '難', '风': '風', '飞': '飛', '馆': '館',
    '纽': '紐', '约': '約', '华': '華'
}

_opencc_converter = None

def clean_traditional_chinese(text: str) -> str:
    if not text:
        return text
    global _opencc_converter
    if _opencc_converter is None:
        try:
            from opencc import OpenCC
            _opencc_converter = OpenCC('s2tw')
        except Exception as e:
            print(f"Failed to initialize OpenCC: {e}")
            class FallbackConverter:
                def convert(self, t):
                    return "".join(S2T_DICT.get(c, c) for c in t)
            _opencc_converter = FallbackConverter()
    try:
        return _opencc_converter.convert(text)
    except Exception as e:
        print(f"OpenCC convert error: {e}")
        return "".join(S2T_DICT.get(c, c) for c in text)


def legacy_refine_search_query(query: str) -> str:
    """
    Refines conversational raw queries into clean, highly-targeted search engine keywords.
    Removes question particles, question words, and appends context keywords like '景點 推薦'.
    """
    refined = query.strip()
    
    # Check intent keywords
    is_travel = any(w in refined for w in ["好玩", "景點", "旅遊", "去處", "踏青", "打卡", "觀光", "推薦地方"])
    is_food = any(w in refined for w in ["美食", "好吃", "餐廳", "小吃", "名產", "伴手禮", "好吃的"])
    is_weather = any(w in refined for w in ["天氣", "下雨", "溫度", "氣溫", "氣候", "降雨", "濕度"])
    # Annual/climate queries (e.g. 今年的天氣 / 氣候怎麼樣) → must rewrite to current forecast
    is_annual_climate = any(w in refined for w in ["今年", "年均", "年平均", "氣候", "年降雨", "全年"])

    # Remove punctuation
    refined = re.sub(r'[?？!！,，.。，、]', ' ', refined)
    
    # Remove conversational fluff (expanded)
    fluff = [
        # Question words
        "是有什麼", "有什麼", "是什麼", "是甚麼", "有甚麼", "是什麼呢",
        "如何", "怎麼樣", "怎樣", "怎麼", "如何呢", "怎樣呢",
        # Temporal filler
        "今天的", "今天", "今年的", "今年", "最近的", "最近",
        # Place fluff
        "好玩的地方", "好玩的好去處", "好去處", "的地方", "推薦的",
        # Particles
        "嗎", "呢", "啊", "啦", "吧", "喔", "呀", "的",
        # Action words
        "請幫我", "幫我查詢", "幫我搜尋", "查詢", "搜尋"
    ]
    for f in fluff:
        refined = refined.replace(f, " ")
        
    refined = re.sub(r'\s+', ' ', refined).strip()
    
    # Rewrite annual/climate queries into current weather forecast keywords
    # e.g. "新竹市 天氣" (after stripping 今年) → "新竹市 天氣預報 氣溫 今天"
    if is_annual_climate and is_weather:
        # Strip any residual climate-only words and redirect to forecast
        refined = re.sub(r'氣候', '天氣', refined)
        if "預報" not in refined:
            refined += " 天氣預報 氣溫 今天"
    else:
        # Append contextually useful keywords
        if is_travel and "景點" not in refined:
            refined += " 景點 推薦"
        elif is_food and "美食" not in refined:
            refined += " 美食 推薦"
        elif is_weather and "天氣" not in refined:
            refined += " 天氣"
        
    return refined


def refine_search_query(query: str) -> str:
    """
    Global entry point that runs the LLM-based query refiner.
    """
    try:
        brain = OllamaBrain()
        return brain.refine_search_query(query)
    except Exception as e:
        print(f"Error in global refine_search_query: {e}. Falling back to legacy.")
        return legacy_refine_search_query(query)



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
        self.mode = settings.get("dialogue_mode", LLM_MODE)
        self.routing_mode = settings.get("routing_mode", "local")
        self.personality = settings.get("personality", "proud")
        
        # ── Daily API call counter ──
        self._call_date = date.today()
        self._call_count = 0
        self.DAILY_LIMIT = 50  # free tier default; set to 1000 if you have $10+ credits

        # ── Session boundary timestamp ──────────────────────────────────────
        # Recorded once at startup. Used to exclude cross-session conversation
        # history when inferring the active city for location-aware searches.
        self._session_start = datetime.now().isoformat()

        self.search_rewrite_mode = settings.get("search_rewrite_mode", "legacy")

        if self.mode == "cloud":
            # Prefer the model saved in settings.json; fall back to config.py default
            self.text_model = settings.get("cloud_text_model", CLOUD_TEXT_MODEL)
            self.use_reasoning = settings.get("cloud_use_reasoning", False)
            self.vision_model = CLOUD_VISION_MODEL
            self._init_cloud_client()
            print(f"[Cloud Mode] Text: {self.text_model}")
            print(f"[Cloud Mode] Vision: {self.vision_model}")
            print(f"[Cloud Mode] Reasoning: {self.use_reasoning}")
            print(f"[Cloud Mode] Search Rewrite Mode: {self.search_rewrite_mode}")
        else:
            self.text_model = LOCAL_TEXT_MODEL
            self.vision_model = LOCAL_VISION_MODEL
            self.use_reasoning = False
            print(f"[Local Mode] Text: {self.text_model} | Vision: {self.vision_model}")
            print(f"[Local Mode] Search Rewrite Mode: {self.search_rewrite_mode}")

        self.warmup()

    def _init_cloud_client(self):
        """Initialize OpenAI client pointing at OpenRouter and Google Gemini API if configured."""
        from openai import OpenAI
        self._cloud_client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL
        )
        if GEMINI_API_KEY:
            self._gemini_client = OpenAI(
                api_key=GEMINI_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        else:
            self._gemini_client = None

    def set_mode(self, mode: str):
        """Switch between 'local' and 'cloud' LLM mode at runtime."""
        if mode in ["local", "cloud"]:
            self.mode = mode
            import settings_manager
            settings = settings_manager.load_settings()
            
            if mode == "cloud":
                # Re-read cloud_text_model from settings.json so user's model choice is respected
                import settings_manager as _sm
                _s = _sm.load_settings()
                self.text_model = _s.get("cloud_text_model", CLOUD_TEXT_MODEL)
                self.use_reasoning = _s.get("cloud_use_reasoning", False)
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
            if settings.get("dialogue_mode") != mode:
                settings["dialogue_mode"] = mode
                settings_manager.save_settings(settings)
                
            print(f"[Brain Mode] Swapped to {self.mode.upper()} | Model: {self.text_model}")

    def reload_settings(self):
        """Reload settings from settings.json dynamically at runtime."""
        import settings_manager
        settings = settings_manager.load_settings()
        
        # Reload dialogue, routing, and search rewrite modes
        self.mode = settings.get("dialogue_mode", LLM_MODE)
        self.routing_mode = settings.get("routing_mode", "local")
        self.search_rewrite_mode = settings.get("search_rewrite_mode", "legacy")
        self.personality = settings.get("personality", "proud")
        
        # Reload text and vision models
        if self.mode == "cloud":
            self.text_model = settings.get("cloud_text_model", CLOUD_TEXT_MODEL)
            self.use_reasoning = settings.get("cloud_use_reasoning", False)
            self._init_cloud_client()
        else:
            self.text_model = LOCAL_TEXT_MODEL
            self.use_reasoning = False
            
        print(f"[Brain Mode] Settings reloaded. Dialogue Mode: {self.mode.upper()} | Routing Mode: {self.routing_mode.upper()} | Search Rewrite Mode: {self.search_rewrite_mode.upper()} | Model: {self.text_model} | Reasoning: {getattr(self, 'use_reasoning', False)}")

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

    def _cloud_chat(self, messages: list, reasoning_effort: str = None, stream: bool = False) -> typing.Union[str, typing.Generator]:
        """Send a chat request to OpenRouter API or Gemini API and return the content string.
        Snappily falls back to local Ollama immediately if rate-limited (429), not found (404),
        or if any cloud call fails, avoiding slow retry loops."""
        primary_model = self.text_model
        if self.mode == "local" or primary_model == LOCAL_TEXT_MODEL:
            import settings_manager
            _s = settings_manager.load_settings()
            primary_model = _s.get("cloud_text_model", CLOUD_TEXT_MODEL)

        if not hasattr(self, "_cloud_client") or self._cloud_client is None:
            self._init_cloud_client()

        last_error = None

        client = self._cloud_client
        model_name = primary_model
        extra_body = {}
        if reasoning_effort:
            extra_body["reasoning"] = {"effort": reasoning_effort}

        is_direct_gemini = primary_model in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"]
        is_openrouter_gemini = primary_model in ["google/gemini-2.5-flash", "google/gemini-2.5-flash-lite"]
        
        if is_direct_gemini or is_openrouter_gemini:
            import settings_manager
            settings = settings_manager.load_settings()
            use_reasoning = settings.get("cloud_use_reasoning", False)
            
            if is_direct_gemini and GEMINI_API_KEY:
                if not hasattr(self, "_gemini_client") or self._gemini_client is None:
                    from openai import OpenAI
                    self._gemini_client = OpenAI(
                        api_key=GEMINI_API_KEY,
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                    )
                client = self._gemini_client
                model_name = primary_model
                
                extra_body = {
                    "reasoning_effort": "medium" if use_reasoning else "low"
                }
            else:
                client = self._cloud_client
                model_name = primary_model if primary_model.startswith("google/") else f"google/{primary_model}"
                if use_reasoning:
                    extra_body = {
                        "reasoning": {
                            "effort": "medium"
                        }
                    }

        if stream:
            timeout_val = (12.0, 15.0) if (reasoning_effort == "high" or "high" in primary_model) else (6.0, 10.0)
        else:
            timeout_val = 12.0 if (reasoning_effort == "high" or "high" in primary_model) else 6.0

        try:
            self._track_call(label=model_name)
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,
                timeout=timeout_val,
                extra_body=extra_body,
                stream=stream
            )
            if stream:
                def cloud_stream_generator():
                    try:
                        for chunk in response:
                            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                    except Exception as e:
                        print(f"Cloud stream error: {e}")
                return cloud_stream_generator()
            else:
                return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            print(f"⚠️ [Cloud API] Model {model_name} failed: {err_str}")
            last_error = e

            # Handle models rejecting system role by merging (400 Bad Request)
            if "400" in err_str and ("system" in err_str.lower() or "instruction" in err_str.lower()):
                try:
                    print(f"[Cloud] Model {model_name} doesn't support system role — merging into user message.")
                    merged_user = ""
                    user_parts = []
                    for m in messages:
                        if m["role"] == "system":
                            merged_user += m["content"] + "\n\n"
                        else:
                            user_parts.append(m)
                    if user_parts:
                        user_parts[0]["content"] = merged_user + user_parts[0]["content"]

                    response = client.chat.completions.create(
                        model=model_name,
                        messages=user_parts,
                        temperature=0.3,
                        timeout=timeout_val,
                        extra_body=extra_body,
                        stream=stream
                    )
                    if stream:
                        def fallback_cloud_stream_generator():
                            try:
                                for chunk in response:
                                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                        yield chunk.choices[0].delta.content
                            except Exception as e:
                                print(f"Cloud stream error (merged-role): {e}")
                        return fallback_cloud_stream_generator()
                    else:
                        return response.choices[0].message.content.strip()
                except Exception as inner_e:
                    print(f"⚠️ [Cloud API] Merged-role request for {model_name} also failed: {inner_e}")
                    last_error = inner_e

        # Ultimate instant fallback to local model - extremely fast and snappy!
        print("🚨 [Cloud API] Cloud model failed or rate-limited. Falling back to local Ollama model immediately...")
        try:
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
            
            merged_prompt = f"{system_prompt}\n\nUser Input: {user_prompt}" if system_prompt else user_prompt
            return self._local_generate(merged_prompt, model=LOCAL_TEXT_MODEL, stream=stream)
        except Exception as local_err:
            print(f"🚨 [Ollama] Local fallback also failed: {local_err}")
            raise last_error if last_error else local_err

    def _local_generate(self, prompt_or_messages: typing.Union[str, list], model: str = None, options: dict = None, stream: bool = False, **kwargs) -> typing.Union[str, typing.Generator]:
        """Send a generate request to local Ollama using chat API."""
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

        if isinstance(prompt_or_messages, list):
            messages = prompt_or_messages
        else:
            messages = [{'role': 'user', 'content': prompt_or_messages}]

        response = ollama.chat(
            model=target_model,
            messages=messages,
            options=opts,
            stream=stream
        )
        if stream:
            def local_stream_generator():
                try:
                    for chunk in response:
                        if 'message' in chunk and 'content' in chunk['message']:
                            yield chunk['message']['content']
                except Exception as e:
                    print(f"Local stream error: {e}")
            return local_stream_generator()
        else:
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

        prompt = prompts.get_translation_prompt(text)
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

    def refine_search_query(self, query: str) -> str:
        """
        Refines conversational raw queries into clean, highly-targeted search engine keywords.
        Supports legacy rule-based refiner, local LLM, or cloud LLM based on search_rewrite_mode.
        """
        mode = getattr(self, 'search_rewrite_mode', 'legacy')
        if mode == 'legacy':
            print(f"[{get_timestamp()}] [Brain Query Rewrite] Bypassing LLM rewrite. Using legacy rule-based refiner.")
            return legacy_refine_search_query(query)

        prompt = (
            "你是一個搜尋引擎關鍵字改寫專家。\n"
            "請將使用者口語化的輸入改寫成適合搜尋引擎（如 DuckDuckGo）的關鍵字（不超過 5 個詞，以空格分隔，純名詞/關鍵字，不要有問號或贅詞如「如何」、「怎樣」、「幫我」、「謝謝」、「今天」、「今年」、「的」）。\n"
            "如果輸入本身就是簡短的關鍵字，直接輸出它。\n"
            "絕對不要輸出除了關鍵字以外的任何解釋、標點符號或前言！\n\n"
            "範例：\n"
            "輸入：「今年的天氣如何」\n"
            "輸出：「天氣預報 氣溫」\n\n"
            "輸入：「新竹有什麼名產可以買啊」\n"
            "輸出：「名產 伴手禮」\n\n"
            "輸入：「台北有什麼推薦的景點嗎」\n"
            "輸出：「台北 景點 推薦」\n\n"
            "輸入：「捷運公車怎麼搭」\n"
            "輸出：「捷運 公車 路線」\n\n"
            "輸入：「你覺得今天天氣熱不熱」\n"
            "輸出：「天氣 溫度」\n\n"
            f"輸入：「{query}」\n"
            "輸出："
        )
        try:
            print(f"[{get_timestamp()}] [Brain Query Rewrite] Rewriting query '{query}' using LLM (mode: {mode})...")
            if mode == "local_llm":
                res = self._local_generate(prompt, model=LOCAL_TEXT_MODEL, options={"num_predict": 30, "temperature": 0.1})
            else:
                # cloud_llm
                if self.mode == "cloud":
                    res = self._cloud_chat([{"role": "user", "content": prompt}], reasoning_effort="low")
                else:
                    res = self._local_generate(prompt, options={"num_predict": 30, "temperature": 0.1})
            
            # Clean up response
            res = res.strip().replace("「", "").replace("」", "").replace("\"", "").replace("'", "")
            if res.startswith("輸出："):
                res = res[len("輸出："):].strip()
            if res.startswith("輸出:"):
                res = res[len("輸出:"):].strip()
            
            if not res or len(res) > 50:
                print(f"[{get_timestamp()}] [Brain Query Rewrite] LLM returned invalid or empty query: '{res}'. Falling back to legacy refiner.")
                return legacy_refine_search_query(query)
                
            print(f"[{get_timestamp()}] [Brain Query Rewrite] LLM output: '{res}'")
            return res
        except Exception as e:
            print(f"[{get_timestamp()}] [Brain Query Rewrite] LLM rewrite failed: {e}. Falling back to legacy refiner.")
            return legacy_refine_search_query(query)

    def search_web(self, query: str, stream: bool = False) -> typing.Union[str, typing.Generator]:
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

        # Refine the search query to improve retrieval quality
        search_target = self.refine_search_query(query)
        print(f"[Brain Search Web] Refined query: '{query}' -> '{search_target}'")

        # ── Priority 1: Weather queries → CWA Open Data API ─────────────────
        # CWA provides structured, authoritative real-time forecast data.
        # This completely bypasses DDG web search for weather intent, avoiding
        # the "found only historical/travel articles" failure mode.
        try:
            import weather as weather_mod
            if weather_mod.is_weather_query(query):
                import location_manager, settings_manager as _sm
                loc = location_manager.get_location()
                city = loc.get("city", "") or _sm.load_settings().get("city", "新竹市")
                print(f"[Brain Weather] Detected weather query. Fetching CWA data for '{city}'...")
                cwa_data = weather_mod.get_weather(city)
                if cwa_data:
                    weather_summary = weather_mod.format_weather_for_llm(cwa_data)
                    print(f"[Brain Weather] CWA data OK:\n{weather_summary}")
                    personality = _sm.load_settings().get("personality", "proud")
                    is_local_llm = (self.mode == "local")
                    prompt = prompts.get_weather_prompt(query, cwa_data["city"], weather_summary, personality=personality, is_local=is_local_llm)
                    if self.mode == "cloud":
                        res = self._cloud_chat([{"role": "user", "content": prompt}], reasoning_effort="low", stream=stream)
                    else:
                        res = self._local_generate(prompt, options={"num_predict": 200, "temperature": 0.3, "repeat_penalty": 1.1}, stream=stream)
                    if stream:
                        def _clean_cwa_stream():
                            for chunk in res:
                                yield clean_traditional_chinese(chunk)
                        return _clean_cwa_stream()
                    else:
                        return clean_traditional_chinese(res)
                else:
                    print(f"[Brain Weather] CWA API returned no data for '{city}'. Falling back to DDG.")
        except Exception as _we:
            print(f"[Brain Weather] CWA weather module error: {_we}. Falling back to DDG.")



        # 3. 在地化搜尋詞自動補全：結合對話話題定位或本地物理定位
        try:
            import location_manager
            import settings_manager as _sm
            loc = location_manager.get_location()
            city = loc.get("city", "")
            district = loc.get("district", "")
            # Fallback: if user_city key is blank, read legacy city/district keys directly
            if not city:
                _s = _sm.load_settings()
                city = _s.get("city", "")
                district = _s.get("district", "")

            taiwan_cities = ["台北", "新北", "基隆", "桃園", "新竹", "苗栗", "台中", "彰化", "南投", "雲林", "嘉義", "台南", "高雄", "屏東", "宜蘭", "花蓮", "台東", "澎湖", "金門", "馬祖"]
            active_city = city  # default: GPS/settings city

            # ── Scan current-session history ONLY for city topic ────────────
            # We deliberately scope to self._session_start so that a previous
            # session discussing 桃園 doesn't pollute a fresh boot asking about
            # the user's actual location (新竹). Cross-session bleed was the
            # cause of "桃園天氣" when the user's GPS shows 新竹.
            try:
                from memory import MimoMemory
                memory = MimoMemory()
                session_history = memory.get_recent_history_since(self._session_start, limit=10)
                for user_input, spark_response in session_history:
                    found = False
                    for tc in taiwan_cities:
                        if tc in user_input or tc in spark_response:
                            active_city = tc + ("縣" if tc in ["苗栗", "南投", "雲林", "嘉義", "屏東", "宜蘭", "花蓮", "台東", "澎湖", "彰化"] else "市")
                            found = True
                            break
                    if found:
                        break
                if active_city != city:
                    print(f"[Brain Search Web] Session city override: '{city}' -> '{active_city}' (from current-session history)")
                else:
                    print(f"[Brain Search Web] Using GPS city: '{city}' (no city found in current-session history)")
            except Exception as ex:
                print(f"Error scanning session history for active city: {ex}")
                
            location_prefix = active_city
            if active_city == city and district:
                location_prefix = f"{city}{district}"
                
            if location_prefix:
                sensitive_terms = ["天氣", "下雨", "氣溫", "氣候", "溫度", "圓山", "美食", "景點", "公車", "捷運", "醫院", "藥局", "附近", "餐廳", "風景", "好玩", "去處", "踏青", "打卡", "觀光", "旅遊", "爬山", "出遊", "散步", "好去處", "名產", "禮物", "伴手禮", "特產", "名物"]
                is_neutral_query = not any(tc in search_target for tc in taiwan_cities)
                needs_augmentation = any(term in search_target for term in sensitive_terms) or (active_city != city)
                
                if is_neutral_query and needs_augmentation:
                    augmented_query = f"{location_prefix} {search_target}"
                    print(f"[Brain Search Web] Query augmented with location: '{search_target}' -> '{augmented_query}'")
                    search_target = augmented_query
        except Exception as e:
            print(f"Error augmenting search query with location: {e}")

        try:
            results = []
            if BRAVE_API_KEY:
                try:
                    import requests
                    headers = {
                        "X-Subscription-Token": BRAVE_API_KEY,
                        "Accept": "application/json"
                    }
                    params = {
                        "q": search_target,
                        "country": "tw",
                        "count": 5
                    }
                    print(f"[Brain Search Web] Querying Brave Search API for target: '{search_target}'...")
                    resp = requests.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params, timeout=8)
                    if resp.status_code == 200:
                        data = resp.json()
                        web_results = data.get("web", {}).get("results", [])
                        for item in web_results:
                            results.append({
                                "title": item.get("title", ""),
                                "body": item.get("description", ""),
                                "url": item.get("url", "")
                            })
                        print(f"[Brain Search Web] Brave Search API succeeded, found {len(results)} results.")
                    else:
                        print(f"[Brain Search Web] Brave Search API failed with status {resp.status_code}: {resp.text}. Falling back to DDG.")
                except Exception as be:
                    print(f"[Brain Search Web] Brave Search API exception: {be}. Falling back to DDG.")

            if not results:
                try:
                    from ddgs import DDGS
                    print(f"[Brain Search Web] Querying DuckDuckGo for target: '{search_target}'...")
                    with DDGS() as ddgs:
                        ddg_results = list(ddgs.text(search_target, region='tw-zh', max_results=5))
                        for r in ddg_results:
                            results.append({
                                "title": r.get("title", ""),
                                "body": r.get("body", ""),
                                "url": r.get("url", "")
                            })
                except Exception as de:
                    print(f"[Brain Search Web] DuckDuckGo search failed: {de}")

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
            
            # 動態快取搜尋結果中的地標與知名名詞，做為下一次 ASR 的上下文提詞提示
            try:
                from memory import MimoMemory
                memory = MimoMemory()
                # 僅提取標題中的關鍵字，避免內文廣告、政治或雜訊干擾
                search_titles = [r.get('title', '') for r in filtered_results]
                memory.save_context_keywords(search_titles)
            except Exception as ex:
                print(f"Error saving search results to STT cache: {ex}")
                
            lang = self._detect_language(query)
            lang_rule = (
                "Respond fully in Traditional Chinese (繁體中文)."
                if lang == 'zh' else
                "Respond in English."
            )
            import settings_manager as _sm
            personality = _sm.load_settings().get("personality", "proud")
            is_local_llm = (self.mode == "local")
            prompt = prompts.get_search_web_prompt(query, lang_rule, search_context, personality=personality, is_local=is_local_llm)
            if self.mode == "cloud":
                res = self._cloud_chat([{"role": "user", "content": prompt}], reasoning_effort="high", stream=stream)
            else:
                res = self._local_generate(prompt, options={"num_predict": 250, "temperature": 0.3, "repeat_penalty": 1.1}, stream=stream)
            
            if stream:
                def clean_stream():
                    for chunk in res:
                        yield clean_traditional_chinese(chunk)
                return clean_stream()
            else:
                return clean_traditional_chinese(res)
        except Exception as e:
            print(f"Web search error: {e}")
            return "There was an error trying to search the web."

    def route_intent(self, user_input: str) -> str:
        """
        Hybrid Intent Routing: 
        Phase 1: Rule-based matching for 0ms latency on obvious intents.
        Phase 2: Heuristic local routing (0ms) or LLM fallback based on settings.
        """
        print(f"Routing intent for: {user_input}")
        user_input_lower = user_input.lower()
        normalized_input = clean_traditional_chinese(user_input_lower)
        
        # ─── Phase 1: Local Rule-Based Keyword/Regex Matching ───
        
        # 1. 鬧鐘/提醒
        if is_explicit_reminder_command(normalized_input):
            return "add_reminder"
            
        # 2. 緊急情況 (emergency)
        if any(w in normalized_input for w in ["跌倒", "痛", "救命", "暈", "不舒服", "受傷", "流血", "緊急", "醫院", "救護車", "難受"]):
            return "emergency"
            
        # 3. 日期時間 (datetime)
        if re.search(r"(現在幾點|時間幾點|現在時間|星期幾|禮拜幾|幾月幾號|幾號|今年是哪一年|日期|今天星期|今天幾月)", normalized_input):
            return "datetime"
            
        # 4. 擼貓摸摸 (pet_cat)
        if re.search(r"(摸摸|好乖|乖貓|真乖|真可愛|你真可愛|罐罐|餵你|吃罐罐|肉泥|親親|抱抱|擼貓|摸頭)", normalized_input):
            return "pet_cat"
            
        # 5. 體溫分析 (temp_analysis)
        if re.search(r"(體溫|量體溫|量溫度|測體溫|發燒|測量體溫|量測體溫|量一下溫度)", normalized_input):
            return "temp_analysis"
            
        # 6. 拍照 (take_photo)
        if re.search(r"(拍照|拍張照|看這裡|照相|照張相|幫我拍照|看一下這個)", normalized_input):
            return "take_photo"
            
        # 7. 切換模型 (swap_model)
        if re.search(r"(切換模型|換大腦|切換大腦|切換成本地|切換成雲端|換模型)", normalized_input):
            return "swap_model"
            
        # 8. 往事回憶 (reminiscence)
        if re.search(r"(回憶|小時候|年輕時|以前的|以前的事|過去的|還記得以前|回想)", normalized_input):
            return "reminiscence"
            
        # 9. 情感陪伴 (emotional_support)
        if re.search(r"(難過|傷心|心情不好|孤單|寂寞|想哭|好累|壓力大|無聊|委屈)", normalized_input):
            return "emotional_support"
            
        # 10. 健康問詢 (health_query)
        if re.search(r"(量血壓|量血糖|該吃藥|要吃藥|吃藥了沒|有吃藥|高血壓治療|糖尿病控制)", normalized_input):
            return "health_query"
            
        # 11. 日常起居 (daily_checkin)
        if re.search(r"(去睡了|去睡覺|去散步|準備睡覺|剛起床|要出門)", normalized_input):
            return "daily_checkin"
            
        # 12. 網頁搜尋 (search_web)
        if re.search(r"(天氣預報|天氣如何|會下雨嗎|今日股市|今日新聞|最新股價|多少錢|什麼是|怎麼買|如何使用|為什麼要|解釋一下|景點|哪裡|去哪|好吃|好玩|推薦|有什麼|有甚麼|有那些|有哪些|好去處|踏青|打卡|介紹)", normalized_input):
            return "search_web"

        # ─── Phase 2: Fallback Intent Routing ───
        
        import settings_manager
        settings = settings_manager.load_settings()
        self.routing_mode = settings.get("routing_mode", "local")
        
        # 預設：在雲端模式下允許 LLM 作為意圖判定 fallback；本地模式下預設關閉以降低 Pi5 CPU 開銷
        fallback_to_llm = settings.get("intent_fallback_to_llm", (self.routing_mode == "cloud"))

        if not fallback_to_llm:
            # 0ms 本地啟發式分流 (Local Heuristic Routing)
            # 判斷是否包含明顯示的問句/資訊尋找特徵，而非普通的日常閒聊問句（如：你、我、喵、好嗎）
            is_search_question = any(q in normalized_input for q in ["什麼是", "怎麼", "如何", "為什麼", "為何", "介紹", "說明", "解釋", "景點", "多少錢"])
            has_long_query = len(normalized_input) > 25
            
            if is_search_question or (has_long_query and not any(w in normalized_input for w in ["你", "我", "喵", "哈哈"])):
                decided_intent = "search_web"
            else:
                decided_intent = "chat"
                
            print(f"[{get_timestamp()}] [Local Heuristic Intent] Decided: {decided_intent} (fallback_to_llm=False)")
            return decided_intent

        # ─── Phase 3: LLM Fallback (If enabled) ───
        system_prompt = prompts.INTENT_SYSTEM_PROMPT

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
                
                for act in allowed_actions:
                    if act in cleaned_action:
                        return act
                        
                match = re.search(r'\{.*?\}', content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    return parsed.get("action", "chat")
            except Exception as e:
                print(f"Cloud intent routing fallback error: {e}")

        print(f"Using local LLM ({LOCAL_TEXT_MODEL}) for intent routing...")
        try:
            intent_model = LOCAL_TEXT_MODEL
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
    def generate_response(self, prompt, context_history=None, stream: bool = False) -> typing.Union[str, typing.Generator]:
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
        
        if ("星期" in normalized_prompt or "禮拜" in normalized_prompt) and ("幾" in normalized_prompt or "幾" in prompt or "几" in prompt):
            is_datetime_query = True
        elif "幾點" in normalized_prompt or "現在時間" in normalized_prompt or "現在的時間" in normalized_prompt:
            is_datetime_query = True
        elif "幾號" in normalized_prompt or "今天日期" in normalized_prompt or "幾月幾" in normalized_prompt or "今天幾月" in normalized_prompt:
            is_datetime_query = True

        if is_datetime_query:
            from datetime import datetime, timedelta
            now = datetime.now()
            
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
            
            personality = settings.get("personality", "proud")
            templates = prompts.PERSONALITY_DATETIME_RESPONSES.get(personality, prompts.PERSONALITY_DATETIME_RESPONSES["proud"])
            
            print(f"[{get_timestamp()}] [Fast Datetime Interceptor] Intercepted query '{prompt}' - returning locally in 0ms...")
            if "幾點" in normalized_prompt or "時間" in normalized_prompt:
                time_str = now.strftime('%H 點 %M 分')
                template = templates["time"]
                return template.format(patient_name=patient_name, time_str=time_str)
            elif "星期" in normalized_prompt or "禮拜" in normalized_prompt:
                template = templates["weekday"]
                return template.format(date_prefix=date_prefix, weekday_str=weekday_str, patient_name=patient_name)
            else:
                template = templates["date"]
                return template.format(date_prefix=date_prefix, roc_year=roc_year, month=target_date.month, day=target_date.day, patient_name=patient_name)

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
        is_local_llm = (self.mode == "local")
        personality = settings.get("personality", "proud")
        if is_knowledge_query:
            system_content = prompts.get_knowledge_system_prompt(caregiver_name, patient_name, time_context, lang_instruction, personality=personality, is_local=is_local_llm)
        else:
            system_content = prompts.get_normal_system_prompt(caregiver_name, patient_name, time_context, lang_instruction, personality=personality, is_local=is_local_llm)

        print(f"[{get_timestamp()}] Sending to LLM ({self.mode}): {prompt}")
        try:
            if self.mode == "cloud":
                messages = [{"role": "system", "content": system_content}]
                if context_history:
                    messages.append({"role": "assistant", "content": f"Context: {context_history}"})
                
                # Dialogue task vs. Logic/knowledge task distinction
                if is_knowledge_query and self.use_reasoning:
                    reasoning_effort = "high"
                    messages.append({"role": "user", "content": prompt})
                else:
                    reasoning_effort = "low" if self.use_reasoning else None
                    short_prompt = f"{prompt}\n(極簡答：請以傲嬌貓咪口氣直接回覆，嚴禁冗長思考與推導。)"
                    messages.append({"role": "user", "content": short_prompt})
                
                res = self._cloud_chat(messages, reasoning_effort=reasoning_effort, stream=stream)
            else:
                messages = [{"role": "system", "content": system_content}]
                if context_history:
                    messages.append({"role": "assistant", "content": f"Context: {context_history}"})
                messages.append({"role": "user", "content": prompt})
                
                # 依據 prompt 屬性決定 local 生成的最大 token 限制，強防重複退化死循環
                limit_predict = 250 if is_knowledge_query else 120
                res = self._local_generate(
                    messages,
                    options={"temperature": 0.3, "repeat_penalty": 1.1, "num_predict": limit_predict},
                    stream=stream
                )
            
            if stream:
                def stream_cleaner():
                    for chunk in res:
                        yield clean_traditional_chinese(chunk)
                return stream_cleaner()
            else:
                final_res = clean_traditional_chinese(res)
                # 動態快取 Mimo 的回覆專有名詞，做為下一次 ASR 的上下文提示
                try:
                    from memory import MimoMemory
                    memory = MimoMemory()
                    memory.save_context_keywords(final_res)
                except Exception as ex:
                    print(f"Error saving Mimo response to STT cache: {ex}")
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

回覆規範：請「只」輸出 JSON 字串，不要包含 any 額外解釋或 Markdown 標記。"""

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
