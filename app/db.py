# app/db.py
import os
import sqlite3

from app.security import hash_password  # solo usa passlib (no hay ciclo)

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    # Para poder usar row["campo"]
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str):
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    cols = [row[1] for row in cur.fetchall()]  # row[1] = name
    if column not in cols:
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}')
        conn.commit()


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Usuarios
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)

    # Clientes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        documento TEXT,
        telefono TEXT,
        direccion TEXT,
        codigo_postal TEXT,
        observaciones TEXT
    )
    """)

    # Pagos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        fecha TEXT,
        valor REAL,
        nota TEXT,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    """)

    conn.commit()

    # Migraciones seguras (no tumbar el arranque)
    try:
        _ensure_column(conn, "clientes", "created_at", "TEXT")
    except Exception:
        pass

    try:
        _ensure_column(conn, "pagos", "created_at", "TEXT")
    except Exception:
        pass

    conn.close()


def ensure_admin(username: str, password: str):
    """
    Crea/actualiza admin desde ENV en cada startup.
    Guarda password hasheada para que SIEMPRE sirva el login.
    """
    if not username or not password:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()

    hashed = hash_password(password)

    if not row:
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
            (username, hashed),
        )
    else:
        # fuerza rol admin + actualiza password al valor de ENV
        cur.execute(
            "UPDATE usuarios SET password = ?, role = 'admin' WHERE username = ?",
            (hashed, username),
        )

    conn.commit()
    conn.close()
