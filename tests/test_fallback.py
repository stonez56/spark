import time
import sys
import os

# Add parent directory to path to import brain
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import OllamaBrain

def run_refinement_test():
    print("="*75)
    print("🧪 啟動 Mimo 大腦：0ms 本地時間與動態字數 (LLM科普) 二合一測試")
    print("="*75)

    # 1. 初始化 OllamaBrain 實例
    print("\n[Step 1] 初始化 OllamaBrain...")
    brain = OllamaBrain()
    
    # 2. 測試 0ms 系統時間攔截器
    print("\n[Step 2] 測試本地 0ms 時間/日期攔截器...")
    time_queries = ["現在幾點", "今天星期幾", "今天幾號", "今天幾月幾號", "今天是星期几", "幾月幾日"]
    for q in time_queries:
        start_time = time.time()
        response = brain.generate_response(q)
        elapsed = time.time() - start_time
        print(f"❓ 問題: '{q}'")
        print(f"⏱️ 耗時: {elapsed*1000:.2f} 毫秒 (目標：趨近 0 毫秒！)")
        print(f"💬 Mimo 回應: {response}\n")
        
        # 驗證是否極速生成
        if elapsed < 0.1:
            print("✅ 成功！這是 100% 本地 0 毫秒極速時間攔截！")
        else:
            print("❌ 失敗：耗時過長，可能仍發送給了雲端/本地大腦模型。")
        print("-" * 50)

    # 3. 測試知識科普問答放寬字數 (什麼是LLM)
    print("\n[Step 3] 測試認真的知識型科普問答放寬字數 (解決斷句痛點)...")
    prompt = "跟我說一下什麼是LLM"
    print(f"❓ 問題: '{prompt}'")
    
    # 強制使用雲端以驗證 Gemini-2.5-flash
    brain.mode = "cloud"
    brain._init_cloud_client()
    
    start_time = time.time()
    try:
        response = brain.generate_response(prompt)
        elapsed = time.time() - start_time
        print(f"⏱️ 總花費時間: {elapsed:.2f} 秒")
        print(f"💬 Mimo 回應內容: \n{response}\n")
        
        # 驗證字數與完整性
        word_count = len(response)
        print(f"📏 回應字數: {word_count} 字")
        if word_count > 30:
            print("✅ 成功！Mimo 已經成功突破 20 字極限，給予了奴才高質量的完整解釋！")
        else:
            print("❌ 失敗：字數依然過短，請確認 length_instruction 是否生效。")
            
        if response.endswith("...") or response.endswith("就是很"):
            print("❌ 失敗：檢測到句子被截斷或斷開！")
        else:
            print("✅ 成功！句子結尾完整，沒有出現任何截斷或中途斷句！")
            
    except Exception as e:
        print(f"❌ 測試呼叫失敗: {e}")

    print("\n" + "="*75)
    print("🎉 測試圓滿結束！")
    print("="*75 + "\n")

if __name__ == "__main__":
    run_refinement_test()
