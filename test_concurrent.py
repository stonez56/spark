import ollama
import time

print("Loading text model...")
ollama.generate(model='gemma3:1b', prompt='hello', keep_alive=-1)

print("Loading vision model with small image...")
with open('1.jpg', 'rb') as f:
    img_bytes = f.read()
try:
    response = ollama.generate(
        model='moondream',
        prompt='Describe this',
        images=[img_bytes],
        keep_alive=-1
    )
    print("Success:", response['response'])
except Exception as e:
    print("Vision Model Error:", e)
