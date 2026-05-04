import ollama

def test_intent(prompt):
    system = """You are an Intent Router. Reply ONLY with a JSON object containing the key 'action'.
Actions:
- 'chat': Normal conversation or general questions.
- 'take_photo': The user asks you to look at something, see something, describe an image, or take a picture.
- 'search_web': The user asks for real-time information, news, or weather.

Examples:
User: What's the weather today?
{"action": "search_web"}
User: Can you see what I am holding?
{"action": "take_photo"}
User: Look at this!
{"action": "take_photo"}
User: How are you?
{"action": "chat"}
"""
    response = ollama.chat(
        model='gemma3:1b',
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt}
        ],
        format='json'
    )
    return response['message']['content']

print("Test 1:", test_intent("what's the weather like today?"))
print("Test 2:", test_intent("look at me, what am I holding?"))
print("Test 3:", test_intent("describe the image"))
print("Test 4:", test_intent("hello there!"))
