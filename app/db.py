# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# -----------------------
# Config
# -----------------------
DB_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # Render Postgres (recomendado: Internal Database URL)


# -----------------------
# Helpers URL Postgres
# -----------------------
def _normalize_database_url(url: str) -> str:
    """
    Render a veces entrega 'postgres://', psycopg prefiere 'postgresql://'.
    Además forzamos sslmode=require si no viene.
    """
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


def _using_postgres() -> bool:
    return bool(DATABASE_URL)


def _adapt_sql_for_postgres(sql: str) -> str:
    """
    Convierte placeholders SQLite (?) a placeholders psycopg (%s).
    Esto permite que el resto del proyecto siga usando '?' sin romper en Postgres.
    """
    return sql.replace("?", "%s")


# -----------------------
# Wrappers para unificar execute/cursor
# -----------------------
class CursorWrapper:
    def __init__(self, real_cursor, is_postgres: bool):
        self._cur = real_cursor
        self._is_pg = is_postgres

    def execute(self, sql: str, params=None):
        if params is None:
            params = ()

        if self._is_pg:
            sql = _adapt_sql_for_postgres(sql)

        return self._cur.execute(sql, params)

    def executemany(self, sql: str, seq_of_params):
        if self._is_pg:
            sql = _adapt_sql_for_postgres(sql)
        return self._cur.executemany(sql, seq_of_params)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return getattr(self._cur, "rowcount", None)

    def __getattr__(self, name):
        return getattr(self._cur, name)


class ConnWrapper:
    def __init__(self, real_conn, is_postgres: bool):
        self._conn = real_conn
        self._is_pg = is_postgres

    def cursor(self):
        if self._is_pg:
            # psycopg3 rows como dict para parecerse a sqlite Row (acceso por clave)
            from psycopg.rows import dict_row

            cur = self._conn.cursor(row_factory=dict_row)
            return CursorWrapper(cur, is_postgres=True)

        # SQLite
        cur = self._conn.cursor()
        return CursorWrapper(cur, is_postgres=False)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


# -----------------------
# Conexión
# -----------------------
def get_connection():
    """
    Compatibilidad con imports existentes (app.auth y otros).
    Retorna un ConnWrapper (no context manager).
    """
    if _using_postgres():
        import psycopg

        url = _normalize_database_url(DATABASE_URL)
        conn = psycopg.connect(url)
        return ConnWrapper(conn, is_postgres=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return ConnWrapper(conn, is_postgres=False)


@contextmanager
def get_conn():
    """
    Uso recomendado: with get_conn() as conn:
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


def execute(sql: str, params=None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        return cur


# -----------------------
# Migraciones / Schema
# -----------------------
def _sqlite_column_exists(conn: ConnWrapper, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r["name"] if isinstance(r, sqlite3.Row) else r.get("name") for r in cur.fetchall()]
    return column in cols


def _sqlite_table_exists(conn: ConnWrapper, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table,))
    return cur.fetchone() is not None


def _create_tables_sqlite():
    with get_conn() as conn:
        cur = conn.cursor()

        # usuarios
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
            """
        )

        # clientes
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                documento TEXT,
                telefono TEXT,
                direccion TEXT,
                codigo_postal TEXT,
                tipo_cobro TEXT DEFAULT 'mensual',
                observaciones TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )

        # pagos
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                valor REAL NOT NULL,
                observaciones TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
            )
            """
        )

        # ---- Migraciones seguras (agrega columnas si faltan) ----
        if _sqlite_table_exists(conn, "clientes"):
            if not _sqlite_column_exists(conn, "clientes", "tipo_cobro"):
                cur.execute("ALTER TABLE clientes ADD COLUMN tipo_cobro TEXT DEFAULT 'mensual'")
            if not _sqlite_column_exists(conn, "clientes", "codigo_postal"):
                cur.execute("ALTER TABLE clientes ADD COLUMN codigo_postal TEXT")

        # Nota: SQLite no permite DROP COLUMN fácil.
        # Si no quieres usar codigo_postal, se oculta desde el template, no aquí.


def _create_tables_postgres():
    with get_conn() as conn:
        cur = conn.cursor()

        # usuarios
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
            """
        )

        # clientes
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                documento TEXT,
                telefono TEXT,
                direccion TEXT,
                codigo_postal TEXT,
                tipo_cobro TEXT DEFAULT 'mensual',
                observaciones TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )

        # pagos
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pagos (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
                fecha DATE NOT NULL,
                valor NUMERIC NOT NULL,
                observaciones TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )

        # Migraciones seguras
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tipo_cobro TEXT DEFAULT 'mensual'")
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_postal TEXT")


def init_db():
    """
    Llamada en startup.
    """
    if _using_postgres():
        _create_tables_postgres()
    else:
        _create_tables_sqlite()


def ensure_admin(username: str, password: str):
    """
    Crea admin si no existe.
    """
    if not username or not password:
        return

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            return

        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            (username, password, "admin"),
        )
