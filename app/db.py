# app/db.py
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str):
    """
    Agrega una columna si no existe (SQLite puede no tener IF NOT EXISTS en ADD COLUMN).
    """
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    cols = [row[1] for row in cur.fetchall()]
    if column not in cols:
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}')
        conn.commit()


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

    # Tabla clientes
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

    # Tabla pagos
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

    # Migraciones seguras (NO tumban el arranque)
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
    Crea o ACTUALIZA el admin según variables de entorno.

    ✅ Si el usuario ya existe, actualiza password y fuerza role='admin'
    para que puedas entrar siempre con ADMIN_USER / ADMIN_PASS.
    """
    if not username or not password:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()

    if not row:
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
            (username, password),
        )
    else:
        cur.execute(
            "UPDATE usuarios SET password = ?, role = 'admin' WHERE username = ?",
            (password, username),
        )

    conn.commit()
    conn.close()


def migrate_excel_to_sqlite(*args, **kwargs):
    """
    Placeholder de seguridad para que Render NO se caiga si alguien lo importa.
    """
    return
