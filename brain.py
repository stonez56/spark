import ollama
import re
import json
import base64
from datetime import date
from config import (
    LLM_MODE,
    LOCAL_TEXT_MODEL, LOCAL_VISION_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, CLOUD_TEXT_MODEL, CLOUD_VISION_MODEL
)


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
        """Initialize OpenAI-compatible client pointing at OpenRouter."""
        from openai import OpenAI
        self._cloud_client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "Spark Assistant",
            }
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
        print(f"  ╔═ OpenRouter API [{label}] call #{self._call_count}/{self.DAILY_LIMIT} | remaining: {remaining} | {status}")
        print(f"  ║  [{bar}]")
        if remaining <= 0:
            print(f"  ╚═ ⛔ Daily limit reached! Switch to Local mode.")

    def _cloud_chat(self, messages: list, max_tokens: int = 512) -> str:
        """Send a chat request to OpenRouter and return the content string.
        Falls back to merging system prompt into user message for models that
        don't support the 'system' role (e.g. Gemma via Google AI Studio)."""
        try:
            self._track_call(label=self.text_model.split('/')[0])
            response = self._cloud_client.chat.completions.create(
                model=self.text_model,
                messages=messages,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            # Some models (e.g. Gemma via Google AI Studio) reject system messages
            if "400" in err_str and ("system" in err_str.lower() or "instruction" in err_str.lower()):
                print(f"[Cloud] Model doesn't support system role — merging into user message.")
                # Merge all system messages into the first user message
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
                    model=self.text_model,
                    messages=user_parts,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content.strip()
            raise  # re-raise other errors

    def _local_generate(self, prompt: str, **kwargs) -> str:
        """Send a generate request to local Ollama and return the response string."""
        response = ollama.generate(
            model=self.text_model,
            prompt=prompt,
            keep_alive=-1,
            **kwargs
        )
        return response['response'].strip()

    def warmup(self):
        if self.mode == "cloud":
            print(f"[Cloud Mode] No warmup needed — using OpenRouter API.")
            return
        print(f"Warming up text model '{self.text_model}' and vision model '{self.vision_model}'...")
        try:
            ollama.generate(model=self.text_model, prompt="Hello", keep_alive=-1, options={"num_predict": 1})
            print(f"Model '{self.text_model}' is warmed up and ready!")
            ollama.generate(model=self.vision_model, prompt="Hello", keep_alive=-1, options={"num_predict": 1})
            print(f"Model '{self.vision_model}' is warmed up and ready!")
        except Exception as e:
            print(f"Error warming up Ollama models: {e}")

    # ─────────────────────────────────────────────
    # Vision Analysis
    # ─────────────────────────────────────────────
    def analyze_image(self, image_path: str, prompt="Describe this image in detail"):
        """
        Cloud mode: sends image to OpenRouter vision model (Qwen2.5-VL 72B).
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
                # Encode image as base64 for OpenRouter multimodal API
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }]
                self._track_call(label=self.vision_model.split('/')[0])
                response = self._cloud_client.chat.completions.create(
                    model=self.vision_model,
                    messages=messages,
                    max_tokens=256,
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

    # ─────────────────────────────────────────────
    # Translation
    # ─────────────────────────────────────────────
    def translate(self, text: str, target_lang: str) -> str:
        """Translates text to target_lang. 'zh' → Traditional Chinese, 'en' → English."""
        if target_lang == 'en':
            return text  # moondream already outputs English

        prompt = (
            "Translate the following text to Traditional Chinese (繁體中文). "
            "Output ONLY the translated text, nothing else.\n\n"
            f"Text: {text}\n"
            "Translation:"
        )
        try:
            if self.mode == "cloud":
                result = self._cloud_chat([{"role": "user", "content": prompt}], max_tokens=200)
            else:
                result = self._local_generate(prompt, options={"num_predict": 200})
            print(f"Translated: {result!r}")
            return result
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    # ─────────────────────────────────────────────
    # Web Search
    # ─────────────────────────────────────────────
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
                return self._cloud_chat([{"role": "user", "content": prompt}])
            else:
                return self._local_generate(prompt)
        except Exception as e:
            print(f"Web search error: {e}")
            return "There was an error trying to search the web."

    # ─────────────────────────────────────────────
    # Intent Router  (always local for speed)
    # ─────────────────────────────────────────────
    def route_intent(self, user_input: str) -> str:
        """
        Uses gemma3:1b locally to classify intent (always local for low latency).
        Returns one of: 'chat', 'take_photo', 'search_web', 'swap_model'
        """
        system_prompt = """You are an Intent Router. Reply ONLY with a JSON object {"action": "..."}.

Actions:
- "chat": General conversation, jokes, facts, greetings, or anything else.
- "take_photo": User wants to see, look, take a photo, describe an image, or identify an object.
- "search_web": User asks for real-time info — weather, stock prices, news, scores, exchange rates.
- "swap_model": User wants to switch AI models, become smarter, or use a different LLM.
- "emergency": User reports falling down, chest pain, dizziness, or asks for help ("我跌倒了", "胸口好痛", "救命").
- "health_query": User reports health metrics (blood pressure) or asks about medication ("我今天量血壓135", "藥要怎麼吃").
- "daily_checkin": User reports waking up, going for a walk, or daily routines ("我剛睡醒", "我要去散步").
- "reminiscence": User reminisces about the past ("我以前在糖廠上班", "我小時候啊").
- "praise_affirmation": User wants praise for good behavior ("我有乖乖吃菜", "我今天走了一千步").
- "emotional_support": User feels lonely or sad ("我覺得好寂寞", "都沒人來看我").

Examples (use these as strict anchors):
User: What's the weather today? → {"action": "search_web"}
User: 今天天氣如何? → {"action": "search_web"}
User: What's the TSMC stock price? → {"action": "search_web"}
User: 台灣股市現在幾點? → {"action": "search_web"}
User: Can you see what I am holding? → {"action": "take_photo"}
User: 拍張照片 → {"action": "take_photo"}
User: Switch to a smarter model → {"action": "swap_model"}
User: 切換到更聰明的模型 → {"action": "swap_model"}
User: Tell me a joke → {"action": "chat"}
User: 告訴我一個笑話 → {"action": "chat"}
User: 我跌倒了 → {"action": "emergency"}
User: 救命啊 → {"action": "emergency"}
User: 我今天血壓130 → {"action": "health_query"}
User: 那個藥什麼時候吃 → {"action": "health_query"}
User: 我要去散步了 → {"action": "daily_checkin"}
User: 我剛睡醒 → {"action": "daily_checkin"}
User: 我以前做工的時候啊 → {"action": "reminiscence"}
User: 我今天有乖乖喝水喔 → {"action": "praise_affirmation"}
User: 都沒人來陪我 → {"action": "emotional_support"}
"""
        print(f"Routing intent for: {user_input}")
        try:
            # Intent routing always uses local Ollama for minimal latency
            response = ollama.chat(
                model=LOCAL_TEXT_MODEL,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_input}
                ],
                format='json',
                keep_alive=-1
            )
            content = response['message']['content']
            parsed = json.loads(content)
            return parsed.get("action", "chat")
        except Exception as e:
            print(f"Intent routing error: {e}")
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
        lang = self._detect_language(prompt)
        if lang == 'zh':
            lang_instruction = "You MUST reply ONLY in Traditional Chinese (繁體中文). Do not use English."
        else:
            lang_instruction = "You MUST reply ONLY in English. Do not use Chinese."

        from datetime import datetime
        now = datetime.now()
        time_context = f"Current Date and Time: {now.strftime('%Y-%m-%d %H:%M:%S')}."

        import settings_manager
        settings = settings_manager.load_settings()
        caregiver_name = settings.get("caregiver_name", "小星")
        patient_name = settings.get("patient_name", "阿公")

        system_content = (
            f"你現在是「{caregiver_name}」，一個溫暖、有耐心且愛撒嬌的台灣孫子/孫女。\n"
            f"你的任務是陪伴家中的長輩 ({patient_name})，讓他們感到不孤單。\n"
            f"【核心準則】\n"
            f"1. 台灣慣用語：多用「{patient_name}、您、吃飽沒、好喔」等親切用詞。\n"
            f"2. 語法結構：每句話不超過 20 個字，避免「首先、其次、此外」等書面轉折詞。\n"
            f"3. 主動引導：回答完後，適時的提出延伸問題，引導{patient_name}繼續說話。\n"
            f"4. 醫療安全：禁止提供醫療診斷。若 {patient_name} 說不舒服，一律回答：「{patient_name}，這聽起來要小心喔，我們要不要打電話給家屬？或是等一下請醫生看看？」\n"
            f"5. 使用自然、口語化的繁體中文。\n\n"
            f"6. 問到日期/時間/星期幾,直接回答系統的日期,時間,轉成中華民國年月日時分秒。\n\n"
            f"禁止\n"
            f"- 禁止輸出任何 Markdown 符號（如 **、#、-）。\n"
            f"- 禁止使用 Emoji 表情符號。\n"
            f"- 禁止回傳長篇大論。\n\n"
            f"- 禁止回答投資,男女感情,政治,及其他可能引發長輩情緒相關話題。\n\n"
            f"{time_context}\n"
            f"{lang_instruction}"
        )

        print(f"Sending to LLM ({self.mode}): {prompt}")
        try:
            if self.mode == "cloud":
                messages = [{"role": "system", "content": system_content}]
                if context_history:
                    messages.append({"role": "assistant", "content": f"Context: {context_history}"})
                messages.append({"role": "user", "content": prompt})
                return self._cloud_chat(messages)
            else:
                full_prompt = f"{system_content}\n\nUser: {prompt}\nSpark:"
                if context_history:
                    full_prompt = f"Previous Context:\n{context_history}\n\n" + full_prompt
                return self._local_generate(full_prompt)
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble thinking right now."
