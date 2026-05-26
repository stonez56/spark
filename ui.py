import asyncio
import logging
import json
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
    connected_clients.add(websocket)
    print("🟢 [WebSocket] Browser client connected!")
    # Send the current state immediately upon connection
    await websocket.send_text(json.dumps({"type": "state", "value": current_state}))
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
        
    settings_manager.save_settings(settings)
    
    if need_regenerate and hasattr(app.state, 'command_queue'):
        app.state.command_queue.put({'type': 'regenerate_cache'})
        
    return JSONResponse({"status": "ok"})


@app.post("/api/reset-db")
async def reset_db_endpoint():
    try:
        from reset_db import reset_database
        reset_database()
        return JSONResponse({"status": "ok", "message": "記憶與資料庫已完全清除喵！"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"清除失敗：{str(e)}"}, status_code=500)





async def broadcast(message: dict):
    dead = set()
    for client in connected_clients:
        try:
            await client.send_text(json.dumps(message))
        except Exception:
            dead.add(client)
    connected_clients.difference_update(dead)


async def broadcast_state(state: str):
    global current_state
    current_state = state
    await broadcast({"type": "state", "value": state})


async def broadcast_transcript(user_text: str, spark_text: str):
    await broadcast({"type": "transcript", "user": user_text, "spark": spark_text})


async def broadcast_audio(audio_bytes: bytes):
    for client in connected_clients:
        try:
            await client.send_bytes(audio_bytes)
        except Exception as e:
            logging.error(f"Error sending audio to websocket: {e}")


async def run_server_loop(state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue):
    app.state.audio_queue = audio_queue
    app.state.mode_queue = mode_queue
    app.state.stop_audio_flag = stop_audio_flag
    app.state.command_queue = command_queue
    app.state.current_mode = 'local'
    app.state.current_model = 'gemma3:1b'

    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)

    server_task = asyncio.create_task(server.serve())

    async def monitor_state_queue():
        while True:
            if not state_queue.empty():
                item = state_queue.get()
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
            await asyncio.sleep(0.05)

    async def monitor_tts_queue():
        while True:
            if not tts_queue.empty():
                audio_bytes = tts_queue.get()
                await broadcast_audio(audio_bytes)
            await asyncio.sleep(0.05)

    async def monitor_transcript_queue():
        while True:
            if not transcript_queue.empty():
                user_text, spark_text = transcript_queue.get()
                await broadcast_transcript(user_text, spark_text)
            await asyncio.sleep(0.05)

    state_task = asyncio.create_task(monitor_state_queue())
    tts_task = asyncio.create_task(monitor_tts_queue())
    transcript_task = asyncio.create_task(monitor_transcript_queue())

    await asyncio.gather(server_task, state_task, tts_task, transcript_task)


def run_ui(state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue):
    """Entry point for the UI process"""
    asyncio.run(run_server_loop(state_queue, audio_queue, tts_queue, mode_queue, transcript_queue, stop_audio_flag, command_queue))
