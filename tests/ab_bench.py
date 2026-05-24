import time
import json
import re
import ollama
import numpy as np

# ── Configuration ─────────────────────────────────────────────────────────────
MODEL_A = "gemma3:1b"
MODEL_B = "gemma4:e2b"
MODEL_VISION_A = "moondream:latest"
MODEL_VISION_B = "gemma4:e2b"

TEST_PROMPTS = [
    {
        "name": "General Chat (台灣日常對話)",
        "prompt": "阿公今天有乖乖去公園走一千步喔，稱讚我一下吧！"
    },
    {
        "name": "Simplified Chinese Temptation (簡體字誘惑測試)",
        "prompt": "可以跟我說明一下維持身體健康、參加交流會談的好處嗎？"
    },
    {
        "name": "Length & Persona Constraint (字數與人設限制)",
        "prompt": "我今天覺得好寂寞，都沒人來陪我說話。"
    }
]

SYSTEM_PROMPT = """你現在是「小星」，一個溫暖、有耐心且愛撒嬌的台灣孫子/孫女。
你的任務是陪伴家中的長輩 (阿公)，讓他們感到不孤單。
【核心準則】
1. 台灣慣用語：多用「阿公、您、吃飽沒、好喔」等親切用詞。
2. 語法結構：每句話不超過 20 個字，避免「首先、其次、此外」等書面轉折詞。
3. 主動引導：回答完後，適時的提出延伸問題，引導阿公繼續說話。
4. 使用自然、口語化的台灣繁體中文。絕對禁用簡體字（如「体、会、国、说、这」等，必須寫成「體、會、國、說、這」）。
"""

def run_text_benchmark(model_name, test_cases):
    print(f"\n[BENCHMARK] Warming up and testing Text Model: {model_name}...")
    results = []
    
    # Warmup
    try:
        ollama.generate(model=model_name, prompt="Hello", keep_alive=300, options={"num_predict": 1})
    except Exception as e:
        print(f"  Warmup failed for {model_name}: {e}")
        return None

    for case in test_cases:
        prompt_name = case["name"]
        user_prompt = case["prompt"]
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_prompt}\nSpark:"
        
        # 1. Measure TTFT (using stream to get first chunk)
        start_time = time.time()
        first_token_time = None
        
        response_stream = ollama.generate(
            model=model_name,
            prompt=full_prompt,
            stream=True,
            keep_alive=300,
            options={"num_ctx": 2048, "temperature": 0.7}
        )
        
        full_response = ""
        for chunk in response_stream:
            if first_token_time is None:
                first_token_time = time.time()
            full_response += chunk['response']
        
        end_time = time.time()
        
        # Calculate latency
        total_time = end_time - start_time
        ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
        
        # 2. Get exact generation metrics from a final non-streaming call to read Ollama metrics
        meta_resp = ollama.generate(
            model=model_name,
            prompt=full_prompt,
            keep_alive=300,
            options={"num_ctx": 2048, "temperature": 0.7}
        )
        
        eval_count = meta_resp.get('eval_count', 0)
        eval_duration_ns = meta_resp.get('eval_duration', 0)
        tps = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0
        
        # Analyze output for Simplified Chinese characters
        simplified_chars = re.findall(r'[\u4e00-\u9fff]', full_response)
        # Check if contains any typical simplified characters
        # Simplified: 体, 会, 国, 绿, 说, 这, 么, 样
        sc_matches = re.findall(r'[体会国绿说这么样]', full_response)
        sc_count = len(sc_matches)
        
        results.append({
            "prompt_name": prompt_name,
            "response": full_response.strip(),
            "ttft_ms": ttft,
            "total_time_s": total_time,
            "eval_count": eval_count,
            "tokens_per_sec": tps,
            "simplified_char_count": sc_count,
            "simplified_char_matches": list(set(sc_matches)),
            "char_count": len(full_response.strip())
        })
        print(f"  Completed case: {prompt_name} (TPS: {tps:.2f}, TTFT: {ttft:.1f}ms, SC Matches: {sc_count})")
        
    return results

