# app/db.py
import os
import sqlite3
from pathlib import Path

# ✅ En Render lo correcto es usar un DISK montado en /var/data
# Si no existe (local), usa ./data/bless.db
DEFAULT_DB = "/var/data/bless.db"
FALLBACK_LOCAL = str(Path(__file__).resolve().parent.parent / "data" / "bless.db")

DB_PATH = os.getenv("DB_PATH", DEFAULT_DB)


def _safe_db_path() -> str:
    """
    Devuelve una ruta segura:
    - Si DB_PATH apunta a /var/data/bless.db y existe el directorio: úsala.
    - Si no, usa un fallback local ./data/bless.db
    """
    p = Path(DB_PATH)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    except Exception:
        p2 = Path(FALLBACK_LOCAL)
        p2.parent.mkdir(parents=True, exist_ok=True)
        return str(p2)


def get_connection():
    db_file = _safe_db_path()
    conn = sqlite3.connect(db_file, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
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

    # ✅ Usuarios
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)

    # ✅ Clientes
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

    # ✅ Pagos (y préstamos)
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

    # ✅ Migraciones seguras (sin tumbar)
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
    # placeholder de seguridad
    return
