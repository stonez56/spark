import os
import shutil
import sqlite3
import chromadb

def reset_database():
    print("🧹 [Reset DB] Starting complete memory/database reset...")
    
    # 1. Reset SQLite Conversation History (mimo_memory.db)
    try:
        conn = sqlite3.connect("mimo_memory.db")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS conversation_history")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                user_input TEXT,
                spark_response TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ [Reset DB] SQLite memory database (mimo_memory.db) reset successfully.")
    except Exception as e:
        print(f"❌ [Reset DB] Error resetting SQLite memory: {e}")
        try:
            if os.path.exists("mimo_memory.db"):
                os.remove("mimo_memory.db")
                print("🗑️ [Reset DB] SQLite memory file deleted for clean recreation.")
        except Exception as ex:
            print(f"❌ [Reset DB] Could not delete SQLite memory file: {ex}")

    # 2. Reset SQLite Reminders (reminders.db)
    try:
        conn = sqlite3.connect("reminders.db")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS reminders")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                times TEXT NOT NULL,
                days_of_week TEXT DEFAULT '0,1,2,3,4,5,6',
                start_date TEXT,
                end_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ [Reset DB] SQLite reminders database (reminders.db) reset successfully.")
    except Exception as e:
        print(f"❌ [Reset DB] Error resetting SQLite reminders: {e}")
        try:
            if os.path.exists("reminders.db"):
                os.remove("reminders.db")
                print("🗑️ [Reset DB] SQLite reminders file deleted for clean recreation.")
        except Exception as ex:
            print(f"❌ [Reset DB] Could not delete SQLite reminders file: {ex}")

    # 3. Reset ChromaDB collection
    try:
        chroma_path = "./mimo_chroma_db"
        if os.path.exists(chroma_path):
            # Try semantic deletion using PersistentClient first
            try:
                chroma_client = chromadb.PersistentClient(path=chroma_path)
                try:
                    chroma_client.delete_collection("mimo_conversations")
                    print("✅ [Reset DB] ChromaDB collection 'mimo_conversations' deleted.")
                except Exception:
                    pass
                chroma_client.get_or_create_collection("mimo_conversations")
                print("✅ [Reset DB] ChromaDB semantic memory reset successfully.")
            except Exception as e:
                print(f"⚠️ [Reset DB] Native ChromaDB reset failed: {e}. Falling back to directory removal.")
                shutil.rmtree(chroma_path, ignore_errors=True)
                print("🗑️ [Reset DB] ChromaDB directory removed.")
        else:
            print("ℹ️ [Reset DB] ChromaDB directory not found. No reset needed.")
    except Exception as e:
        print(f"❌ [Reset DB] Error resetting ChromaDB: {e}")

    # 4. Reset Personalization Settings (settings.json) to defaults
    try:
        import settings_manager
        default_settings = {
            "patient_name": "主人",
            "caregiver_name": "Mimo",
            "speaking_speed": "normal",
            "routing_mode": "local"
        }
        settings_manager.save_settings(default_settings)
        print("✅ [Reset DB] Personalization settings (settings.json) reset to default clean values.")
    except Exception as e:
        print(f"❌ [Reset DB] Error resetting personalization settings: {e}")

    # 5. Clear Audio Cache directory (guarantees complete clean name regeneration)
    try:
        cache_dir = "./audio_cache_data"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
            print("🗑️ [Reset DB] Audio cache directory cleared for clean fresh regeneration.")
    except Exception as e:
        print(f"❌ [Reset DB] Error clearing audio cache: {e}")

    print("🎉 [Reset DB] Database and memory reset completed!")

if __name__ == "__main__":
    reset_database()
