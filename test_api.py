import requests

data = {
    "model": "moondream",
    "prompt": "Describe ./1.jpg",
    "stream": False
}

try:
    resp = requests.post("http://localhost:11434/api/generate", json=data)
    print(resp.status_code)
    print(resp.text)
except Exception as e:
    print(e)
