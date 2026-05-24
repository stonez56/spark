"""
interactive_wake_word_tester.py — Browser-based wake word tester (no PortAudio needed).

Since headless/remote machines cannot access the local mic directly via PortAudio,
this script starts a tiny HTTP + WebSocket server that:
  1. Serves a minimal browser page that opens the mic
  2. Receives audio chunks from the browser via WebSocket
  3. Feeds them to openWakeWord and prints results in real-time

Usage:
    python tests/interactive_wake_word_tester.py              # test "alexa" (default)
    python tests/interactive_wake_word_tester.py hey_jarvis
    python tests/interactive_wake_word_tester.py hey_mycroft

Then open:  http://localhost:9999/
"""

import sys
import time
import numpy as np
import warnings
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

warnings.filterwarnings("ignore")

WAKE_WORD  = sys.argv[1] if len(sys.argv) > 1 else "alexa"
PORT       = 9999
THRESHOLD  = 0.5
COOLDOWN   = 2.0   # seconds between detections

app = FastAPI()

# ── Global Model Reference (loaded lazily to avoid overhead during import) ─────
oww_model = None

def get_model():
    global oww_model
    if oww_model is None:
        import openwakeword
        from openwakeword.model import Model
        
        all_paths = openwakeword.get_pretrained_model_paths()
        paths = [p for p in all_paths if WAKE_WORD in p]

        if not paths:
            print(f"[ERROR] No model found for '{WAKE_WORD}'.")
            print("Available models:", [p.split("/")[-1].replace(".onnx","") for p in all_paths])
            sys.exit(1)

        print(f"Loading model for '{WAKE_WORD}'...", end="", flush=True)
        oww_model = Model(wakeword_model_paths=paths)
        oww_model.predict(np.zeros(1280, dtype=np.int16))  # warmup
        print(" ready!\n")
    return oww_model

# ── HTML page served to browser ────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Wake Word Tester</title>
  <style>
    body {{ background:#0a0a0f; color:#e0e0e0; font-family:monospace;
           display:flex; flex-direction:column; align-items:center;
           justify-content:center; height:100vh; margin:0; }}
    h2   {{ color:#00ffff; margin-bottom:8px; }}
    #status {{ font-size:18px; color:#aaa; margin:10px; }}
    #bar {{ font-size:14px; color:#00ffff; font-family:monospace; margin:6px; }}
    #log {{ max-height:200px; overflow-y:auto; width:500px; margin-top:20px;
            background:#111; padding:10px; border-radius:8px; font-size:13px; }}
    .detect {{ color:#00ff88; font-weight:bold; }}
  </style>
</head>
<body>
  <h2>🎤 Wake Word Tester</h2>
  <p id="status">Connecting...</p>
  <p id="bar"></p>
  <div id="log"></div>

  <script>
    const WAKE_WORD = "{WAKE_WORD}";
    const ws = new WebSocket(`ws://localhost:{PORT}/ws`);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {{
      document.getElementById('status').textContent = `Listening for "${{WAKE_WORD}}" — speak now!`;
      startMic();
    }};

    ws.onmessage = (e) => {{
      const msg = JSON.parse(e.data);
      const bar_filled = Math.round(msg.score * 20);
      const bar = '█'.repeat(bar_filled) + '░'.repeat(20 - bar_filled);
      document.getElementById('bar').textContent = `[${{bar}}] ${{msg.score.toFixed(3)}}`;
      if (msg.detected) {{
        const log = document.getElementById('log');
        const line = document.createElement('div');
        line.className = 'detect';
        line.textContent = `✅ DETECTED! score=${{msg.score.toFixed(3)}}  (${{new Date().toLocaleTimeString()}})`;
        log.appendChild(line);
        log.scrollTop = log.scrollHeight;
      }}
    }};

    async function startMic() {{
      const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
      const ctx = new AudioContext({{ sampleRate: 16000 }});
      const src = ctx.createMediaStreamSource(stream);
      const proc = ctx.createScriptProcessor(2048, 1, 1);

      proc.onaudioprocess = (e) => {{
        const input = e.inputBuffer.getChannelData(0);
        const pcm = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++)
          pcm[i] = Math.max(-1, Math.min(1, input[i])) * 0x7FFF;
        if (ws.readyState === WebSocket.OPEN)
          ws.send(pcm.buffer);
      }};

      src.connect(proc);
      proc.connect(ctx.destination);
    }}
  </script>
</body>
</html>"""

@app.get("/")
async def index():
    return HTMLResponse(HTML)

detect_count  = 0
last_detected = 0.0

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    global detect_count, last_detected
    model = get_model()
    await websocket.accept()
    print(f'Browser connected. Say "{WAKE_WORD}"...')
    try:
        while True:
            data = await websocket.receive_bytes()
            audio = np.frombuffer(data, dtype=np.int16)
            prediction = model.predict(audio)

            for model_name, score in prediction.items():
                now = time.time()
                detected = (score >= THRESHOLD and (now - last_detected) > WAKE_WORD_COOLDOWN_SEC) if 'WAKE_WORD_COOLDOWN_SEC' in globals() else (score >= THRESHOLD and (now - last_detected) > COOLDOWN)

                if detected:
                    detect_count += 1
                    last_detected = now
                    model.reset()
                    print(f"✅ DETECTED! score={score:.3f}  (#{detect_count})", flush=True)
                else:
                    bar_len = int(score * 20)
                    bar = "█" * bar_len + "░" * (20 - bar_len)
                    print(f"\r  [{bar}] {score:.3f} ", end="", flush=True)

                await websocket.send_json({"score": round(float(score), 4), "detected": bool(detected)})

    except WebSocketDisconnect:
        print("\nBrowser disconnected.")

if __name__ == "__main__":
    print(f"{'='*50}")
    print(f"  Interactive Wake Word Tester (Browser-based)")
    print(f"  Keyword   : {WAKE_WORD}")
    print(f"  Threshold : {THRESHOLD}")
    print(f"{'='*50}")
    print(f"\n👉 Open your browser at:  http://localhost:{PORT}/\n")
    
    # Load the model explicitly on startup
    get_model()
    
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
