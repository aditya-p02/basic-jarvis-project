import sqlite3
import sqlite_vec
import struct
import os
from openai import OpenAI  # ollama uses the openai-compatible client
import threading

class DatabaseManager:
    def __init__(self, db_path="jarvis.db"):
        self.db_path = db_path
        
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
        self.embedding_model = "nomic-embed-text"
        
        self.conn = self._init_db()
        self._lock = threading.Lock()
        print("[DATABASE] Semantic memory online (Powered by Ollama / nomic-embed-text).")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS agent_memory USING vec0(
        id INTEGER PRIMARY KEY,
        embedding float[768]
        )
    """)
        
        conn.commit()
        return conn

    def _serialize_f32(self, vector):
        return struct.pack(f"{len(vector)}f", *vector)

    def _get_embedding(self, text):
        try:
            response = self.client.embeddings.create(
                input=[text],
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[EMBEDDING ERROR] NVIDIA API failure: {e}")
            return None

    def save_message(self, role, content):
        if not content or not content.strip():
            return
        
        with self._lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO memory_logs (role, content) VALUES (?, ?)", 
                    (role, content)
                )
                rowid = cursor.lastrowid
            
                embedding = self._get_embedding(content)
                if embedding:
                    cursor.execute(
                        "INSERT INTO agent_memory (id, embedding) VALUES (?, ?)",
                        (rowid, self._serialize_f32(embedding))
                    )
                self.conn.commit()
            except Exception as e:
                print(f"[DATABASE ERROR] {e}")

    def save_code_summary(self, code):
        """Store a short summary instead of full code for assistant turns."""
        lines = [l.strip() for l in code.strip().splitlines() if l.strip()]
        summary = f"[Executed {len(lines)}-line Python script. First action: {lines[0] if lines else 'none'}]"
        self.save_message("assistant", summary)    

    def get_recent_context(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT role, content FROM memory_logs ORDER BY timestamp DESC LIMIT ?", 
            (limit,)
        )
        rows = cursor.fetchall()
        rows.reverse()
        return [{"role": row[0], "content": row[1]} for row in rows]
        
    def wipe_short_term_memory(self):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM memory_logs")
            cursor.execute("DELETE FROM agent_memory")
            self.conn.commit()