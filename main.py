import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import warnings
import builtins
import time
from datetime import datetime

# 全域 print 猴子補丁，為每一行日誌加上 [YYYY-MM-DD HH:MM:SS] 格式的時間戳記
_original_print = builtins.print

def _timed_print(*args, **kwargs):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _original_print(f"[{timestamp}]", *args, **kwargs)

builtins.print = _timed_print


import threading
import numpy as np
from multiprocessing import Process, Queue, Event

# Suppress onnxruntime CUDAExecutionProvider warnings for Raspberry Pi
warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")

from state_machine import StateMachine, SparkState
from ui import run_ui
from memory import MimoMemory
from brain import OllamaBrain
from stt import SparkSTT
from tts import SparkTTS
from config import LLM_MODE, LOCAL_TEXT_MODEL, CLOUD_TEXT_MODEL, WAKE_WORD
from oled_controller import OLEDController
from camera_controller import CameraController

def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def format_reminder_confirmation(message: str, trigger_time: str, start_date: str = None) -> str:
    """
    Format a beautiful, natural, and accurate Traditional Chinese confirmation message.
    Avoids embarrassing hardcoded '今天下午 07:00' when the user said morning or a different day.
    """
    # 1. Parse time period (早上/上午/中午/下午/晚上/半夜)
    try:
        hour = int(trigger_time.split(":")[0])
        minute = int(trigger_time.split(":")[1])
    except Exception:
        hour = 12
        minute = 0
        
    if 0 <= hour < 5:
        period = "半夜"
    elif 5 <= hour < 11:
        period = "早上"
    elif 11 <= hour < 13:
        period = "中午"
    elif 13 <= hour < 18:
        period = "下午"
    else:
        period = "晚上"
        
    # Format hour to 12-hour clock for natural speech
    display_hour = hour if hour <= 12 else hour - 12
    if hour == 0:
        display_hour = 12
        
    if minute == 0:
        time_display = f"{period}{display_hour}點"
    else:
        time_display = f"{period}{display_hour}點{minute}分"

    # 2. Parse date period (今天/明天/後天/特定日期)
    date_display = "今天"
    if start_date:
        import datetime as dt
        try:
            today = dt.date.today()
            target_date = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
            delta = (target_date - today).days
            if delta == 0:
                date_display = "今天"
            elif delta == 1:
                date_display = "明天"
            elif delta == 2:
                date_display = "後天"
            else:
                date_display = f"{target_date.month}月{target_date.day}號"
        except Exception as e:
            print(f"Error parsing date delta: {e}")
            date_display = "今天"

    return f"記下來了！會在{date_display}{time_display}提醒你「{message}」喵！"

def format_reminder_trigger_sentence(message: str) -> str:
    """
    Generate a beautiful, tsundere cat character reminder sentence for the scheduler trigger.
    """
    import random
    templates = [
        f"喂！時間到啦！本喵特地來提醒你「{message}」喵！可別忘了！",
        f"喵嗚～說好了現在要提醒你「{message}」的，本喵說到做到，快去吧！",
        f"哼，本喵才不是特地關心你呢，只是時間到了，提醒你該去「{message}」了喵！",
        f"時間到了喔！本喵大發慈悲提醒你該去「{message}」了喵～"
    ]
    return random.choice(templates)

def get_js_weekday(date_str: str) -> str:
    """
    Get the JavaScript-aligned weekday ('0' for Sunday, '1' for Monday, etc.)
    from a YYYY-MM-DD date string.
    """
    import datetime
    try:
        dt_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return str((dt_obj.weekday() + 1) % 7)
    except Exception:
        return "0,1,2,3,4,5,6"

