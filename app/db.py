# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

DB_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # Render Postgres (usa Internal Database URL)

def db_kind() -> str:
    return "postgres" if DATABASE_URL else "sqlite"

def _normalize_database_url(url: str) -> str:
    if not url:
        return url

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "sslmode" not in q:
        q["sslmode"] = "require"
    new_query = urlencode(q, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def _adapt_sql(sql: str) -> str:
    # Convierte placeholders sqlite (?) a psycopg (%s) cuando estás en Postgres
    if db_kind() == "postgres":
        return sql.replace("?", "%s")
    return sql

class CursorWrapper:
    def __init__(self, cur, kind: str):
        self._cur = cur
        self._kind = kind

    def execute(self, sql: str, params=None):
        if params is None:
            params = ()
        sql = _adapt_sql(sql)
        return self._cur.execute(sql, params)

    def executemany(self, sql: str, seq_params):
        sql = _adapt_sql(sql)
        return self._cur.executemany(sql, seq_params)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __getattr__(self, name):
        return getattr(self._cur, name)

class ConnWrapper:
    def __init__(self, conn, kind: str):
        self._conn = conn
        self._kind = kind

    def cursor(self):
        if self._kind == "postgres":
            from psycopg.rows import dict_row
            cur = self._conn.cursor(row_factory=dict_row)
            return CursorWrapper(cur, self._kind)

        cur = self._conn.cursor()
        return CursorWrapper(cur, self._kind)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)

def get_connection():
    if db_kind() == "postgres":
        import psycopg
        url = _normalize_database_url(DATABASE_URL)
        conn = psycopg.connect(url)
        return ConnWrapper(conn, "postgres")

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return ConnWrapper(conn, "sqlite")

@contextmanager
def get_conn():
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

def execute(sql: str, params=None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        return cur

def fetch_one(sql: str, params=None):
    cur = execute(sql, params)
    return cur.fetchone()

def fetch_all(sql: str, params=None):
    cur = execute(sql, params)
    return cur.fetchall()

def init_db():
    if db_kind() == "postgres":
        _create_tables_postgres()
    else:
        _create_tables_sqlite()

def _create_tables_sqlite():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            documento TEXT,
            telefono TEXT,
            direccion TEXT,
            tipo_cobro TEXT DEFAULT 'mensual',
            observaciones TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            valor REAL NOT NULL,
            observaciones TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Migración segura: agrega tipo_cobro si faltaba
        cur.execute("PRAGMA table_info(clientes)")
        cols = [r["name"] for r in cur.fetchall()]
        if "tipo_cobro" not in cols:
            cur.execute("ALTER TABLE clientes ADD COLUMN tipo_cobro TEXT DEFAULT 'mensual'")

def _create_tables_postgres():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            documento TEXT,
            telefono TEXT,
            direccion TEXT,
            tipo_cobro TEXT DEFAULT 'mensual',
            observaciones TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            fecha DATE NOT NULL,
            valor NUMERIC NOT NULL,
            observaciones TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """)

        # Migración segura por si ya existía
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tipo_cobro TEXT DEFAULT 'mensual'")

def ensure_admin(username: str, password: str):
    if not username or not password:
        return
    row = fetch_one("SELECT id FROM usuarios WHERE username = ?", (username,))
    if row:
        return
    execute(
        "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
        (username, password, "admin"),
    )
