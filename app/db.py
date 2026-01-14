# app/db.py
import os
import sqlite3
import time
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# ----------------------------
# Config
# ----------------------------
DB_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # En Render debe existir


# ----------------------------
# Helpers
# ----------------------------
def _is_postgres() -> bool:
    return bool(DATABASE_URL and DATABASE_URL.strip())


def _normalize_database_url(url: str) -> str:
    """
    Render/Neon a veces entregan:
      - postgres://  (en vez de postgresql://)
    y a veces no trae sslmode.

    psycopg acepta postgresql:// y normalmente postgres:// también,
    pero normalizamos y forzamos sslmode=require si no está.
    """
    if not url:
        return url

    url = url.strip()

    # Normaliza esquema
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # Fuerza sslmode si no existe (Render/Neon suelen requerir SSL)
    if "sslmode" not in q:
        q["sslmode"] = "require"

    new_query = urlencode(q)
    parsed = parsed._replace(query=new_query)
    return urlunparse(parsed)


def _adapt_sql_for_postgres(sql: str) -> str:
    """
    Convierte placeholders SQLite style '?' a psycopg style '%s'
    para que el mismo código (auth.py, clientes.py, etc.) no reviente.
    """
    # OJO: esto asume que '?' se usa solo como placeholder.
    # En este proyecto aplica (SELECT ... WHERE x = ?).
    return sql.replace("?", "%s")


# ----------------------------
# Cursor/Connection Proxies
# ----------------------------
class CursorProxy:
    def __init__(self, inner, use_postgres: bool):
        self._cur = inner
        self._pg = use_postgres

    def execute(self, sql, params=None):
        if self._pg and isinstance(sql, str):
            sql = _adapt_sql_for_postgres(sql)
        if params is None:
            return self._cur.execute(sql)
        return self._cur.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        if self._pg and isinstance(sql, str):
            sql = _adapt_sql_for_postgres(sql)
        return self._cur.executemany(sql, seq_of_params)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)

    def close(self):
        try:
            return self._cur.close()
        except Exception:
            return None

    @property
    def description(self):
        return getattr(self._cur, "description", None)


class ConnectionProxy:
    def __init__(self, inner, use_postgres: bool):
        self._conn = inner
        self._pg = use_postgres

    def cursor(self):
        return CursorProxy(self._conn.cursor(), self._pg)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    # Para usos directos (por si algún módulo accede atributos)
    def __getattr__(self, name):
        return getattr(self._conn, name)


# ----------------------------
# Public API
# ----------------------------
def get_connection():
    """
    Devuelve una conexión (proxy) ya lista para:
      - SQLite local (con row_factory)
      - Postgres (psycopg) en Render
    """
    if _is_postgres():
        import psycopg
        from psycopg.rows import dict_row

        url = _normalize_database_url(DATABASE_URL)
        # row_factory=dict_row => fetchone/fetchall devuelven dicts
        conn = psycopg.connect(url, row_factory=dict_row)
        return ConnectionProxy(conn, use_postgres=True)

    # SQLite local
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return ConnectionProxy(conn, use_postgres=False)


@contextmanager
def get_conn(retries: int = 10, sleep_s: float = 1.0):
    """
    Context manager robusto.
    Render a veces tarda en levantar Postgres: reintenta.
    """
    last_err = None
    for _ in range(max(1, retries)):
        try:
            conn = get_connection()
            try:
                yield conn
                return
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            last_err = e
            time.sleep(sleep_s)

    raise last_err


def init_db():
    """
    Crea tablas en SQLite o Postgres.
    Importante: incluye codigo_postal y tipo_cobro.
    """
    if _is_postgres():
        _create_tables_postgres()
    else:
        _create_tables_sqlite()


def ensure_admin(username: str, password: str):
    """
    Crea admin si no existe.
    Nota: mantiene password tal cual (sin hash) para no romper login actual.
    """
    if not username or not password:
        return

    with get_conn() as conn:
        cur = conn.cursor()

        # ¿Existe?
        cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        row = cur.fetchone()

        if row:
            return

        # Inserta admin
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            (username, password, "admin"),
        )
        conn.commit()


# ----------------------------
# SQLite schema
# ----------------------------
def _create_tables_sqlite():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT DEFAULT (datetime('now'))
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
            tipo TEXT NOT NULL DEFAULT 'pago',
            monto REAL NOT NULL DEFAULT 0,
            seguro REAL NOT NULL DEFAULT 0,
            monto_entregado REAL NOT NULL DEFAULT 0,
            interes_mensual REAL NOT NULL DEFAULT 0,
            frecuencia TEXT DEFAULT 'mensual',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
        )
        """)

        # índices útiles
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pagos_cliente_fecha ON pagos(cliente_id, fecha)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_clientes_tipo_cobro ON clientes(tipo_cobro)")

        conn.commit()


# ----------------------------
# Postgres schema
# ----------------------------
def _create_tables_postgres():
    with get_conn() as conn:
        cur = conn.cursor()

        # usuarios
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

        # clientes (mantiene codigo_postal + tipo_cobro)
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
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

        # pagos
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            fecha DATE NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'pago',
            monto NUMERIC(14,2) NOT NULL DEFAULT 0,
            seguro NUMERIC(14,2) NOT NULL DEFAULT 0,
            monto_entregado NUMERIC(14,2) NOT NULL DEFAULT 0,
            interes_mensual NUMERIC(14,2) NOT NULL DEFAULT 0,
            frecuencia TEXT DEFAULT 'mensual',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)

        # índices
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pagos_cliente_fecha ON pagos(cliente_id, fecha)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_clientes_tipo_cobro ON clientes(tipo_cobro)")

        conn.commit()
