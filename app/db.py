# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import psycopg
from psycopg.rows import dict_row


# -----------------------------
# Config
# -----------------------------
DB_PATH = os.getenv("DB_PATH", "bless.db")

# En Render pon DATABASE_URL = (Internal Database URL) de tu Postgres "bless-db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def db_kind() -> str:
    """Retorna 'postgres' si hay DATABASE_URL, si no 'sqlite'."""
    return "postgres" if DATABASE_URL else "sqlite"


def _normalize_database_url(url: str) -> str:
    """
    psycopg3 acepta postgresql:// y normalmente también postgres://, pero
    normalizamos y forzamos sslmode=require si no viene.
    """
    if not url:
        return url

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # Render suele funcionar con sslmode=require para URLs externas.
    # Para Internal URL no estorba si ya viene; si no viene, lo añadimos.
    if "sslmode" not in q:
        q["sslmode"] = "require"

    parsed = parsed._replace(query=urlencode(q))
    return urlunparse(parsed)


def _adapt_sql(sql: str) -> str:
    """
    Evita el error: "query has 0 placeholders but 1 parameters were passed"
    cuando el código manda '?' pero Postgres requiere '%s', y viceversa.
    """
    if db_kind() == "postgres":
        if "?" in sql and "%s" not in sql:
            return sql.replace("?", "%s")
        return sql
    else:
        # sqlite3 usa '?'
        if "%s" in sql and "?" not in sql:
            return sql.replace("%s", "?")
        return sql


@contextmanager
def get_conn():
    """
    Context manager de conexión. Devuelve:
    - sqlite: sqlite3.Connection (row_factory = sqlite3.Row)
    - postgres: psycopg.Connection (row_factory = dict_row)
    """
    if db_kind() == "sqlite":
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    else:
        url = _normalize_database_url(DATABASE_URL)
        conn = psycopg.connect(url, row_factory=dict_row)
        try:
            yield conn
        finally:
            conn.close()


# Compatibilidad con imports antiguos: from app.db import get_connection
def get_connection():
    """
    Devuelve una conexión ABIERTA (sin context manager).
    Preferir get_conn() salvo que sea estrictamente necesario.
    """
    if db_kind() == "sqlite":
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    url = _normalize_database_url(DATABASE_URL)
    return psycopg.connect(url, row_factory=dict_row)


def execute(sql: str, params=None) -> None:
    sql = _adapt_sql(sql)
    params = [] if params is None else params

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()


def fetch_all(sql: str, params=None):
    sql = _adapt_sql(sql)
    params = [] if params is None else params

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()

        if db_kind() == "sqlite":
            return [dict(r) for r in rows]
        # postgres ya viene como dict por dict_row
        return rows


def fetch_one(sql: str, params=None):
    sql = _adapt_sql(sql)
    params = [] if params is None else params

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()

        if row is None:
            return None
        if db_kind() == "sqlite":
            return dict(row)
        return row


# -----------------------------
# Schema / Migrations
# -----------------------------
def _ensure_sqlite_column(table: str, column: str, coltype: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]  # name está en índice 1
        if column not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
            conn.commit()


def _ensure_sqlite_tables():
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
            codigo_postal TEXT,
            observaciones TEXT,
            tipo_cobro TEXT DEFAULT 'mensual',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            valor REAL NOT NULL,
            descripcion TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        )
        """)

        conn.commit()

    # columnas que pueden faltar si vienes de versiones anteriores
    _ensure_sqlite_column("clientes", "tipo_cobro", "TEXT DEFAULT 'mensual'")
    _ensure_sqlite_column("clientes", "codigo_postal", "TEXT")
    _ensure_sqlite_column("clientes", "observaciones", "TEXT")
    _ensure_sqlite_column("clientes", "direccion", "TEXT")
    _ensure_sqlite_column("clientes", "documento", "TEXT")
    _ensure_sqlite_column("clientes", "telefono", "TEXT")


def _ensure_postgres_tables():
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
            codigo_postal TEXT,
            observaciones TEXT,
            tipo_cobro TEXT DEFAULT 'mensual',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            fecha DATE NOT NULL,
            valor NUMERIC(14,2) NOT NULL,
            descripcion TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """)

        # columnas/migraciones seguras
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tipo_cobro TEXT DEFAULT 'mensual'")
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_postal TEXT")
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS observaciones TEXT")
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS direccion TEXT")
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS documento TEXT")
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono TEXT")

        conn.commit()


def init_db():
    """
    Llamar en startup. Crea tablas y asegura columnas mínimas.
    """
    if db_kind() == "sqlite":
        _ensure_sqlite_tables()
    else:
        _ensure_postgres_tables()
