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

# Suppress onnxruntime CUDAExecutionProvider warnings for Raspberry Pi
warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")

from state_machine import StateMachine, SparkState
from ui import run_ui
from memory import SparkMemory
from brain import OllamaBrain
from stt import SparkSTT
from tts import SparkTTS
from config import LLM_MODE, LOCAL_TEXT_MODEL, CLOUD_TEXT_MODEL

def audio_orchestrator(sm, state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue):
    print("Loading AI Models...")
    
    try:
        import openwakeword
        from openwakeword.model import Model
        wake_word = "alexa"
        paths = [p for p in openwakeword.get_pretrained_model_paths() if wake_word in p]
        oww_model = Model(wakeword_model_paths=paths) if paths else Model()

        stt = SparkSTT(model_size="base")
        brain = OllamaBrain()
        memory = SparkMemory()
        tts = SparkTTS()
        
        import audio_cache
        audio_cache.initialize(tts)
        
    except Exception as e:
        print(f"Error initializing models: {e}")
        return

    # Report initial mode/model to UI
    _report_mode(state_queue, brain)
    print(f"All models loaded. Ready for interaction! [Mode: {brain.mode} | Model: {brain.text_model}]")

    stt_buffer = []
    listening_start = 0

    while True:
        # ── Check for mode-switch commands from UI ──
        if not mode_queue.empty():
            new_mode = mode_queue.get()
            if new_mode != brain.mode:
                brain.mode = new_mode
                if new_mode == "cloud":
                    from config import CLOUD_TEXT_MODEL
                    brain.text_model = CLOUD_TEXT_MODEL
                    brain._init_cloud_client()
                else:
                    from config import LOCAL_TEXT_MODEL
                    brain.text_model = LOCAL_TEXT_MODEL
                    brain.mode = "local"
                _report_mode(state_queue, brain)
                print(f"[Mode Switch] → {brain.mode.upper()} | Model: {brain.text_model}")

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
                oww_model.reset()
                continue # Skip audio queue processing this tick
            elif cmd['type'] == 'regenerate_cache':
                import audio_cache
                audio_cache.regenerate(tts)
                continue

        if not audio_queue.empty():
            audio_bytes = audio_queue.get()
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

            if state == SparkState.IDLE:
                prediction = oww_model.predict(audio_data)
                for mdl_name, score in prediction.items():
                    if score > 0.5:
                        print(f"Wake word detected! ({score:.2f})")
                        oww_model.reset()
                        
                        # ── Play wake-word acknowledgement immediately ──────
                        import audio_cache
                        ack_audio = audio_cache.get_random_filler("wake_word_ack")
                        if ack_audio:
                            tts_queue.put(ack_audio)
                            # Wait for ack to finish before opening mic
                            # PCM int16: bytes / (sample_rate * 2 bytes per sample)
                            ack_duration = len(ack_audio) / (audio_cache.SAMPLE_RATE * 2)
                            time.sleep(ack_duration + 0.1)  # +0.1s margin
                        
                        # ── Now enter LISTENING ────────────────────────────
                        sm.transition(SparkState.LISTENING)
                        state_queue.put(SparkState.LISTENING)
                        stt_buffer = []
                        listening_start = time.time()

            elif state == SparkState.LISTENING or state == SparkState.ATTENTIVE:
                stt_buffer.append(audio_data)

                if time.time() - listening_start > 4.0:
                    print("Finished listening. Processing...")
                    sm.transition(SparkState.THINKING)
                    state_queue.put(SparkState.THINKING)

                    full_audio = np.concatenate(stt_buffer)
                    transcription = stt.transcribe(full_audio)
                    print(f"User: {transcription}")

                    response = "..."
                    if transcription:
                        action = brain.route_intent(transcription)
                        print(f"Decided action: {action}")
                        
                        import audio_cache
                        filler_bytes = audio_cache.get_random_filler(action)
                        if filler_bytes:
                            # Play filler audio immediately
                            tts_queue.put(filler_bytes)

                        if action in ["chat", "health_query", "daily_checkin", "reminiscence", "praise_affirmation", "emotional_support"]:
                            context = memory.retrieve_context(transcription)
                            intent_hint = ""
                            if action == "reminiscence": intent_hint = "(提示：長輩正在回憶過去，請用傾聽和好奇的口吻引導他們多說一點。)"
                            elif action == "praise_affirmation": intent_hint = "(提示：長輩需要肯定，請大力稱讚他們的行為！)"
                            elif action == "emotional_support": intent_hint = "(提示：長輩心情低落或寂寞，請用非常溫柔撒嬌的語氣安撫他們。)"
                            elif action == "health_query": intent_hint = "(提示：長輩在詢問健康或回報數據，請關心他們，但絕對不要給醫療診斷。)"
                            
                            augmented_prompt = transcription
                            if intent_hint:
                                augmented_prompt += f"\n{intent_hint}"
                                
                            response = brain.generate_response(augmented_prompt, context)
                            memory.add_interaction(transcription, response)
                        elif action == "emergency":
                            import settings_manager
                            patient_name = settings_manager.load_settings().get("patient_name", "阿公")
                            response = f"{patient_name}，這聽起來很危險，請您先坐著休息不要動，我立刻幫您通知家人！"
                            def handle_emergency():
                                print(">>> [System] Line Notify: EMERGENCY TRIGGERED! Sending alert to family.")
                            handle_emergency()
                        elif action == "take_photo":
                            import os
                            if os.path.exists("./1.jpg"):
                                vision_desc = brain.analyze_image("./1.jpg", transcription)
                                lang = brain._detect_language(transcription)
                                translated_desc = brain.translate(vision_desc, lang)
                                if lang == 'zh':
                                    response = f"我看了一下照片。{translated_desc}"
                                else:
                                    response = f"Let me look at that. {translated_desc}"
                            else:
                                response = "對不起，我現在沒有接上眼睛（攝影機），看不到。"
                        elif action == "search_web":
                            response = brain.search_web(transcription)
                        elif action == "swap_model":
                            new_mode = "cloud" if brain.mode == "local" else "local"
                            brain.set_mode(new_mode)
                            mode_queue.put(new_mode)  # Update UI
                            response = f"好喔！我已經切換到{'雲端' if new_mode == 'cloud' else '本地'}大腦了。"
                        else:
                            response = "我不太確定該怎麼做，您可以再說一次嗎？"

                        print(f"Spark [{brain.mode.upper()} | {brain.text_model}]: {response}")

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
