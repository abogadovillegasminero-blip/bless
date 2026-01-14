# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable

try:
    import psycopg  # psycopg v3
except Exception:
    psycopg = None


# -------------------------
# Config
# -------------------------
DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")
DATABASE_URL = os.getenv("DATABASE_URL", "") or os.getenv("POSTGRES_URL", "")


def db_kind() -> str:
    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        return "postgres"
    return "sqlite"


def _convert_placeholders(query: str) -> str:
    """
    Convierte placeholders automáticamente según el motor:
      - Si estás en Postgres y el query trae "?" -> lo convierte a "%s"
      - Si estás en SQLite y el query trae "%s" -> lo convierte a "?"
    Esto evita el error: "query has 0 placeholders but 1 parameters were passed"
    """
    kind = db_kind()
    q = query
    if kind == "postgres":
        # Convertir ? -> %s (uno a uno)
        if "?" in q:
            parts = q.split("?")
            q = "%s".join(parts)
    else:
        # sqlite: convertir %s -> ?
        if "%s" in q:
            q = q.replace("%s", "?")
    return q


def _rows_to_dicts(cursor, rows) -> list[dict]:
    cols = [d[0] for d in (cursor.description or [])]
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append(r)
        elif hasattr(r, "keys"):  # sqlite Row
            out.append(dict(r))
        else:
            out.append({cols[i]: r[i] for i in range(len(cols))})
    return out


@contextmanager
def get_conn():
    kind = db_kind()
    if kind == "sqlite":
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    else:
        if psycopg is None:
            raise RuntimeError("psycopg no está instalado pero DATABASE_URL es Postgres.")
        conn = psycopg.connect(DATABASE_URL)
        try:
            yield conn
        finally:
            conn.close()


def execute(query: str, params: Iterable[Any] | None = None) -> int:
    q = _convert_placeholders(query)
    p = list(params) if params is not None else []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        conn.commit()
        return getattr(cur, "rowcount", 0) or 0


def fetch_all(query: str, params: Iterable[Any] | None = None) -> list[dict]:
    q = _convert_placeholders(query)
    p = list(params) if params is not None else []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        rows = cur.fetchall()
        return _rows_to_dicts(cur, rows)


def fetch_one(query: str, params: Iterable[Any] | None = None) -> dict | None:
    q = _convert_placeholders(query)
    p = list(params) if params is not None else []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        row = cur.fetchone()
        if row is None:
            return None
        rows = _rows_to_dicts(cur, [row])
        return rows[0] if rows else None


# -------------------------
# Schema
# -------------------------
def _create_tables_sqlite():
    # Usuarios
    execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # Clientes
    execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        documento TEXT DEFAULT '',
        telefono TEXT DEFAULT '',
        direccion TEXT DEFAULT '',
        observaciones TEXT DEFAULT '',
        tipo_cobro TEXT DEFAULT 'mensual'
    )
    """)

    # Pagos (simple)
    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,                 -- YYYY-MM-DD (Colombia)
        valor INTEGER NOT NULL DEFAULT 0,    -- PESOS enteros
        observaciones TEXT DEFAULT '',
        creado TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    )
    """)

    # =========================
    # CONTABILIDAD (SQLite)
    # =========================
    execute("""
    CREATE TABLE IF NOT EXISTS base_dia (
        fecha TEXT PRIMARY KEY,         -- YYYY-MM-DD (Colombia)
        base_valor INTEGER NOT NULL DEFAULT 0,
        creado TEXT DEFAULT (datetime('now'))
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS gastos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,            -- YYYY-MM-DD (Colombia)
        concepto TEXT NOT NULL,
        categoria TEXT NOT NULL DEFAULT 'general',
        valor INTEGER NOT NULL DEFAULT 0,
        cobrador_username TEXT DEFAULT '',
        creado TEXT DEFAULT (datetime('now'))
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS seguros_recaudos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,            -- YYYY-MM-DD (Colombia)
        cobrador_username TEXT NOT NULL,
        valor INTEGER NOT NULL DEFAULT 0,
        creado TEXT DEFAULT (datetime('now'))
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS prestamos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,            -- YYYY-MM-DD (Colombia)
        cliente_id INTEGER,
        cobrador_username TEXT DEFAULT '',
        valor INTEGER NOT NULL DEFAULT 0,
        observaciones TEXT DEFAULT '',
        creado TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE SET NULL
    )
    """)


def _create_tables_postgres():
    # Usuarios
    execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id BIGSERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    # Clientes
    execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id BIGSERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        documento TEXT DEFAULT '',
        telefono TEXT DEFAULT '',
        direccion TEXT DEFAULT '',
        observaciones TEXT DEFAULT '',
        tipo_cobro TEXT DEFAULT 'mensual'
    )
    """)

    # Pagos
    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id BIGSERIAL PRIMARY KEY,
        cliente_id BIGINT NOT NULL,
        fecha DATE NOT NULL,
        valor BIGINT NOT NULL DEFAULT 0,
        observaciones TEXT DEFAULT '',
        creado TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    # FK pagos->clientes
    try:
        execute("""
        ALTER TABLE pagos
        ADD CONSTRAINT pagos_cliente_fk
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON DELETE CASCADE
        """)
    except Exception:
        pass

    # =========================
    # CONTABILIDAD (Postgres)
    # =========================
    execute("""
    CREATE TABLE IF NOT EXISTS base_dia (
        fecha DATE PRIMARY KEY,
        base_valor BIGINT NOT NULL DEFAULT 0,
        creado TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS gastos (
        id BIGSERIAL PRIMARY KEY,
        fecha DATE NOT NULL,
        concepto TEXT NOT NULL,
        categoria TEXT NOT NULL DEFAULT 'general',
        valor BIGINT NOT NULL DEFAULT 0,
        cobrador_username TEXT DEFAULT '',
        creado TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS seguros_recaudos (
        id BIGSERIAL PRIMARY KEY,
        fecha DATE NOT NULL,
        cobrador_username TEXT NOT NULL,
        valor BIGINT NOT NULL DEFAULT 0,
        creado TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS prestamos (
        id BIGSERIAL PRIMARY KEY,
        fecha DATE NOT NULL,
        cliente_id BIGINT NULL,
        cobrador_username TEXT DEFAULT '',
        valor BIGINT NOT NULL DEFAULT 0,
        observaciones TEXT DEFAULT '',
        creado TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    try:
        execute("""
        ALTER TABLE prestamos
        ADD CONSTRAINT prestamos_cliente_fk
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON DELETE SET NULL
        """)
    except Exception:
        pass


def init_db():
    if db_kind() == "sqlite":
        _create_tables_sqlite()
    else:
        _create_tables_postgres()


def ensure_admin(username: str, password: str):
    """
    Crea el admin si no existe.
    Nota: guarda password tal cual (como venías manejándolo).
    """
    if not username or not password:
        return

    u = fetch_one("SELECT id FROM usuarios WHERE username = ?", [username])
    if u:
        return

    execute(
        "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
        [username, password, "admin"]
    )
