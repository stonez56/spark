import logging
import asyncio
import json
import queue

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from state_machine import SparkState

# Setup FastAPI app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("static/index.html")

@app.get("/config")
async def get_config():
    return FileResponse("static/config.html")

# Keep track of connected websocket clients
connected_clients = set()

# A global reference to the latest state
current_state = SparkState.LOADING.value

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Initialize the ASGI scope write lock for the websocket to serialize writes
    websocket.scope["write_lock"] = asyncio.Lock()
    connected_clients.add(websocket)
    print("🟢 [WebSocket] Browser client connected!")
    # Send the current state immediately upon connection
    await _safe_send_text(websocket, json.dumps({"type": "state", "value": current_state}))
    audio_active_printed = False
    try:
        while True:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                break
            elif "text" in data:
                # Handle text commands from client (e.g. "stop_audio")
                try:
                    msg = json.loads(data["text"])
                    msg_type = msg.get("type")
                    if msg_type == "stop_audio":
                        # Signal the audio orchestrator to stop playback
                        if hasattr(app.state, 'stop_audio_flag'):
                            app.state.stop_audio_flag.set()
                    elif msg_type == "pet_cat":
                        if hasattr(app.state, 'command_queue') and app.state.command_queue:
                            app.state.command_queue.put({'type': 'pet_cat'})
                    elif msg_type == "temp_measure":
                        if hasattr(app.state, 'command_queue') and app.state.command_queue:
                            app.state.command_queue.put({'type': 'temp_measure', 'value': msg.get('value', 36.5)})
                except Exception as e:
                    print(f"Error handling text websocket message: {e}")
            elif "bytes" in data:
                if not audio_active_printed:
                    print("🎙️ [WebSocket] Audio stream active (receiving microphone data)...")
                    audio_active_printed = True
                if app.state.audio_queue:
                    app.state.audio_queue.put(data["bytes"])
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print("🔴 [WebSocket] Browser client disconnected.")


@app.post("/api/set-mode")
async def set_mode(payload: dict):
    """Switch between 'local' and 'cloud' LLM mode at runtime."""
    mode = payload.get("mode", "local")
    if hasattr(app.state, 'mode_queue'):
        app.state.mode_queue.put(mode)
    return JSONResponse({"status": "ok", "mode": mode})


@app.get("/api/status")
async def get_status():
    """Return current mode and model info."""
    return JSONResponse({
        "mode": getattr(app.state, 'current_mode', 'local'),
        "model": getattr(app.state, 'current_model', 'gemma3:1b'),
    })

# --- Reminder API Endpoints ---
import reminders_db

@app.get("/api/reminders")
async def get_reminders():
    return JSONResponse(reminders_db.get_all_reminders())

@app.post("/api/reminders")
async def add_reminder(payload: dict):
    reminders_db.add_reminder(
        payload.get("message"), 
        payload.get("times"), 
        payload.get("days_of_week", "0,1,2,3,4,5,6"), 
        payload.get("start_date"), 
        payload.get("end_date"), 
        payload.get("is_active", True)
    )
    return JSONResponse({"status": "ok"})

@app.put("/api/reminders/{reminder_id}")
async def update_reminder(reminder_id: int, payload: dict):
    reminders_db.update_reminder(
        reminder_id, 
        payload.get("message"), 
        payload.get("times"), 
        payload.get("days_of_week", "0,1,2,3,4,5,6"), 
        payload.get("start_date"), 
        payload.get("end_date"), 
        payload.get("is_active", True)
    )
    return JSONResponse({"status": "ok"})

@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int):
    reminders_db.delete_reminder(reminder_id)
    return JSONResponse({"status": "ok"})

# --- Settings API Endpoints ---
import settings_manager

@app.get("/api/settings")
async def get_settings():
    return JSONResponse(settings_manager.load_settings())

