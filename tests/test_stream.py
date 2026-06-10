import sys
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_APIKEY = os.getenv("OPENROUTER_APIKEY", "")

def test_stream_latency():
    if not OPENROUTER_APIKEY:
        print("Missing OPENROUTER_APIKEY")
        return

    client = OpenAI(
        api_key=OPENROUTER_APIKEY,
        base_url="https://openrouter.ai/api/v1"
    )
    
    model = "deepseek/deepseek-v4-flash"
    prompt = "寫一首簡短的詩介紹台灣的天氣，請用中文。"
    
    print(f"Testing stream latency for model: {model}")
    print(f"Sending prompt: {prompt}\n")
    
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            stream=True
        )
        
        first_token_time = None
        total_tokens = 0
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - start_time
                    print(f"⏱️ Time to First Token (TTFT): {ttft:.3f} seconds\n")
                    print("Stream Output: ", end="", flush=True)
                print(content, end="", flush=True)
                total_tokens += 1
                
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n\n✅ Stream completed.")
        print(f"⏱️ Total duration: {duration:.3f} seconds")
        print(f"📊 Total tokens received: {total_tokens}")
        print(f"⚡ Average token generation speed: {total_tokens / (end_time - first_token_time):.2f} tokens/sec")
        
    except Exception as e:
        print(f"\n❌ Error during streaming: {e}")

if __name__ == "__main__":
    test_stream_latency()
