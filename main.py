import os
import warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

import time
import threading
import warnings
import numpy as np
from multiprocessing import Process, Queue, Event
from datetime import datetime

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

def audio_orchestrator(sm, state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue):
    # Initialize and start OLED first so it shows loading status on SSD1306
    oled_ctrl = OLEDController(sm)
    oled_ctrl.start()
    
    print("Loading AI Models...")
    
    try:
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
        stt = SparkSTT(model_size="base")
        
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
            new_mode = mode_queue.get()
            if new_mode != brain.mode:
                brain.set_mode(new_mode)
                _report_mode(state_queue, brain)

        state = sm.get_state()

        # ── Check for system commands (e.g., proactive reminders) ──
        if not command_queue.empty() and state == SparkState.IDLE:
            cmd = command_queue.get()
            if cmd['type'] == 'reminder':
                msg = cmd['message']
                print(f"\n[System] Orchestrating reminder: {msg}")
                transcript_queue.put(("[System Reminder]", msg))
                
                sm.transition(SparkState.SPEAKING)
                state_queue.put(SparkState.SPEAKING)
                stop_audio_flag.clear()
                
                audio_output = tts.synthesize(msg)
                tts_queue.put(audio_output)
                
                audio_duration = len(audio_output) / (22050 * 2)
                elapsed = 0
                step = 0.05
                while elapsed < audio_duration:
                    if stop_audio_flag.is_set():
                        break
                    time.sleep(step)
                    elapsed += step
                
                # After speaking reminder, transition to LISTENING to await response
                sm.transition(SparkState.LISTENING)
                state_queue.put(SparkState.LISTENING)
                stt_buffer = []
                listening_start = time.time()
                last_active_time = time.time()
                has_spoken = False
                
                # 讀取並計算自適應靜音斷句超時時間
                import settings_manager
                speed_mode = settings_manager.load_settings().get("speaking_speed", "normal")
                if speed_mode == "fast":
                    active_silence_timeout = 1.2
                elif speed_mode == "slow":
                    active_silence_timeout = 2.5
                else:
                    active_silence_timeout = 1.8
                
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
                    stop_audio_flag.clear()
                    
                    audio_output = tts.synthesize(response)
                    tts_queue.put(audio_output)
                    
                    audio_duration = len(audio_output) / (22050 * 2)
                    elapsed = 0
                    step = 0.05
                    while elapsed < audio_duration:
                        if stop_audio_flag.is_set():
                            break
                        time.sleep(step)
                        elapsed += step
                    
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
                stop_audio_flag.clear()
                
                audio_output = tts.synthesize(response)
                tts_queue.put(audio_output)
                
                audio_duration = len(audio_output) / (22050 * 2)
                elapsed = 0
                step = 0.05
                while elapsed < audio_duration:
                    if stop_audio_flag.is_set():
                        break
                    time.sleep(step)
                    elapsed += step
                
                sm.transition(SparkState.IDLE)
                state_queue.put(SparkState.IDLE)
                continue
            elif cmd['type'] == 'regenerate_cache':
                import audio_cache
                audio_cache.regenerate(tts)
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
                stop_audio_flag.clear()
                
                audio_output = tts.synthesize(response)
                tts_queue.put(audio_output)
                
                audio_duration = len(audio_output) / (22050 * 2)
                elapsed = 0
                step = 0.05
                while elapsed < audio_duration:
                    if stop_audio_flag.is_set():
                        break
                    time.sleep(step)
                    elapsed += step
                
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
                            
                            # 讀取並計算自適應靜音斷句超時時間
                            import settings_manager
                            speed_mode = settings_manager.load_settings().get("speaking_speed", "normal")
                            if speed_mode == "fast":
                                active_silence_timeout = 1.2
                            elif speed_mode == "slow":
                                active_silence_timeout = 2.5
                            else:
                                active_silence_timeout = 1.8
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

                    full_audio = np.concatenate(stt_buffer)
                    transcription = stt.transcribe(full_audio)
                    print(f"[{get_timestamp()}] User: {transcription}")

                    import re
                    cleaned_text = ""
                    if transcription:
                        cleaned_text = re.sub(r'[^\w\u4e00-\u9fff]', '', transcription).strip()

                    if not cleaned_text:
                        print(f"[{get_timestamp()}] [System] No meaningful speech detected (only silence or punctuation). Returning to Idle.")
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

                    # Play generic thinking filler immediately at 0ms to hide routing/LLM generation latency
                    import audio_cache
                    filler_bytes = audio_cache.get_random_filler("chat")
                    if filler_bytes:
                        tts_queue.put(filler_bytes)

                    response = "..."
                    if transcription:
                        action = brain.route_intent(transcription)
                        print(f"[{get_timestamp()}] Decided action: {action}")

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
                                
                            response = brain.generate_response(augmented_prompt, context)
                            memory.add_interaction(transcription, response)
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
                            response = brain.search_web(transcription)
                        elif action == "swap_model":
                            new_mode = "cloud" if brain.mode == "local" else "local"
                            brain.set_mode(new_mode)
                            mode_queue.put(new_mode)  # Update UI
                            response = f"好喔！我已經切換到{'雲端' if new_mode == 'cloud' else '本地'}大腦了。"
                        else:
                            response = "我不太確定該怎麼做，您可以再說一次嗎？"

                        print(f"[{get_timestamp()}] Spark [{brain.mode.upper()} | {brain.text_model}]: {response}")

                        # Send transcript to UI
                        transcript_queue.put((transcription, response))

                        # TTS
                        sm.transition(SparkState.SPEAKING)
                        state_queue.put(SparkState.SPEAKING)

                        stop_audio_flag.clear()
                        audio_output = tts.synthesize(response)
                        tts_queue.put(audio_output)

                        # Wait for audio duration, but allow ESC to interrupt
                        audio_duration = len(audio_output) / (22050 * 2)
                        elapsed = 0
                        step = 0.05
                        while elapsed < audio_duration:
                            if stop_audio_flag.is_set():
                                print("Audio stopped by user (ESC).")
                                break
                            time.sleep(step)
                            elapsed += step

                    # Flush stale audio
                    while not audio_queue.empty():
                        try:
                            audio_queue.get_nowait()
                        except:
                            break

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
            while True:
                now = datetime.datetime.now()
                current_time = now.strftime("%H:%M")
                current_date = now.strftime("%Y-%m-%d")
                current_weekday = str(now.weekday()) # 0=Monday, 6=Sunday
                
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
                
                if now.second == 0:
                    last_triggered.clear()
                    
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

if __name__ == "__main__":
    main()