@app.post("/api/settings")
async def update_settings(payload: dict):
    settings = settings_manager.load_settings()
    need_regenerate = False
    
    if "patient_name" in payload:
        if payload["patient_name"] != settings.get("patient_name"):
            settings["patient_name"] = payload["patient_name"]
            need_regenerate = True
            
    if "caregiver_name" in payload:
        settings["caregiver_name"] = payload["caregiver_name"]
        
    if "speaking_speed" in payload:
        settings["speaking_speed"] = payload["speaking_speed"]
        
    if "dialogue_mode" in payload:
        new_dialogue_mode = payload["dialogue_mode"]
        if new_dialogue_mode != settings.get("dialogue_mode"):
            settings["dialogue_mode"] = new_dialogue_mode
            if hasattr(app.state, 'mode_queue'):
                app.state.mode_queue.put(new_dialogue_mode)

    if "routing_mode" in payload:
        new_routing_mode = payload["routing_mode"]
        if new_routing_mode != settings.get("routing_mode"):
            settings["routing_mode"] = new_routing_mode
            # Notify the audio orchestrator to reload settings & switch mode
            if hasattr(app.state, 'mode_queue'):
                app.state.mode_queue.put({"type": "settings_update"})
                
    if "offload_local_llm" in payload:
        new_offload = bool(payload["offload_local_llm"])
        if new_offload != settings.get("offload_local_llm"):
            settings["offload_local_llm"] = new_offload
            # If offloading is turned ON while active mode is cloud, trigger offload immediately
            if new_offload and settings.get("dialogue_mode", "local") == "cloud":
                if hasattr(app.state, 'command_queue'):
                    app.state.command_queue.put({'type': 'offload_ollama'})
                    
    if "cloud_text_model" in payload:
        new_cloud_model = payload["cloud_text_model"]
        if new_cloud_model != settings.get("cloud_text_model"):
            settings["cloud_text_model"] = new_cloud_model
            if hasattr(app.state, 'mode_queue'):
                app.state.mode_queue.put({"type": "settings_update"})
                
    if "cloud_use_reasoning" in payload:
        new_reasoning = bool(payload["cloud_use_reasoning"])
        if new_reasoning != settings.get("cloud_use_reasoning", False):
            settings["cloud_use_reasoning"] = new_reasoning
            if hasattr(app.state, 'mode_queue'):
                app.state.mode_queue.put({"type": "settings_update"})
        
    settings_manager.save_settings(settings)
    
    if need_regenerate and hasattr(app.state, 'command_queue'):
        app.state.command_queue.put({'type': 'regenerate_cache'})
        
    return JSONResponse({"status": "ok"})

# --- Location API Endpoints ---
import location_manager

@app.get("/api/location")
async def get_location_endpoint():
    return JSONResponse(location_manager.get_location())

@app.post("/api/location")
async def set_location_endpoint(payload: dict):
    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is not None and lon is not None:
        city, district = location_manager.reverse_geocode(lat, lon)
        location_manager.save_location(city, district, lat, lon)
        return JSONResponse({"status": "ok", "city": city, "district": district, "latitude": lat, "longitude": lon})
    return JSONResponse({"status": "error", "message": "經緯度缺失"}, status_code=400)

@app.post("/api/location/manual")
async def set_location_manual_endpoint(payload: dict):
    city = payload.get("city", "")
    district = payload.get("district", "")
    location_manager.save_location(city, district)
    return JSONResponse({"status": "ok", "city": city, "district": district})

@app.post("/api/location/autodetect")
async def set_location_autodetect_endpoint():
    loc = location_manager.auto_detect_ip()
    if loc:
        location_manager.save_location(loc["city"], loc["district"], loc["latitude"], loc["longitude"])
        return JSONResponse({"status": "ok", "city": loc["city"], "district": loc["district"]})
    return JSONResponse({"status": "error", "message": "IP 定位失敗"}, status_code=500)

@app.post("/api/reset-db")
async def reset_db_endpoint():
    try:
        from reset_db import reset_database
        reset_database()
        return JSONResponse({"status": "ok", "message": "記憶與資料庫已完全清除喵！"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"清除失敗：{str(e)}"}, status_code=500)


@app.post("/api/debug-log")
async def debug_log(payload: dict):
    print(f"🖥️ [Browser Log] {payload.get('message')}")
    return JSONResponse({"status": "ok"})





