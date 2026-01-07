# app/db.py
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")


def get_connection():
    # ✅ asegura carpeta si DB_PATH está en /var/data/...
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row  # ✅ para usar row["id"]
    # ajustes sanos
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str):
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    cols = [row[1] for row in cur.fetchall()]
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
        observaciones TEXT,
        created_at TEXT
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
        tipo TEXT,
        seguro REAL,
        monto_entregado REAL,
        interes_mensual REAL,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    """)

    conn.commit()

    # Migraciones suaves por si ya existían tablas viejas
    try:
        _ensure_column(conn, "clientes", "created_at", "TEXT")
        _ensure_column(conn, "pagos", "tipo", "TEXT")
        _ensure_column(conn, "pagos", "seguro", "REAL")
        _ensure_column(conn, "pagos", "monto_entregado", "REAL")
        _ensure_column(conn, "pagos", "interes_mensual", "REAL")
    except Exception:
        pass

    conn.close()


def ensure_admin(username: str, password: str):
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
        conn.commit()

    conn.close()


def migrate_excel_to_sqlite(*args, **kwargs):
    return