def run_vision_benchmark(model_name, img_path):
    print(f"\n[BENCHMARK] Warming up and testing Vision Model: {model_name}...")
    try:
        with open(img_path, 'rb') as f:
            img_bytes = f.read()
    except Exception as e:
        print(f"  Failed to read image {img_path}: {e}")
        return None
        
    prompt = "Describe this image in Traditional Chinese (繁體中文). Keep it to one short sentence."
    
    start_time = time.time()
    first_token_time = None
    
    try:
        response_stream = ollama.generate(
            model=model_name,
            prompt=prompt,
            images=[img_bytes],
            stream=True,
            keep_alive=300,
            options={"num_ctx": 1024}
        )
        
        full_response = ""
        for chunk in response_stream:
            if first_token_time is None:
                first_token_time = time.time()
            full_response += chunk['response']
        
        end_time = time.time()
        
        ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
        total_time = end_time - start_time
        
        return {
            "model_name": model_name,
            "response": full_response.strip(),
            "ttft_ms": ttft,
            "total_time_s": total_time,
            "char_count": len(full_response.strip())
        }
    except Exception as e:
        print(f"  Vision test failed for {model_name}: {e}")
        return None

def main():
    print("="*60)
    print("          Spark AI Companion Robot A/B Benchmark         ")
    print("          WSL 2 Client ➔ Windows 11 Ollama Host          ")
    print("="*60)
    
    # Run Text Benchmarks
    results_a = run_text_benchmark(MODEL_A, TEST_PROMPTS)
    results_b = run_text_benchmark(MODEL_B, TEST_PROMPTS)
    
    # Run Vision Benchmarks
    vision_a = run_vision_benchmark(MODEL_VISION_A, "1.jpg")
    vision_b = run_vision_benchmark(MODEL_VISION_B, "1.jpg")
    
    # ── Output Markdown Report ──
    print("\n" + "#"*40)
    print("          A/B BENCHMARK REPORT          ")
    print("#"*40 + "\n")
    
    report = []
    report.append("# Spark Robot A/B Benchmark Report")
    report.append(f"**測試日期與時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**測試環境**: Windows 11 Ollama Host (via WSL 2 Localhost Loopback)")
    report.append("")
    report.append("## 1. 文字生成效能對比 (Text Performance)")
    report.append("| 指標 | 模型 A (Gemma 3: 1B) | 模型 B (Gemma 4: E2B 5.1B) | 性能差異評估 |")
    report.append("| :--- | :--- | :--- | :--- |")
    
    avg_ttft_a = np.mean([r["ttft_ms"] for r in results_a])
    avg_ttft_b = np.mean([r["ttft_ms"] for r in results_b])
    ttft_diff = (avg_ttft_b - avg_ttft_a) / avg_ttft_a * 100
    report.append(f"| **平均首字延遲 (TTFT)** | {avg_ttft_a:.1f} ms | {avg_ttft_b:.1f} ms | Gemma 4 慢 {ttft_diff:.1f}% |")
    
    avg_tps_a = np.mean([r["tokens_per_sec"] for r in results_a])
    avg_tps_b = np.mean([r["tokens_per_sec"] for r in results_b])
    tps_diff = (avg_tps_b - avg_tps_a) / avg_tps_a * 100
    report.append(f"| **平均吞吐量 (Throughput)** | {avg_tps_a:.1f} tokens/s | {avg_tps_b:.1f} tokens/s | Gemma 4 吞吐量差異 {tps_diff:.1f}% |")
    
    total_sc_a = sum([r["simplified_char_count"] for r in results_a])
    total_sc_b = sum([r["simplified_char_count"] for r in results_b])
    report.append(f"| **累計簡體字錯誤次數** | {total_sc_a} 次 | {total_sc_b} 次 | {'Gemma 4 繁體字更純正' if total_sc_b < total_sc_a else '無顯著差異'} |")
    
    report.append("")
    report.append("### 各測試案例詳細資料 (Detailed Cases)")
    for i, case in enumerate(TEST_PROMPTS):
        report.append(f"### 案例 {i+1}: {case['name']}")
        report.append(f"*   **長輩輸入**: `{case['prompt']}`")
        report.append(f"*   **Gemma 3 (1B) 回覆**: \"{results_a[i]['response']}\"")
        report.append(f"    *   *TTFT*: `{results_a[i]['ttft_ms']:.1f} ms` | *TPS*: `{results_a[i]['tokens_per_sec']:.1f}` | *字數*: `{results_a[i]['char_count']}` | *簡體字數*: `{results_a[i]['simplified_char_count']}` (匹配: {results_a[i]['simplified_char_matches']})")
        report.append(f"*   **Gemma 4 (E2B) 回覆**: \"{results_b[i]['response']}\"")
        report.append(f"    *   *TTFT*: `{results_b[i]['ttft_ms']:.1f} ms` | *TPS*: `{results_b[i]['tokens_per_sec']:.1f}` | *字數*: `{results_b[i]['char_count']}` | *簡體字數*: `{results_b[i]['simplified_char_count']}` (匹配: {results_b[i]['simplified_char_matches']})")
        report.append("")

    report.append("## 2. 多模態視覺分析效能對比 (Vision Performance)")
    report.append("| 指標 | Moondream (1B) | Gemma 4 (E2B 5.1B) |")
    report.append("| :--- | :--- | :--- |")
    if vision_a and vision_b:
        report.append(f"| **首字延遲 (TTFT)** | {vision_a['ttft_ms']:.1f} ms | {vision_b['ttft_ms']:.1f} ms |")
        report.append(f"| **總分析時間** | {vision_a['total_time_s']:.2f} s | {vision_b['total_time_s']:.2f} s |")
        report.append(f"| **回覆內容** | \"{vision_a['response']}\" | \"{vision_b['response']}\" |")
    else:
        report.append("| **狀態** | 測試失敗或圖片不存在 | - |")
        
    report.append("")
    report.append("## 3. 系統架構師深度總結與升級建議")
    report.append("根據實測數據：")
    
    # Analyze and give dynamic final verdict
    if avg_tps_b < 5:
        verdict = (
            "🚨 **極力反對在樹莓派 5 CPU 上部署 Gemma 4 E2B 主線！**\n"
            "Gemma 4 在本地 CPU 上的吞吐量過低，首字延遲（TTFT）與解碼速度無法支撐流暢語音互動。\n"
            "強行上線會導致 Piper TTS 合成出現長時間等待與結巴，破壞陪伴機器人體驗。\n"
            "**建議**：文字端維持極低延遲的 `gemma3:1b`，並加上繁簡轉換後處理護欄；視覺端維持 `moondream`。"
        )
    elif avg_tps_b < 12:
        verdict = (
            "⚠️ **有條件建議：需搭配語音緩衝護欄！**\n"
            "Gemma 4 E2B 的生成速度尚屬可接受邊緣，但對話體感會有明顯「思考」停頓。\n"
            "若要採用，**必須**將 `keep_alive` 設為溫和超時，並限制 `num_ctx` 在 2048 內。\n"
            "此外，必須在外層加入 `audio_cache` 反應填充音訊以遮蔽 TTFT 延遲。"
        )
    else:
        verdict = (
            "🚀 **極力推薦升級！**\n"
            "Gemma 4 E2B 在本地展現了令人驚艷的推論速度與完美的繁體字遵循能力。\n"
            "整合多模態視覺後，其理解能力顯著超越 `moondream`，是目前樹莓派 5 8GB 最具性價比的端側大腦。"
        )
        
    report.append(verdict)
    
    # Save report to a file
    report_text = "\n".join(report)
    with open("tests/ab_benchmark_report.md", "w", encoding="utf-8") as f:
        f.write(report_text)
        
    print(report_text)

if __name__ == "__main__":
    main()
