import sqlite3
import chromadb
from datetime import datetime
import uuid

class MimoMemory:
    def __init__(self, db_path="mimo_memory.db", chroma_path="./mimo_chroma_db"):
        # SQLite Setup for exact retrieval and structured logging
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                user_input TEXT,
                spark_response TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stt_context_keywords (
                keyword TEXT PRIMARY KEY,
                timestamp TEXT
            )
        ''')
        self.conn.commit()

        # ChromaDB setup for semantic retrieval
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        # We use a default embedding model 'all-MiniLM-L6-v2' provided by Chroma automatically
        self.collection = self.chroma_client.get_or_create_collection(name="mimo_conversations")

    def add_interaction(self, user_input, spark_response):
        # Generate unique ID
        interaction_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Save to SQLite
        self.cursor.execute(
            "INSERT INTO conversation_history (id, timestamp, user_input, spark_response) VALUES (?, ?, ?, ?)",
            (interaction_id, timestamp, user_input, spark_response)
        )
        self.conn.commit()

        # Save to ChromaDB (Embed the user input + response for context)
        document_text = f"User asked: {user_input} | Mimo replied: {spark_response}"
        try:
            self.collection.add(
                documents=[document_text],
                metadatas=[{"timestamp": timestamp}],
                ids=[interaction_id]
            )
        except Exception as e:
            # Self-healing: if collection does not exist, recreate it and retry!
            print(f"[Memory] Collection might be stale or missing: {e}. Re-initializing collection...")
            try:
                self.collection = self.chroma_client.get_or_create_collection(name="mimo_conversations")
                self.collection.add(
                    documents=[document_text],
                    metadatas=[{"timestamp": timestamp}],
                    ids=[interaction_id]
                )
            except Exception as ex:
                print(f"❌ [Memory] Failed to self-heal ChromaDB add: {ex}")
        print(f"Interaction saved to memory.")

    def retrieve_context(self, current_input, n_results=3):
        """Retrieve relevant past interactions based on semantic similarity."""
        try:
            # Self-healing: check if collection exists/valid
            try:
                if self.collection.count() == 0:
                    return ""
            except Exception:
                # Re-fetch collection if count() fails due to stale reference
                self.collection = self.chroma_client.get_or_create_collection(name="mimo_conversations")
                if self.collection.count() == 0:
                    return ""
                
            results = self.collection.query(
                query_texts=[current_input],
                n_results=min(n_results, self.collection.count())
            )
            
            if not results['documents'] or not results['documents'][0]:
                return ""
                
            context = "\n".join(results['documents'][0])
            return context
        except Exception as e:
            print(f"Error retrieving memory context: {e}")
            return ""

    def get_recent_history(self, limit=2):
        """Retrieve recent conversation history (user_input, spark_response) from SQLite."""
        try:
            self.cursor.execute(
                "SELECT user_input, spark_response FROM conversation_history ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving recent history: {e}")
            return []

    def save_context_keywords(self, text_list_or_str):
        """Extract valid keywords from text list or string and save them to SQLite context table."""
        if not text_list_or_str:
            return
        
        if isinstance(text_list_or_str, str):
            texts = [text_list_or_str]
        else:
            texts = text_list_or_str
            
        import re
        stop_words = {
            "這個", "那個", "什麼", "什麼是", "怎麼", "如何", "為何", "為什麼", "這樣", "那樣",
            "本喵", "主人", "奴才", "你們", "我們", "他們", "自己", "一個", "一些", "一下", "一次",
            "可以", "幫我", "需要", "不要", "不用", "可以嗎", "好嗎", "好的", "哼", "喵", "喵～",
            "的", "了", "在", "是", "我", "你", "他", "她", "它", "們", "這", "那", "都", "不", "也"
        }
        
        timestamp = datetime.now().isoformat()
        extracted = []
        for text in texts:
            if not text:
                continue
            parts = re.split(r'[^\w\u4e00-\u9fff]+', text)
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                if re.match(r'^[\u4e00-\u9fff]+$', p):
                    if 2 <= len(p) <= 8 and p not in stop_words:
                        extracted.append(p)
                        
        if not extracted:
            return
            
        try:
            for kw in extracted:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO stt_context_keywords (keyword, timestamp) VALUES (?, ?)",
                    (kw, timestamp)
                )
            self.conn.commit()
            
            self.cursor.execute(
                "DELETE FROM stt_context_keywords WHERE keyword NOT IN ("
                "SELECT keyword FROM stt_context_keywords ORDER BY timestamp DESC LIMIT 50)"
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error saving context keywords: {e}")

    def get_context_keywords(self, limit=25):
        """Retrieve the most recent STT context keywords from SQLite."""
        try:
            self.cursor.execute(
                "SELECT keyword FROM stt_context_keywords ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Error retrieving context keywords: {e}")
            return []