async def _safe_send_text(websocket: WebSocket, text: str):
    if "write_lock" not in websocket.scope:
        websocket.scope["write_lock"] = asyncio.Lock()
    async with websocket.scope["write_lock"]:
        await websocket.send_text(text)


async def _safe_send_bytes(websocket: WebSocket, data: bytes):
    if "write_lock" not in websocket.scope:
        websocket.scope["write_lock"] = asyncio.Lock()
    async with websocket.scope["write_lock"]:
        await websocket.send_bytes(data)


async def broadcast(message: dict):
    dead = set()
    payload = json.dumps(message)
    for client in list(connected_clients):
        try:
            await _safe_send_text(client, payload)
        except Exception as e:
            logging.warning(f"Error broadcasting text to client, removing from active: {e}")
            dead.add(client)
    connected_clients.difference_update(dead)


async def broadcast_state(state: str):
    global current_state
    current_state = state
    await broadcast({"type": "state", "value": state})


async def broadcast_transcript(user_text: str, spark_text: str):
    await broadcast({"type": "transcript", "user": user_text, "spark": spark_text})


async def broadcast_audio(audio_bytes: bytes):
    print(f"[Web UI] Broadcasting {len(audio_bytes)} bytes of audio to clients...")
    dead = set()
    for client in list(connected_clients):
        try:
            await _safe_send_bytes(client, audio_bytes)
        except Exception as e:
            logging.error(f"Error sending audio to websocket, removing from active: {e}")
            dead.add(client)
    connected_clients.difference_update(dead)


async def run_server_loop(state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue):
    app.state.audio_queue = audio_queue
    app.state.mode_queue = mode_queue
    app.state.stop_audio_flag = stop_audio_flag
    app.state.command_queue = command_queue
    settings = settings_manager.load_settings()
    app.state.current_mode = settings.get("dialogue_mode", "local")
    if app.state.current_mode == "cloud":
        app.state.current_model = settings.get("cloud_text_model", "openai/gpt-oss-120b:free")
    else:
        app.state.current_model = "llama3.2:3b"

    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)

    server_task = asyncio.create_task(server.serve())

    async def monitor_state_queue():
        while True:
            try:
                while True:
                    item = state_queue.get_nowait()
                    if isinstance(item, dict):
                        # Mode/model update dict — update state and broadcast to frontend
                        app.state.current_mode = item.get('mode', app.state.current_mode)
                        app.state.current_model = item.get('model', app.state.current_model)
                        await broadcast({
                            "type": "model_info",
                            "mode": app.state.current_mode,
                            "model": app.state.current_model,
                        })
                    else:
                        await broadcast_state(item.value)
            except queue.Empty:
                pass
            await asyncio.sleep(0.05)

    async def monitor_tts_queue():
        while True:
            # Drain ALL pending audio chunks per iteration to prevent gaps in streaming playback.
            # A single 50ms sleep with one-item-per-cycle causes silent gaps between TTS chunks.
            drained = False
            try:
                while True:
                    audio_bytes = tts_queue.get_nowait()
                    await broadcast_audio(audio_bytes)
                    drained = True
            except queue.Empty:
                pass
            # If nothing was available, yield control briefly
            if not drained:
                await asyncio.sleep(0.01)

    async def monitor_transcript_queue():
        while True:
            try:
                while True:
                    user_text, spark_text = transcript_queue.get_nowait()
                    await broadcast_transcript(user_text, spark_text)
            except queue.Empty:
                pass
            await asyncio.sleep(0.05)

    state_task = asyncio.create_task(monitor_state_queue())
    tts_task = asyncio.create_task(monitor_tts_queue())
    transcript_task = asyncio.create_task(monitor_transcript_queue())

    try:
        await asyncio.gather(server_task, state_task, tts_task, transcript_task)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        # Suppress noisy multiprocessing queue errors or bad descriptor errors during abrupt teardown
        logging.debug(f"[Web UI] Loop exception during teardown: {e}")


def run_ui(state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue):
    """Entry point for the UI process"""
    try:
        asyncio.run(run_server_loop(state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue))
    except (KeyboardInterrupt, SystemExit):
        pass  # Graceful exit on user cancellation or process exit
    except Exception as e:
        print(f"[Web UI] Server process exception: {e}")
