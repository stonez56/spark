import os
import sys
import shutil
import sqlite3
from unittest.mock import patch, MagicMock

# Add parent directory to path to import brain, memory, etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import OllamaBrain
from memory import MimoMemory

def run_test():
    print("="*80)
    print("🧪 啟動新竹景點與伴手禮跨回合對話歷史與搜尋詞偏置測試")
    print("="*80)

    db_path = "mimo_memory.db"
    backup_path = "mimo_memory.db.bak"
    db_exists = os.path.exists(db_path)
    
    if db_exists:
        print("[Step 1] 備份現有的 mimo_memory.db...")
        shutil.copy2(db_path, backup_path)
        # 清空測試用的 SQLite 表
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("DELETE FROM conversation_history")
        conn.commit()
        conn.close()
        print("備份完成，已重設測試數據庫。")
    else:
        print("[Step 1] mimo_memory.db 不存在，將直接建立測試資料庫。")

    try:
        # 2. 模擬第一回合對話：「新竹是有什麼好玩的地方嗎？」
        # 由於 main.py 已改為在處理鏈末端統一調用 add_interaction，我們直接調用它來模擬寫入對話歷史
        print("\n[Step 2] 模擬第一回合語音對話...寫入歷史")
        memory = MimoMemory()
        
        user_input_1 = "新竹是有什麼好玩的地方嗎？"
        mimo_response_1 = "本喵覺得新竹市有很多好去處喵，像是城隍廟、動物園都很好玩！"
        
        memory.add_interaction(user_input_1, mimo_response_1)
        print("第一回合對話已成功寫入 SQLite。")
        
        # 驗證是否成功寫入
        history = memory.get_recent_history(limit=2)
        print(f"當前 SQLite 歷史記錄: {history}")
        assert len(history) == 1, "歷史記錄筆數不正確！"
        assert "新竹" in history[0][0], "歷史記錄內容不正確！"

        # 3. 模擬第二回合語音對話：「有什麼名產可以買？」
        # 此時會觸發 search_web
        print("\n[Step 3] 模擬第二回合：「有什麼名產可以買？」觸發網頁搜尋...")
        
        brain = OllamaBrain()
        # 強制將定位偏設為 台北市士林區（以確保如果沒有上下文，它會回報士林名產）
        import settings_manager
        settings = settings_manager.load_settings()
        settings["city"] = "台北市"
        settings["district"] = "士林區"
        settings_manager.save_settings(settings)
        
        # 使用 mock 攔截 ddgs.DDGS 的 text 方法，以擷取最終傳遞給 ddgs 的搜尋詞
        captured_query = None
        
        # 由於 brain.py 中是：
        # from ddgs import DDGS
        # with DDGS() as ddgs:
        #     results = list(ddgs.text(search_target, ...))
        
        class MockDDGS:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            def text(self, query, region=None, max_results=5):
                nonlocal captured_query
                captured_query = query
                return [{"title": "新竹貢丸", "body": "新竹市名產貢丸米粉很好吃"}]

        with patch("ddgs.DDGS", MockDDGS):
            print("開始執行 search_web()...")
            response = brain.search_web("有什麼名產可以買？")
            print(f"Mimo 搜尋回應: {response}")
            
        print(f"\n🔍 捕獲的最終搜尋關鍵字: '{captured_query}'")
        
        # 驗證搜尋詞是否正確偏置 (augmented) 為包含「新竹」或「新竹市」而非「台北市士林區」
        if captured_query and "新竹" in captured_query:
            print("✅ 成功！搜尋關鍵字正確偏置為包含討論主題的『新竹』！")
        else:
            print("❌ 失敗：搜尋關鍵字未偏置至歷史主題！")
            if captured_query:
                print(f"實際搜尋詞：'{captured_query}'")
            else:
                print("未捕獲到搜尋詞")
            sys.exit(1)

    finally:
        # 4. 還原備份
        print("\n[Step 4] 還原原始 mimo_memory.db...")
        if db_exists and os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
            os.remove(backup_path)
            print("數據庫還原完成。")
        elif not db_exists and os.path.exists(db_path):
            os.remove(db_path)
            print("清理測試用數據庫文件。")
            
    print("\n" + "="*80)
    print("🎉 測試圓滿結束！所有功能驗證成功！")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_test()