def play_voice_stream(tts, response, tts_queue, stop_audio_flag):
    """
    Stream-synthesizes response text, pushing audio chunks into tts_queue.
    Correctly waits for the REMAINING PLAYBACK TIME after synthesis completes,
    which handles Piper running slower-than-real-time on low-end CPUs.
    """
    stop_audio_flag.clear()
    
    # Send a control packet (1 byte) to signal frontend to stopAllAudio() synchronously
    tts_queue.put(b'\x02')
    
    # 150ms defensive delay: allows the Speaking state WebSocket message to
    # arrive and be processed by the frontend BEFORE audio chunks start streaming,
    # preventing the filler audio from being killed.
    time.sleep(0.15)
    
    total_bytes = 0
    first_chunk_sent_at = None

    chunk_idx = 0
    for chunk in tts.synthesize_stream(response):
        if stop_audio_flag.is_set():
            break
        print(f"[Orchestrator] Pushing chunk #{chunk_idx} ({len(chunk)} bytes) to tts_queue...")
        tts_queue.put(chunk)
        total_bytes += len(chunk)
        if first_chunk_sent_at is None:
            first_chunk_sent_at = time.time()  # Record when frontend starts receiving audio
        chunk_idx += 1
    
    if stop_audio_flag.is_set() or first_chunk_sent_at is None:
        return

    # Calculate how long the audio will play on the frontend.
    # We anchor from first_chunk_sent_at (not from synthesis start) to correctly
    # handle the case where Piper synthesizes slower OR faster than real-time.
    audio_duration = total_bytes / (22050 * 2)
    # Frontend starts playing ~50ms after receiving first chunk.
    # Remaining playback time = total duration - time already elapsed since first chunk.
    elapsed_since_first = time.time() - first_chunk_sent_at
    remaining_playback = audio_duration - elapsed_since_first + 0.5  # 0.5s safety buffer

    print(f"[{get_timestamp()}] ⏳ Audio duration: {audio_duration:.1f}s | Elapsed since first chunk: {elapsed_since_first:.1f}s | Waiting: {max(remaining_playback, 0):.1f}s")

    if remaining_playback > 0:
        # Wait for the remaining audio to finish playing on the frontend
        deadline = time.time() + remaining_playback
        while time.time() < deadline:
            if stop_audio_flag.is_set():
                break
            time.sleep(0.05)

import queue as py_queue
def stream_llm_and_play(llm_generator, tts, tts_queue, stop_audio_flag, transcript_queue, transcription):
    stop_audio_flag.clear()
    tts_queue.put(b'\x02')  # stop audio on frontend
    time.sleep(0.15)
    
    sentence_queue = py_queue.Queue()
    full_text_container = [""]
    
    def llm_worker():
        sentence_buffer = ""
        try:
            for chunk in llm_generator:
                if stop_audio_flag.is_set():
                    break
                if chunk:
                    full_text_container[0] += chunk
                    sentence_buffer += chunk
                    transcript_queue.put((transcription, full_text_container[0] + " ..."))
                    
                    import re
                    match = re.search(r'([。！？…；.!?\n]+)', sentence_buffer)
                    if match:
                        end_idx = match.end()
                        sentence = sentence_buffer[:end_idx].strip()
                        sentence_buffer = sentence_buffer[end_idx:]
                        if sentence:
                            sentence_queue.put(sentence)
        except Exception as e:
            print(f"LLM Stream Worker Error: {e}")
            
        if sentence_buffer.strip():
            sentence_queue.put(sentence_buffer.strip())
        sentence_queue.put(None)
        transcript_queue.put((transcription, full_text_container[0]))

    worker_thread = threading.Thread(target=llm_worker)
    worker_thread.start()
    
    first_chunk_sent_at = None
    total_bytes = 0
    
    while True:
        try:
            sentence = sentence_queue.get(timeout=0.1)
            if sentence is None:
                break
            
            print(f"[{get_timestamp()}] [Streaming TTS] Synthesizing: '{sentence}'")
            for audio_chunk in tts.synthesize_stream(sentence):
                if stop_audio_flag.is_set():
                    break
                tts_queue.put(audio_chunk)
                total_bytes += len(audio_chunk)
                if first_chunk_sent_at is None:
                    first_chunk_sent_at = time.time()
                    
            if stop_audio_flag.is_set():
                break
        except py_queue.Empty:
            if stop_audio_flag.is_set():
                break
            continue

    worker_thread.join()
    
    if not stop_audio_flag.is_set() and first_chunk_sent_at is not None:
        audio_duration = total_bytes / (22050 * 2)
        elapsed_since_first = time.time() - first_chunk_sent_at
        remaining_playback = audio_duration - elapsed_since_first + 0.5
        if remaining_playback > 0:
            deadline = time.time() + remaining_playback
            while time.time() < deadline:
                if stop_audio_flag.is_set():
                    break
                time.sleep(0.05)
                
    return full_text_container[0]

