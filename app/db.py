# app/db.py
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str):
    """
    Agrega una columna si no existe (SQLite no tiene IF NOT EXISTS en ADD COLUMN en versiones viejas).
    """
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    cols = [row[1] for row in cur.fetchall()]  # row[1] = name
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

    # ✅ Migración segura: si tu código guarda created_at, la tabla debe tenerla
    try:
        _ensure_column(conn, "clientes", "created_at", "TEXT")
    except Exception:
        # Si por algún motivo falla, NO tumbes el arranque.
        pass

    conn.close()


def ensure_admin(username: str, password: str):
    """
    Crea el admin si no existe.
    NOTA: guarda password tal cual (sin hash) para no romper tu login actual.
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
            (username, password)
        )
        conn.commit()

    conn.close()


def migrate_excel_to_sqlite(*args, **kwargs):
    """
    ✅ Placeholder de seguridad para que Render NO se caiga si alguien lo importa.
    Hoy no es necesario para correr Bless.
    """
    return
