# app/db.py
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()

def db_kind() -> str:
    return "postgres" if DATABASE_URL else "sqlite"

def _pg_url() -> str:
    url = DATABASE_URL
    if not url:
        return ""
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

@contextmanager
def get_conn():
    if db_kind() == "sqlite":
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    else:
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(_pg_url(), row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

def execute(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)

def fetch_all(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def fetch_one(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

# --------------------------
# init + migrations
# --------------------------

def _sqlite_has_column(table: str, col: str) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        return col in cols

def _sqlite_add_column(table: str, coldef: str):
    execute(f"ALTER TABLE {table} ADD COLUMN {coldef}")

def _postgres_add_column_if_missing(table: str, col: str, coltype: str, default_sql: str = ""):
    d = f" DEFAULT {default_sql}" if default_sql else ""
    execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {coltype}{d}")

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
        tipo_cobro TEXT DEFAULT 'mensual'
    )
    """)
    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL,                 -- abono | prestamo
        monto REAL DEFAULT 0,               -- abono
        seguro REAL DEFAULT 0,
        monto_entregado REAL DEFAULT 0,     -- prestamo
        interes_mensual REAL DEFAULT 20,    -- prestamo
        frecuencia TEXT DEFAULT 'mensual',  -- prestamo
        FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    )
    """)
    execute("CREATE INDEX IF NOT EXISTS idx_pagos_cliente_id ON pagos(cliente_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha)")

def _create_tables_postgres():
    execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)
    execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        documento TEXT,
        telefono TEXT,
        direccion TEXT,
        codigo_postal TEXT,
        observaciones TEXT,
        tipo_cobro TEXT DEFAULT 'mensual'
    )
    """)
    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL,
        monto DOUBLE PRECISION DEFAULT 0,
        seguro DOUBLE PRECISION DEFAULT 0,
        monto_entregado DOUBLE PRECISION DEFAULT 0,
        interes_mensual DOUBLE PRECISION DEFAULT 20,
        frecuencia TEXT DEFAULT 'mensual'
    )
    """)
    execute("CREATE INDEX IF NOT EXISTS idx_pagos_cliente_id ON pagos(cliente_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha)")

def _migrate_sqlite():
    # NO eliminar codigo_postal. Solo asegurar columnas.
    if not _sqlite_has_column("clientes", "codigo_postal"):
        _sqlite_add_column("clientes", "codigo_postal TEXT")
    if not _sqlite_has_column("clientes", "tipo_cobro"):
        _sqlite_add_column("clientes", "tipo_cobro TEXT DEFAULT 'mensual'")
    if not _sqlite_has_column("pagos", "frecuencia"):
        _sqlite_add_column("pagos", "frecuencia TEXT DEFAULT 'mensual'")

def _migrate_postgres():
    _postgres_add_column_if_missing("clientes", "codigo_postal", "TEXT")
    _postgres_add_column_if_missing("clientes", "tipo_cobro", "TEXT", "'mensual'")
    _postgres_add_column_if_missing("pagos", "frecuencia", "TEXT", "'mensual'")

def init_db():
    if db_kind() == "sqlite":
        _create_tables_sqlite()
        _migrate_sqlite()
    else:
        _create_tables_postgres()
        _migrate_postgres()

def ensure_admin(username: str, password: str):
    if not username or not password:
        return
    if db_kind() == "sqlite":
        u = fetch_one("SELECT id FROM usuarios WHERE username = ?", [username])
        if u:
            return
        execute("INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)", [username, password, "admin"])
    else:
        u = fetch_one("SELECT id FROM usuarios WHERE username = %s", [username])
        if u:
            return
        execute("INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)", [username, password, "admin"])
