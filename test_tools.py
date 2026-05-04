import ollama

def web_search(query: str):
    """Searches the web for the given query"""
    return f"Search results for {query}"

def analyze_image(prompt: str):
    """Takes a photo and analyzes it using the vision model"""
    return "Image analyzed"

response = ollama.chat(
    model='gemma3:1b',
    messages=[{'role': 'user', 'content': 'Can you take a photo of me and tell me what I look like?'}],
    tools=[web_search, analyze_image]
)

print(response.get('message', {}).get('tool_calls'))