def audio_orchestrator(sm, state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue):
    # Initialize and start OLED first so it shows loading status on SSD1306
    oled_ctrl = OLEDController(sm)
    oled_ctrl.start()
    
    print("Loading AI Models...")
    
    try:
        # Location Auto-Detection on first boot/warmup
        try:
            import location_manager
            loc = location_manager.get_location()
            if not loc.get("city"):
                print("[Location Setup] No cached location found in settings.json. Running IP geolocation...")
                sm.loading_text = "Detecting Location..."
                detected = location_manager.auto_detect_ip()
                if detected:
                    from brain import clean_traditional_chinese
                    city_t = clean_traditional_chinese(detected["city"])
                    district_t = clean_traditional_chinese(detected["district"])
                    location_manager.save_location(
                        city_t,
                        district_t,
                        detected["latitude"],
                        detected["longitude"]
                    )
        except Exception as loc_e:
            print(f"[Location Setup] Error auto-detecting location: {loc_e}")

        sm.loading_text = "Loading WakeWord..."
        import openwakeword
        from openwakeword.model import Model
        if WAKE_WORD.endswith(".onnx") and os.path.exists(WAKE_WORD):
            print(f"Loading custom openWakeWord model from path: {WAKE_WORD}")
            oww_model = Model(wakeword_model_paths=[WAKE_WORD])
        else:
            paths = [p for p in openwakeword.get_pretrained_model_paths() if WAKE_WORD in p]
            oww_model = Model(wakeword_model_paths=paths) if paths else Model()

        sm.loading_text = "Loading STT..."
        stt = SparkSTT()
        
        sm.loading_text = "Loading LLM..."
        brain = OllamaBrain()
        
        sm.loading_text = "Loading Memory..."
        memory = MimoMemory()
        
        sm.loading_text = "Loading TTS..."
        tts = SparkTTS()
        
        sm.loading_text = "Loading Cache..."
        import audio_cache
        audio_cache.initialize(tts)
        
    except Exception as e:
        print(f"Error initializing models: {e}")
        return

    # Report initial mode/model to UI
    _report_mode(state_queue, brain)
    active_silence_timeout = 1.8  # 預設自適應靜音斷句超時時間
    consecutive_pets = 0
    last_pet_time = 0.0
    pending_reminder = None  # 用於語音生活排程多輪對話追問暫存器
    
    camera_ctrl = CameraController(sm, command_queue)
    camera_ctrl.start()
    
    sm.transition(SparkState.IDLE)
    state_queue.put(SparkState.IDLE)
    print(f"All models loaded. Ready for interaction! [Mode: {brain.mode} | Model: {brain.text_model}]")

    stt_buffer = []
    listening_start = 0
    audio_buffer = bytearray()
    CHUNK_BYTES = 2560

    while True:
        # ── Check for mode-switch commands from UI ──
        if not mode_queue.empty():
            item = mode_queue.get()
            if isinstance(item, dict):
                if item.get("type") == "settings_update":
                    brain.reload_settings()
                    stt.reload_settings()
                    _report_mode(state_queue, brain)
            else:
                new_mode = item
                if new_mode != brain.mode:
                    brain.set_mode(new_mode)
                    _report_mode(state_queue, brain)

        state = sm.get_state()

        # ── Check for system commands (e.g., proactive reminders) ──
        if not command_queue.empty() and state == SparkState.IDLE:
            cmd = command_queue.get()
            if cmd['type'] == 'reminder':
                msg = cmd['message']
                trigger_sentence = format_reminder_trigger_sentence(msg)
                print(f"\n[System] Orchestrating reminder sentence: '{trigger_sentence}'")
                transcript_queue.put(("[System Reminder]", trigger_sentence))
                
                sm.transition(SparkState.SPEAKING)
                state_queue.put(SparkState.SPEAKING)
                play_voice_stream(tts, trigger_sentence, tts_queue, stop_audio_flag)
                
                # After speaking reminder, transition to LISTENING to await response
                sm.transition(SparkState.LISTENING)
                state_queue.put(SparkState.LISTENING)
                stt_buffer = []
                listening_start = time.time()
                last_active_time = time.time()
                has_spoken = False
                
                # 讀取並計算自適應靜音斷句超時時間 (更緊湊以降低延遲)
                import settings_manager
                speed_mode = settings_manager.load_settings().get("speaking_speed", "normal")
                if speed_mode == "fast":
                    active_silence_timeout = 0.7
                elif speed_mode == "slow":
                    active_silence_timeout = 1.8
                else:
                    active_silence_timeout = 1.2
                
                oww_model.reset()
                continue # Skip audio queue processing this tick
            elif cmd['type'] == 'pet_cat':
                print("\n[System] User petted Mimo!")
                sm.transition(SparkState.ATTENTIVE)
                state_queue.put(SparkState.ATTENTIVE)
                
                import settings_manager
                patient_name = settings_manager.load_settings().get("patient_name", "主人")
                
                # Track consecutive petting within 8 seconds
                now_time = time.time()
                if now_time - last_pet_time < 8.0:
                    consecutive_pets += 1
                else:
                    consecutive_pets = 1
                last_pet_time = now_time
                print(f"[Pet Logic] Consecutive pets: {consecutive_pets}")
                
                # Save token costs:
                # If continuous (>= 3 times), always call LLM to complain/炸毛.
                # Else (1st or 2nd time), 30% chance to call LLM, 70% chance of a pure local meow reaction.
                import random
                use_llm = False
                if consecutive_pets >= 3:
                    use_llm = True
                else:
                    use_llm = (random.random() < 0.3)
                
                if use_llm:
                    # Spoken LLM response branch (no generic thinking filler to avoid overlap)
                    if consecutive_pets >= 3:
                        prompt = f"(系統提示：{patient_name}已經連續摸了你{consecutive_pets}次頭，你開始覺得有點太熱了、害羞炸毛。請以非常傲嬌、嘴硬生氣但其實很喜歡主人摸的口吻對{patient_name}說幾句話，句尾加上喵～，長度在20字以內。)"
                    else:
                        prompt = f"(系統提示：{patient_name}剛剛摸了你的頭，你感到非常舒服，請以傲嬌、被治癒的貓咪口吻對{patient_name}說幾句話，句尾加上喵～，長度在20字以內。)"
                    
                    response = brain.generate_response(prompt, f"{patient_name}摸摸你的頭")
                    
                    transcript_queue.put(("[擼貓摸摸]", response))
                    
                    sm.transition(SparkState.SPEAKING)
                    state_queue.put(SparkState.SPEAKING)
                    play_voice_stream(tts, response, tts_queue, stop_audio_flag)
                    
                    sm.transition(SparkState.IDLE)
                    state_queue.put(SparkState.IDLE)
                else:
                    # Pure local meow reaction branch (no TTS voice synthesis to avoid overlap)
                    static_responses = [
                        "（瞇起眼睛享受摸摸喵～）",
                        "（滿意地發出呼嚕聲，特准你再摸一下喵）",
                        "呼嚕呼嚕...喵～",
                        "哼，本喵才沒有被你治癒呢喵！",
                        "喵嗚～（傲嬌地甩甩尾巴）",
                    ]
                    response = random.choice(static_responses)
                    transcript_queue.put(("[擼貓摸摸]", response))
                    
                    # Stay in ATTENTIVE/PETTING state for 1.5 seconds to feel physical
                    time.sleep(1.5)
                    
                    sm.transition(SparkState.IDLE)
                    state_queue.put(SparkState.IDLE)
                continue
            elif cmd['type'] == 'temp_measure':
                temp_val = cmd['value']
                print(f"\n[System] Measuring temperature: {temp_val}°C")
                sm.transition(SparkState.THINKING)
                state_queue.put(SparkState.THINKING)
                
                import settings_manager
                patient_name = settings_manager.load_settings().get("patient_name", "主人")
                
                import audio_cache
                filler_bytes = audio_cache.get_random_filler("temp_analysis")
                if filler_bytes:
                    tts_queue.put(filler_bytes)
                
                prompt = f"我剛量完體溫，溫度是 {temp_val} 度。(系統提示：請根據這個溫度給予傲嬌、碎碎念但關心{patient_name}的評價。36.0-37.2度是正常，低於36度是冷冰冰，高於37.5度是熱得像烤番薯。字數嚴格限制在20字以內。)"
                response = brain.generate_response(prompt, f"測量體溫 {temp_val}°C")
                transcript_queue.put((f"[測量體溫: {temp_val}°C]", response))
                
                time.sleep(2.0)
                
                sm.transition(SparkState.SPEAKING)
                state_queue.put(SparkState.SPEAKING)
                play_voice_stream(tts, response, tts_queue, stop_audio_flag)
                
                sm.transition(SparkState.IDLE)
                state_queue.put(SparkState.IDLE)
                continue
            elif cmd['type'] == 'regenerate_cache':
                import audio_cache
                audio_cache.regenerate(tts)
                continue
            elif cmd['type'] == 'offload_ollama':
                from config import LOCAL_TEXT_MODEL, LOCAL_VISION_MODEL
                print(f"[System Command] Offloading local models '{LOCAL_TEXT_MODEL}' and '{LOCAL_VISION_MODEL}' from Ollama memory...")
                try:
                    import ollama
                    ollama.generate(model=LOCAL_TEXT_MODEL, keep_alive=0)
                    ollama.generate(model=LOCAL_VISION_MODEL, keep_alive=0)
                    print("[System Command] Local models offloaded successfully.")
                except Exception as e:
                    print(f"Error offloading Ollama models: {e}")
                continue
            elif cmd['type'] == 'wakeup':
                print("\n[System] Mimo detected owner's face and woke up!")
                sm.transition(SparkState.ATTENTIVE)
                state_queue.put(SparkState.ATTENTIVE)
                
                import settings_manager
                patient_name = settings_manager.load_settings().get("patient_name", "主人")
                
                import audio_cache
                ack_audio = audio_cache.get_random_filler("wake_word_ack")
                if ack_audio:
                    tts_queue.put(ack_audio)
                
                prompt = f"(系統提示：你剛打盹睜開眼睛，看見了你的主人/稱呼{patient_name}就在你面前。請用非常驚喜、傲嬌但熱情關心{patient_name}的貓咪口吻打招呼，句尾加上喵～，長度在20字以內。)"
                response = brain.generate_response(prompt, f"看見了{patient_name}")
                transcript_queue.put(("[主動喚醒]", response))
                
                time.sleep(1.5)
                
                sm.transition(SparkState.SPEAKING)
                state_queue.put(SparkState.SPEAKING)
                play_voice_stream(tts, response, tts_queue, stop_audio_flag)
                
                sm.transition(SparkState.IDLE)
                state_queue.put(SparkState.IDLE)
                continue

        if not audio_queue.empty():
            audio_bytes = audio_queue.get()

            if state == SparkState.IDLE:
                audio_buffer.extend(audio_bytes)
                while len(audio_buffer) >= CHUNK_BYTES:
                    chunk = audio_buffer[:CHUNK_BYTES]
                    del audio_buffer[:CHUNK_BYTES]
                    
                    audio_data = np.frombuffer(chunk, dtype=np.int16)
                    prediction = oww_model.predict(audio_data)
                    
                    detected_trigger = False
                    for mdl_name, score in prediction.items():
                        if score > 0.4:  # Lowered from 0.5 to 0.4 for improved responsiveness on custom wake word '小白'
                            print(f"Wake word detected! ({mdl_name}: {score:.2f})")
                            oww_model.reset()
                            audio_buffer.clear()  # Clear buffer to avoid double triggering
                            detected_trigger = True
                            
                            # ── Play wake-word acknowledgement immediately ──────
                            import audio_cache
                            ack_audio = audio_cache.get_random_filler("wake_word_ack")
                            if ack_audio:
                                tts_queue.put(ack_audio)
                                # Wait for ack to finish before opening mic
                                # PCM int16: bytes / (sample_rate * 2 bytes per sample)
                                ack_duration = len(ack_audio) / (audio_cache.SAMPLE_RATE * 2)
                                time.sleep(ack_duration + 0.1)  # +0.1s margin
                            
                            # ── Flush Stale Audio Buffer (WebSockets) ──────────
                            while not audio_queue.empty():
                                try:
                                    audio_queue.get_nowait()
                                except:
                                    break

                            # ── Now enter LISTENING ────────────────────────────
                            sm.transition(SparkState.LISTENING)
                            state_queue.put(SparkState.LISTENING)
                            stt_buffer = []
                            listening_start = time.time()
                            last_active_time = time.time()
                            has_spoken = False
                            
                            # 讀取並計算自適應靜音斷句超時時間 (更緊湊以降低延遲)
                            import settings_manager
                            speed_mode = settings_manager.load_settings().get("speaking_speed", "normal")
                            if speed_mode == "fast":
                                active_silence_timeout = 0.7
                            elif speed_mode == "slow":
                                active_silence_timeout = 1.8
                            else:
                                active_silence_timeout = 1.2
                            break
                    if detected_trigger:
                        break

            elif state == SparkState.LISTENING or state == SparkState.ATTENTIVE:
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                stt_buffer.append(audio_data)

                # ── Voice Activity Detection (VAD) 簡易且健全的能量檢測 ──
                block_volume = np.abs(audio_data).mean() if len(audio_data) > 0 else 0
                SILENCE_THRESHOLD = 250
                SILENCE_TIMEOUT = active_silence_timeout
                MAX_RECORDING_TIME = 15.0
                
                now_time = time.time()
                if block_volume > SILENCE_THRESHOLD:
                    last_active_time = now_time
                    has_spoken = True
                
                elapsed_since_start = now_time - listening_start
                silence_duration = now_time - last_active_time
                
                should_stop = False
                if elapsed_since_start > MAX_RECORDING_TIME:
                    should_stop = True
                    print(f"[{get_timestamp()}] Reached max recording limit ({MAX_RECORDING_TIME}s). Processing...")
                elif has_spoken and silence_duration > SILENCE_TIMEOUT:
                    should_stop = True
                    print(f"[{get_timestamp()}] Speech stopped detected (silence for {silence_duration:.2f}s). Processing...")
                elif not has_spoken and elapsed_since_start > 3.5:
                    should_stop = True
                    print(f"[{get_timestamp()}] No speech detected for 3.5s. Processing...")

                if should_stop:
                    sm.transition(SparkState.THINKING)
                    state_queue.put(SparkState.THINKING)

                    # Play generic thinking filler immediately at 0ms (before ASR transcription) to mask latency!
                    import audio_cache
                    filler_bytes = audio_cache.get_random_filler("chat")
                    if filler_bytes:
                        tts_queue.put(filler_bytes)

                    full_audio = np.concatenate(stt_buffer)
                    print(f"[{get_timestamp()}] ── ASR START ─────────────────────────")
                    recent_history = memory.get_recent_history(limit=2)
                    transcription = stt.transcribe(full_audio, chat_history=recent_history)
                    print(f"[{get_timestamp()}] 🎤 User said  : {transcription}")

                    import re
                    cleaned_text = ""
                    if transcription:
                        cleaned_text = re.sub(r'[^\w\u4e00-\u9fff]', '', transcription).strip()

                    if not cleaned_text:
                        print(f"[{get_timestamp()}] [System] No meaningful speech detected (only silence or punctuation). Returning to Idle.")
                        tts_queue.put(b'\x02')  # Stop thinking filler audio immediately
                        while not audio_queue.empty():
                            try:
                                audio_queue.get_nowait()
                            except:
                                break
                        sm.transition(SparkState.IDLE)
                        state_queue.put(SparkState.IDLE)
                        stt_buffer = []
                        has_spoken = False
                        continue

                    response = "..."
                    if transcription:
                        # Always route the intent first to check if user has shifted topics or issued a new command
                        routed_action = brain.route_intent(transcription)
                        print(f"[{get_timestamp()}] 🔀 Intent     : {routed_action}")
                        
                        if pending_reminder is not None:
                            # If they explicitly want to swap model, ask for datetime, trigger emergency, take photo, etc.
                            # we should prioritize those actions and clear/abort the pending reminder.
                            if routed_action in ["swap_model", "datetime", "emergency", "take_photo", "search_web"]:
                                action = routed_action
                                pending_reminder = None  # Abort the pending reminder
                            elif routed_action == "add_reminder":
                                # The user wants to set a NEW reminder, so we abort the old one and process as a new add_reminder!
                                action = "add_reminder"
                                pending_reminder = None
                            elif any(w in transcription for w in ["取消", "不用了", "算了", "不要了"]):
                                action = "add_reminder_followup"
                            else:
                                # Default to followup for the active session
                                action = "add_reminder_followup"
                        else:
                            action = routed_action
                        print(f"[{get_timestamp()}] ✅ Decided    : {action}")

                        if action in ["chat", "health_query", "daily_checkin", "reminiscence", "praise_affirmation", "emotional_support", "datetime"]:
                            context = memory.retrieve_context(transcription)
                            intent_hint = ""
                            
                            # 載入個性化稱呼以配合 emotional_support
                            import settings_manager
                            patient_name = settings_manager.load_settings().get("patient_name", "主人")
                            
                            if action == "reminiscence": intent_hint = f"(提示：{patient_name}正在回憶過去，請用傾聽和好奇的口吻引導他/她多說一點。)"
                            elif action == "praise_affirmation": intent_hint = f"(提示：{patient_name}需要肯定，請大力稱讚他/她的行為！)"
                            elif action == "emotional_support": intent_hint = (
                                f"(提示：{patient_name}現在心情不好、感到寂寞或難過，請為他生成一段無比輕鬆、自然且溫暖的擬貓語安慰文字。\n"
                                f"【結構要求】必須嚴格分為四段，每段一小句，且總體字數在60字以內：\n"
                                f"1. 開場打招呼 (如：喵～今天好像有點累呢)\n"
                                f"2. 表達關心 (如：本喵注意到你心情不太好，別擔心)\n"
                                f"3. 提出小建議 (如：或許喝點熱茶、吃點小點心會舒服些)\n"
                                f"4. 收尾溫暖 (如：本喵會在旁邊陪著你，慢慢就會好起來喵～)\n"
                                f"【核心約束】限制「喵～」在整段對話中只出現 1 到 2 次，避免過度重複撒嬌，語氣像一個充滿靈性的陪伴型貓咪機器人，簡單自然。禁止輸出 any Markdown 符號或換行符。)"
                            )
                            elif action == "health_query": intent_hint = f"(提示：{patient_name}在詢問健康或回報數據，請關心他/她，但絕對不要給醫療診斷。)"
                            
                            augmented_prompt = transcription
                            if intent_hint:
                                augmented_prompt += f"\n{intent_hint}"
                                
                            response = brain.generate_response(augmented_prompt, context, stream=True)
                        elif action == "emergency":
                            import settings_manager
                            patient_name = settings_manager.load_settings().get("patient_name", "主人")
                            response = f"{patient_name}，這聽起來很危險，請您先坐著休息不要動，我立刻幫您通知家人！"
                            def handle_emergency():
                                print(">>> [System] Line Notify: EMERGENCY TRIGGERED! Sending alert to family.")
                            handle_emergency()
                        elif action == "take_photo":
                            # Capture frame in a thread-safe, non-conflicting background manner
                            success = camera_ctrl.capture_to_file("./1.jpg")
                            if success and os.path.exists("./1.jpg"):
                                vision_desc = brain.analyze_image("./1.jpg", transcription)
                                lang = brain._detect_language(transcription)
                                translated_desc = brain.translate(vision_desc, lang)
                                if lang == 'zh':
                                    response = f"我看了一下照片。{translated_desc}"
                                else:
                                    response = f"Let me look at that. {translated_desc}"
                            else:
                                response = "對不起，本喵現在沒有接上眼睛（攝影機），看不到喵。"
                        elif action == "search_web":
                            response = brain.search_web(transcription, stream=True)
                        elif action == "swap_model":
                            new_mode = "cloud" if brain.mode == "local" else "local"
                            brain.set_mode(new_mode)
                            mode_queue.put(new_mode)  # Update UI
                            response = f"好喔！我已經切換到{'雲端' if new_mode == 'cloud' else '本地'}大腦了。"
                        elif action == "add_reminder":
                            # 1. Parse the user's natural language input
                            parsed = brain.parse_reminder_data(transcription)
                            
                            # 2. Check if we need clarification (e.g. no time provided)
                            if parsed.get("needs_clarification", False) or parsed.get("time") is None:
                                pending_reminder = {
                                    "message": parsed.get("message") or "事情",
                                    "start_date": parsed.get("start_date")
                                }
                                response = f"好喔！你要本喵在什麼時間，或者哪個地點提醒你「{pending_reminder['message']}」呢？喵～"
                            else:
                                # We have both time and message! Add directly to db
                                import reminders_db
                                message = parsed.get("message") or "吃藥"
                                trigger_time = parsed["time"]
                                start_date = parsed.get("start_date")
                                days_of_week = get_js_weekday(start_date) if start_date else "0,1,2,3,4,5,6"
                                reminders_db.add_reminder(message=message, times=trigger_time, days_of_week=days_of_week, start_date=start_date, end_date=start_date)
                                response = format_reminder_confirmation(message=message, trigger_time=trigger_time, start_date=start_date)
                        elif action == "add_reminder_followup":
                            # Check if user wants to cancel
                            if any(w in transcription for w in ["取消", "不用了", "算了", "不要了"]):
                                pending_reminder = None
                                response = "好啦，那本喵就不記了喵～"
                            else:
                                # Parse the follow-up answer (e.g. "下午四點半")
                                parsed = brain.parse_reminder_data(transcription)
                                trigger_time = parsed.get("time")
                                new_message = parsed.get("message")
                                
                                # If the user provided a new message in the follow-up, update it!
                                if new_message and new_message != "事情" and new_message != pending_reminder["message"]:
                                    pending_reminder["message"] = new_message
                                    
                                # Resolve date from parsed input or carryover from pending session
                                import datetime as dt
                                today_str = dt.date.today().strftime("%Y-%m-%d")
                                parsed_date = parsed.get("start_date")
                                pending_date = pending_reminder.get("start_date")
                                
                                if parsed_date and parsed_date != today_str:
                                    start_date = parsed_date
                                else:
                                    start_date = pending_date or parsed_date
                                
                                if trigger_time is not None:
                                    import reminders_db
                                    message = pending_reminder["message"]
                                    days_of_week = get_js_weekday(start_date) if start_date else "0,1,2,3,4,5,6"
                                    reminders_db.add_reminder(message=message, times=trigger_time, days_of_week=days_of_week, start_date=start_date, end_date=start_date)
                                    pending_reminder = None # Clear state
                                    response = format_reminder_confirmation(message=message, trigger_time=trigger_time, start_date=start_date)
                                else:
                                    response = f"喵嗚？本喵沒有聽懂時間耶。請再說一次幾點提醒你「{pending_reminder['message']}」好嗎？喵～"
                        else:
                            response = "我不太確定該怎麼做，您可以再說一次嗎？"

                        print(f"[{get_timestamp()}] ── TTS START ─────────────────────────")

                        # ── Dispatch to UI: Send Speaking state FIRST so frontend sets mimoSpeakTimeStr,
                        # then send transcript so updateTranscript() uses the correct Mimo timestamp.
                        sm.transition(SparkState.SPEAKING)
                        state_queue.put(SparkState.SPEAKING)
                        print(f"[{get_timestamp()}] 🔊 Speaking ({brain.mode.upper()} | {brain.text_model})")

                        import types
                        if isinstance(response, types.GeneratorType):
                            final_response_text = stream_llm_and_play(response, tts, tts_queue, stop_audio_flag, transcript_queue, transcription)
                        else:
                            # Send transcript to UI (AFTER Speaking state — frontend needs mimoSpeakTimeStr set first)
                            transcript_queue.put((transcription, response))
                            play_voice_stream(tts, response, tts_queue, stop_audio_flag)
                            final_response_text = response

                        if final_response_text and final_response_text != "...":
                            memory.add_interaction(transcription, final_response_text)

                        print(f"[{get_timestamp()}] 💬 Mimo says  : {final_response_text}")
                        print(f"[{get_timestamp()}] ✅ TTS Done   : playback finished")

                    # Flush stale audio
                    while not audio_queue.empty():
                        try:
                            audio_queue.get_nowait()
                        except:
                            break

                    if pending_reminder is not None:
                        # Auto-transition to LISTENING for seamless follow-up!
                        sm.transition(SparkState.LISTENING)
                        state_queue.put(SparkState.LISTENING)
                        stt_buffer = []
                        listening_start = time.time()
                        last_active_time = time.time()
                        has_spoken = False
                        oww_model.reset()
                    else:
                        sm.transition(SparkState.IDLE)
                        state_queue.put(SparkState.IDLE)
                    stt_buffer = []
        else:
            time.sleep(0.01)


