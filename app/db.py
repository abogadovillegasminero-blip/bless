# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable, Optional

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")

# En Render usa DATABASE_URL (idealmente el "Internal Database URL")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def db_kind() -> str:
    if DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")):
        return "postgres"
    return "sqlite"


def _adapt_sql(sql: str) -> str:
    """
    Unifica placeholders entre SQLite (?) y Postgres (%s).
    Si llega un query con '?' y estamos en Postgres, lo convertimos a %s.
    Si llega un query con '%s' y estamos en SQLite, lo convertimos a ?.
    """
    kind = db_kind()
    if kind == "postgres":
        # Convertir placeholders de sqlite a postgres
        if "?" in sql:
            return sql.replace("?", "%s")
        return sql
    else:
        # Convertir placeholders de postgres a sqlite
        if "%s" in sql:
            return sql.replace("%s", "?")
        return sql


def _normalize_params(params: Optional[Iterable[Any]]) -> list[Any]:
    if params is None:
        return []
    if isinstance(params, (list, tuple)):
        return list(params)
    return [params]


def _placeholders_count(sql: str) -> int:
    # Conteo simple: sirve para prevenir el error "0 placeholders but 1 params"
    return sql.count("?") + sql.count("%s")


@contextmanager
def get_conn():
    """
    Context manager que SIEMPRE 'yield' una conexión válida.
    """
    if db_kind() == "postgres":
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            # Habilitar FKs en SQLite
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
        finally:
            conn.close()


def execute(sql: str, params: Optional[Iterable[Any]] = None) -> None:
    sql2 = _adapt_sql(sql)
    p = _normalize_params(params)

    # Evita el error: query has 0 placeholders but 1 parameters were passed
    if p and _placeholders_count(sql2) == 0:
        # si el SQL no tiene placeholders, ignora params en vez de reventar
        p = []

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql2, p)
        # En sqlite hace falta commit; en psycopg también, a menos que sea autocommit.
        try:
            conn.commit()
        except Exception:
            pass


def fetch_one(sql: str, params: Optional[Iterable[Any]] = None) -> Optional[dict]:
    sql2 = _adapt_sql(sql)
    p = _normalize_params(params)

    if p and _placeholders_count(sql2) == 0:
        p = []

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql2, p)
        row = cur.fetchone()
        if row is None:
            return None
        # sqlite Row -> dict
        if hasattr(row, "keys"):
            return dict(row)
        return row  # psycopg dict_row ya es dict-like


def fetch_all(sql: str, params: Optional[Iterable[Any]] = None) -> list[dict]:
    sql2 = _adapt_sql(sql)
    p = _normalize_params(params)

    if p and _placeholders_count(sql2) == 0:
        p = []

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql2, p)
        rows = cur.fetchall() or []
        out: list[dict] = []
        for r in rows:
            if r is None:
                continue
            if hasattr(r, "keys"):
                out.append(dict(r))
            else:
                out.append(r)
        return out


# Alias por compatibilidad si algún módulo usa nombres viejos
fetchall = fetch_all
fetchone = fetch_one


def init_db() -> None:
    """
    Crea esquema mínimo para Bless (usuarios, clientes, pagos).
    Compatible SQLite/Postgres.
    """
    if db_kind() == "postgres":
        _create_tables_postgres()
    else:
        _create_tables_sqlite()


def _create_tables_sqlite() -> None:
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
        tipo_cobro TEXT NOT NULL DEFAULT 'mensual',
        creado TEXT DEFAULT (datetime('now'))
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha TEXT DEFAULT (date('now')),
        valor REAL NOT NULL DEFAULT 0,
        observaciones TEXT,
        creado TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    )
    """)


def _create_tables_postgres() -> None:
    execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id BIGSERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id BIGSERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        documento TEXT,
        telefono TEXT,
        direccion TEXT,
        codigo_postal TEXT,
        observaciones TEXT,
        tipo_cobro TEXT NOT NULL DEFAULT 'mensual',
        creado TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id BIGSERIAL PRIMARY KEY,
        cliente_id BIGINT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
        fecha DATE DEFAULT CURRENT_DATE,
        valor NUMERIC(12,2) NOT NULL DEFAULT 0,
        observaciones TEXT,
        creado TIMESTAMPTZ DEFAULT NOW()
    )
    """)


def ensure_admin(username: str, password: str) -> None:
    """
    Crea el admin si no existe.
    NOTA: guarda password tal cual (sin hash) para NO romper tu login actual.
    """
    if not username or not password:
        return

    row = fetch_one("SELECT id FROM usuarios WHERE username = ?", [username])
    if row:
        return

    execute(
        "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
        [username, password, "admin"]
    )
