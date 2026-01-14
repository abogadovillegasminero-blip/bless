# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# ----------------------------
# Config
# ----------------------------
DB_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # Render Postgres

def _normalize_database_url(url: str) -> str:
    """
    psycopg3 acepta 'postgresql://' y normalmente también 'postgres://'.
    Igual normalizamos y forzamos sslmode=require si no viene.
    """
    if not url:
        return url

    # Render a veces entrega postgres://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # Añadir sslmode=require si no viene
    parts = urlparse(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    if "sslmode" not in q:
        q["sslmode"] = "require"
    new_query = urlencode(q)
    parts = parts._replace(query=new_query)
    return urlunparse(parts)

def using_postgres() -> bool:
    return bool(DATABASE_URL)

# ----------------------------
# Connections
# ----------------------------
def _sqlite_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _postgres_conn():
    import psycopg  # psycopg v3
    url = _normalize_database_url(DATABASE_URL)
    # autocommit False para poder manejar commit/rollback
    return psycopg.connect(url)

def get_connection():
    """
    ✅ COMPATIBILIDAD: algunos módulos (auth.py) importan get_connection().
    Retorna conexión viva (sqlite3.Connection o psycopg.Connection).
    """
    if using_postgres():
        return _postgres_conn()
    return _sqlite_conn()

@contextmanager
def get_conn():
    from contextlib import contextmanager

@contextmanager
def get_connection():
    """
    Compatibilidad con código viejo (auth.py) que hace:
      from app.db import get_connection
      with get_connection() as conn:
          ...
    """
    with get_conn() as conn:
        yield conn
    """
    Context manager recomendado para el resto del código.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass

# ----------------------------
# Helpers (execute/fetch)
# ----------------------------
def execute(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur

def fetch_all(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return rows

def fetch_one(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return row

# ----------------------------
# Schema / migrations
# ----------------------------
def _sqlite_has_column(table: str, col: str) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]  # (cid, name, type, notnull, dflt_value, pk)
        return col in cols

def _sqlite_add_column_if_missing(table: str, col: str, col_def: str):
    if not _sqlite_has_column(table, col):
        execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")

def _create_tables_sqlite():
    execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        documento TEXT,
        telefono TEXT,
        direccion TEXT,
        codigo_postal TEXT,
        observaciones TEXT,
        tipo_cobro TEXT
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL,               -- 'abono' o 'prestamo'
        monto REAL NOT NULL DEFAULT 0,
        seguro REAL NOT NULL DEFAULT 0,
        monto_entregado REAL NOT NULL DEFAULT 0,
        interes_mensual REAL NOT NULL DEFAULT 20,
        frecuencia TEXT,                  -- diario/semanal/quincenal/mensual
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
    )
    """)

    # Migraciones seguras (no tumba nada)
    _sqlite_add_column_if_missing("clientes", "tipo_cobro", "TEXT")
    _sqlite_add_column_if_missing("pagos", "frecuencia", "TEXT")

def _create_tables_postgres():
    # Usuarios
    execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)

    # Clientes (mantiene codigo_postal)
    execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        documento TEXT,
        telefono TEXT,
        direccion TEXT,
        codigo_postal TEXT,
        observaciones TEXT,
        tipo_cobro TEXT
    )
    """)

    # Pagos
    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL,
        monto DOUBLE PRECISION NOT NULL DEFAULT 0,
        seguro DOUBLE PRECISION NOT NULL DEFAULT 0,
        monto_entregado DOUBLE PRECISION NOT NULL DEFAULT 0,
        interes_mensual DOUBLE PRECISION NOT NULL DEFAULT 20,
        frecuencia TEXT
    )
    """)

    # Migraciones seguras (Postgres soporta IF NOT EXISTS)
    execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tipo_cobro TEXT")
    execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS frecuencia TEXT")

def init_db():
    """
    Se llama en startup (main.py). Crea tablas y aplica migraciones.
    """
    if using_postgres():
        _create_tables_postgres()
    else:
        _create_tables_sqlite()

def ensure_admin(username: str, password: str):
    """
    Crea admin si no existe. Si existe, NO lo cambia.
    """
    if not username or not password:
        return

    row = fetch_one("SELECT id FROM usuarios WHERE username = %s" if using_postgres() else
                    "SELECT id FROM usuarios WHERE username = ?", [username])

    if row:
        return

    if using_postgres():
        execute(
            "INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)",
            [username, password, "admin"]
        )
    else:
        execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            [username, password, "admin"]
        )