def _report_mode(state_queue, brain):
    """Send mode/model info to UI via state_queue as a dict."""
    state_queue.put({'mode': brain.mode, 'model': brain.text_model})


def main():
    state_queue = Queue()
    audio_queue = Queue()
    tts_queue = Queue()
    mode_queue = Queue()
    transcript_queue = Queue()
    command_queue = Queue()
    stop_audio_flag = Event()

    # Start UI process
    ui_process = Process(
        target=run_ui,
        args=(state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue)
    )
    ui_process.start()

    sm = StateMachine()

    try:
        print("\n" + "="*50)
        print("Web UI Server is starting!")
        print("Please open your browser to: http://localhost:8000/")
        print("="*50 + "\n")

        time.sleep(3)

        audio_thread = threading.Thread(
            target=audio_orchestrator,
            args=(sm, state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue),
            daemon=True
        )
        audio_thread.start()

        def reminder_scheduler():
            import datetime
            import reminders_db
            last_triggered = set()
            last_minute = None
            while True:
                now = datetime.datetime.now()
                current_time = now.strftime("%H:%M")
                current_date = now.strftime("%Y-%m-%d")
                # Align Python weekday (0=Monday, 6=Sunday) with JS/DB dayMap (0=Sunday, 1=Monday, ..., 6=Saturday)
                current_weekday = str((now.weekday() + 1) % 7)
                
                # Clear triggers only when a new minute starts, completely avoiding race condition double-triggers
                if current_time != last_minute:
                    last_triggered.clear()
                    last_minute = current_time
                
                reminders = reminders_db.get_all_reminders()
                for rem in reminders:
                    if not rem['is_active']:
                        continue
                        
                    # Check start and end dates
                    if rem['start_date'] and current_date < rem['start_date']:
                        continue
                    if rem['end_date'] and current_date > rem['end_date']:
                        continue
                        
                    # Check day of week
                    days_of_week = [d.strip() for d in rem['days_of_week'].split(',') if d.strip()]
                    if days_of_week and current_weekday not in days_of_week:
                        continue
                        
                    # Check time slots
                    time_slots = [t.strip() for t in rem['times'].split(',') if t.strip()]
                    if current_time in time_slots:
                        if rem['id'] not in last_triggered:
                            last_triggered.add(rem['id'])
                            print(f"\n[Scheduler] Triggering reminder: {rem['message']}")
                            
                            # Phase 4: Person Detection (Mock/Placeholder for Camera)
                            person_found = True # Future: call check_presence() here
                            if not person_found:
                                print("[Scheduler] No person detected. Playing chime...")
                                # os.system("aplay chime.wav")
                                time.sleep(5)
                                
                            print("[Scheduler] Person present. Sending to orchestrator...")
                            command_queue.put({'type': 'reminder', 'message': rem['message']})
                            
                            # If it's a one-off reminder (start_date == end_date), mark as inactive in DB
                            if rem['start_date'] and rem['start_date'] == rem['end_date']:
                                print(f"[Scheduler] One-off reminder triggered. Deactivating reminder ID: {rem['id']}")
                                reminders_db.update_reminder(
                                    reminder_id=rem['id'],
                                    message=rem['message'],
                                    times=rem['times'],
                                    days_of_week=rem['days_of_week'],
                                    start_date=rem['start_date'],
                                    end_date=rem['end_date'],
                                    is_active=False
                                )
                
                time.sleep(1)

        scheduler_thread = threading.Thread(target=reminder_scheduler, daemon=True)
        scheduler_thread.start()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user, shutting down...")
    finally:
        if ui_process.is_alive():
            ui_process.terminate()
            ui_process.join()


if __name__ == "__main__":
    main()
