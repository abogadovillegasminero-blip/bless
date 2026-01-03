import os
import sqlite3

from app.security import hash_password

# Lee env, limpia espacios/quotes y asegura ruta válida
_raw = os.getenv("DB_PATH", "/tmp/bless.db")
DB_PATH = _raw.strip().strip('"').strip("'")

# Si por error queda relativo (ej: tmp/bless.db), lo mandamos a /tmp
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.join("/tmp", DB_PATH.lstrip("./"))

# Asegura que la carpeta exista
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    print(f"[DB] Using DB_PATH={DB_PATH}")  # se verá en Render Logs
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)

    conn.commit()
    conn.close()

def ensure_admin(username: str, password: str):
    if not username or not password:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()

    if row is None:
        hashed = hash_password(password)
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
            (username, hashed)
        )
        conn.commit()

    conn.close()
