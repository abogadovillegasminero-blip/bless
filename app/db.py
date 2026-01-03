import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Tabla de usuarios (incluye rol)
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
    """
    Crea el admin si no existe.
    NOTA: guarda password tal cual (sin hash) para no romper tu login actual.
    Luego, si quieres, migramos a hash con passlib sin dañar nada.
    """
    if not username or not password:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()

    if row is None:
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
            (username, password)
        )
        conn.commit()

    conn.close()
