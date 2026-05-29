import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_name="jarvis.db"):
        # Put the database in the root project folder
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_name)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initializes tables for conversation history and system settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Table to store chat history across sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_message(self, role, content):
        """Saves a single turn of conversation into the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (role, content) VALUES (?, ?)",
                (role, content)
            )
            conn.commit()

    def get_recent_context(self, limit=10):
        """Retrieves the last N messages formatted for the OpenAI/NVIDIA API."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Fetch the latest messages in reverse order
            cursor.execute(
                "SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            
            # Turn them back into the proper dictionary format and reverse to chronological order
            history = [{"role": row[0], "content": row[1]} for row in rows]
            return history[::-1]

    def wipe_short_term_memory(self):
        """Clears the session logs while maintaining the database file structure."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history")
            conn.commit()