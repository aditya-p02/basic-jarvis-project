"""
JARVIS Database v2 — Persistent Semantic Memory
- Long-term memory that survives task resets
- Semantic similarity search via embeddings
- Preference storage
- Session management
"""
import sqlite3
import sqlite_vec
import struct
import os
import threading
from datetime import datetime

try:
    from openai import OpenAI
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "jarvis_memory.db")
        
        self.db_path = db_path
        self._lock = threading.Lock()
        
        # Ollama for embeddings (local, private)
        if EMBEDDINGS_AVAILABLE:
            self.embed_client = OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama"
            )
        self.embedding_model = "nomic-embed-text"
        
        self.conn = self._init_db()
        print("[DATABASE] Persistent semantic memory online.")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            self.vec_available = True
        except Exception:
            self.vec_available = False
            print("[DATABASE] Vector search unavailable — using text search fallback.")
        
        cursor = conn.cursor()
        
        # Long-term memory (persists forever)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                agent TEXT DEFAULT 'automation',
                session_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                importance INTEGER DEFAULT 1
            )
        """)
        
        # Short-term context (wiped between sessions if needed)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS short_term_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User preferences and learned facts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            )
        """)
        
        # Task history with outcomes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                agent_used TEXT,
                execution_output TEXT,
                success INTEGER DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Vector memory table (if sqlite_vec available)
        if self.vec_available:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                    id INTEGER PRIMARY KEY,
                    embedding float[768]
                )
            """)
        
        # Create indices for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ltm_timestamp 
            ON long_term_memory(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ltm_role 
            ON long_term_memory(role)
        """)
        
        conn.commit()
        return conn

    def _serialize_f32(self, vector):
        return struct.pack(f"{len(vector)}f", *vector)

    def _get_embedding(self, text: str) -> list:
        """Get embedding vector for text. Returns None if unavailable."""
        if not EMBEDDINGS_AVAILABLE:
            return None
        try:
            response = self.embed_client.embeddings.create(
                input=[text[:2000]],  # truncate to avoid token limits
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception:
            return None

    def save_message(self, role: str, content: str, agent: str = "automation", session_id: str = None):
        """Save to BOTH long-term memory and short-term context."""
        if not content or not content.strip():
            return
        
        with self._lock:
            cursor = self.conn.cursor()
            try:
                # Save to long-term memory
                cursor.execute(
                    """INSERT INTO long_term_memory (role, content, agent, session_id) 
                       VALUES (?, ?, ?, ?)""",
                    (role, content, agent, session_id)
                )
                lt_rowid = cursor.lastrowid
                
                # Save to short-term context
                cursor.execute(
                    "INSERT INTO short_term_context (role, content) VALUES (?, ?)",
                    (role, content)
                )
                
                # Generate and store embedding
                if self.vec_available:
                    embedding = self._get_embedding(content)
                    if embedding:
                        cursor.execute(
                            "INSERT OR REPLACE INTO memory_vectors (id, embedding) VALUES (?, ?)",
                            (lt_rowid, self._serialize_f32(embedding))
                        )
                
                self.conn.commit()
            except Exception as e:
                print(f"[DATABASE ERROR] save_message: {e}")

    def save_task(self, command: str, agent: str, output: str, success: bool = True):
        """Save a completed task to task history."""
        with self._lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute(
                    """INSERT INTO task_history (command, agent_used, execution_output, success)
                       VALUES (?, ?, ?, ?)""",
                    (command, agent, output[:500], int(success))
                )
                self.conn.commit()
            except Exception as e:
                print(f"[DATABASE ERROR] save_task: {e}")

    def save_code_summary(self, code: str, agent: str = "automation"):
        """Store a short summary of generated code."""
        lines = [l.strip() for l in code.strip().splitlines() if l.strip()]
        if not lines:
            return
        summary = f"[{agent.upper()} executed {len(lines)}-line script. Action: {lines[0][:80]}]"
        self.save_message("assistant", summary, agent=agent)

    def search_relevant_memories(self, query: str, limit: int = 5) -> list:
        """
        Search long-term memory for semantically relevant past interactions.
        Falls back to keyword search if embeddings unavailable.
        """
        cursor = self.conn.cursor()
        
        # Try vector search first
        if self.vec_available:
            embedding = self._get_embedding(query)
            if embedding:
                try:
                    serialized = self._serialize_f32(embedding)
                    cursor.execute("""
                        SELECT ltm.role, ltm.content, ltm.timestamp
                        FROM memory_vectors mv
                        JOIN long_term_memory ltm ON mv.id = ltm.id
                        WHERE vec_distance_cosine(mv.embedding, ?) < 0.4
                        ORDER BY vec_distance_cosine(mv.embedding, ?) ASC
                        LIMIT ?
                    """, (serialized, serialized, limit))
                    rows = cursor.fetchall()
                    if rows:
                        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
                except Exception:
                    pass
        
        # Fallback: keyword search in long-term memory
        keywords = [w for w in query.lower().split() if len(w) > 3][:5]
        if not keywords:
            return []
        
        conditions = " OR ".join("LOWER(content) LIKE ?" for _ in keywords)
        params = [f"%{kw}%" for kw in keywords] + [limit]
        
        cursor.execute(f"""
            SELECT role, content, timestamp FROM long_term_memory
            WHERE {conditions}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params)
        
        rows = cursor.fetchall()
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]

    def get_recent_context(self, limit: int = 8) -> list:
        """Get recent conversation turns from short-term context."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT role, content FROM short_term_context ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        rows.reverse()
        return [{"role": r[0], "content": r[1]} for r in rows]

    def get_task_history(self, limit: int = 20) -> list:
        """Get recent task history for the HUD."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT command, agent_used, success, timestamp 
               FROM task_history ORDER BY timestamp DESC LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()
        return [{"command": r[0], "agent": r[1], "success": bool(r[2]), "time": r[3]} for r in rows]

    def save_user_knowledge(self, category: str, key: str, value: str):
        """Save a learned fact about the user."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_knowledge (category, key, value, timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (category, key, value))
            self.conn.commit()

    def get_user_knowledge(self, category: str = None) -> list:
        """Get learned facts about the user."""
        cursor = self.conn.cursor()
        if category:
            cursor.execute(
                "SELECT category, key, value FROM user_knowledge WHERE category = ?",
                (category,)
            )
        else:
            cursor.execute("SELECT category, key, value FROM user_knowledge")
        return [{"category": r[0], "key": r[1], "value": r[2]} for r in cursor.fetchall()]

    def get_memory_stats(self) -> dict:
        """Get memory statistics for the HUD."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM long_term_memory")
        lt_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM short_term_context")
        st_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM task_history WHERE success = 1")
        task_count = cursor.fetchone()[0]
        return {
            "long_term": lt_count,
            "short_term": st_count,
            "tasks_completed": task_count
        }

    def wipe_short_term_memory(self):
        """Wipe ONLY short-term context. Long-term memory preserved."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM short_term_context")
            self.conn.commit()
            print("[DATABASE] Short-term context cleared. Long-term memory intact.")

    def wipe_all_memory(self):
        """Nuclear option — wipe everything. Requires explicit user confirmation."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM long_term_memory")
            cursor.execute("DELETE FROM short_term_context")
            cursor.execute("DELETE FROM task_history")
            if self.vec_available:
                cursor.execute("DELETE FROM memory_vectors")
            self.conn.commit()
            print("[DATABASE] ⚠️ All memory wiped.")
