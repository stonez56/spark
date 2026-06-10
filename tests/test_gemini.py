import sys
import os
import time

# Add parent directory to path to import brain
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import OllamaBrain
import settings_manager

def test_gemini():
    print("="*60)
    print("🧪 啟動 Gemini 雲端模型與思考參數對接測試")
    print("="*60)

    # Initialize OllamaBrain
    brain = OllamaBrain()
    brain.mode = "cloud"
    
    # Save settings to simulate user choices
    settings = settings_manager.load_settings()
    
    models_to_test = [
        "google/gemini-2.5-flash-lite", 
        "google/gemini-2.5-flash", 
        "gemini-2.5-flash-lite", 
        "gemini-2.5-flash", 
        "gemini-3.5-flash"
    ]
    test_query = "為什麼天空是藍色的？請用 20 字以內極簡回答。"
    
    for model in models_to_test:
        print(f"\n--- 測試模型: {model} ---")
        settings["cloud_text_model"] = model
        
        # Test 1: With reasoning enabled
        print("[測試 1] 啟用推理模式 (use_reasoning=True)")
        settings["cloud_use_reasoning"] = True
        settings_manager.save_settings(settings)
        brain.reload_settings()
        
        start = time.time()
        try:
            res = brain.generate_response(test_query)
            elapsed = time.time() - start
            print(f"⏱️ 耗時: {elapsed:.2f} 秒")
            print(f"💬 回應: {res}")
        except Exception as e:
            print(f"❌ 發生錯誤: {e}")
            
        # Test 2: With reasoning disabled
        print("[測試 2] 關閉推理模式 (use_reasoning=False)")
        settings["cloud_use_reasoning"] = False
        settings_manager.save_settings(settings)
        brain.reload_settings()
        
        start = time.time()
        try:
            res = brain.generate_response(test_query)
            elapsed = time.time() - start
            print(f"⏱️ 耗時: {elapsed:.2f} 秒")
            print(f"💬 回應: {res}")
        except Exception as e:
            print(f"❌ 發生錯誤: {e}")
            
    print("\n" + "="*60)
    print("🎉 Gemini 對接測試結束")
    print("="*60)

if __name__ == "__main__":
    test_gemini()
