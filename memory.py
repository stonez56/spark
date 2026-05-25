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
        self.collection.add(
            documents=[document_text],
            metadatas=[{"timestamp": timestamp}],
            ids=[interaction_id]
        )
        print(f"Interaction saved to memory.")

    def retrieve_context(self, current_input, n_results=3):
        """Retrieve relevant past interactions based on semantic similarity."""
        try:
            if self.collection.count() == 0:
                return ""
                
            results = self.collection.query(
                query_texts=[current_input],
                n_results=min(n_results, self.collection.count())
            )
            
            if not results['documents'] or not results['documents'][0]:
                return ""
                
            # Combine the retrieved documents into a single context string
            context = "\n".join(results['documents'][0])
            return context
        except Exception as e:
            print(f"Error retrieving memory context: {e}")
            return ""
