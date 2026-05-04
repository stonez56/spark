import ollama
try:
    with open('1.jpg', 'rb') as f:
        img_bytes = f.read()
    response = ollama.chat(
        model='moondream',
        messages=[{'role': 'user', 'content': 'Describe this image', 'images': [img_bytes]}]
    )
    print(response['message']['content'])
except Exception as e:
    print("Error:", e)
