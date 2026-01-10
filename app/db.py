# app/db.py
import os
import sqlite3
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = os.getenv("DB_PATH", "bless.db")

_DB_KIND = "postgres" if DATABASE_URL else "sqlite"
_DB_INITIALIZED = False


def db_kind() -> str:
    return _DB_KIND


def _sqlite_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Activar FK en SQLite (para cascadas si existen)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _postgres_conn():
    """
    Python 3.13 en Render: usar psycopg (v3).
    Dejamos fallback a psycopg2 por compatibilidad local si alguien usa Py viejo.
    """
    dsn = DATABASE_URL
    if "sslmode=" not in dsn:
        sep = "&" if "?" in dsn else "?"
        dsn = f"{dsn}{sep}sslmode=require"

    # 1) Preferido: psycopg (v3)
    try:
        import psycopg
        from psycopg.rows import dict_row

        # row_factory=dict_row => fetchall devuelve dicts
        conn = psycopg.connect(dsn, row_factory=dict_row)
        return conn
    except ImportError:
        pass

    # 2) Fallback: psycopg2 (si está instalado y el Python lo soporta)
    import psycopg2
    from psycopg2.extras import RealDictCursor

    return psycopg2.connect(dsn, cursor_factory=RealDictCursor)


@contextmanager
def get_conn():
    if _DB_KIND == "sqlite":
        conn = _sqlite_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = _postgres_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def fetch_all(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_one(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql: str, params=None) -> int:
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        # psycopg3: rowcount existe; sqlite también
        return getattr(cur, "rowcount", 0) or 0


# --------------------------
# Schema helpers
# --------------------------

def _sqlite_table_columns(table: str) -> set[str]:
    rows = fetch_all(f"PRAGMA table_info({table})")
    return {r["name"] for r in rows}


def _postgres_table_columns(table: str) -> set[str]:
    sql = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name=%s
    """
    rows = fetch_all(sql, [table])
    cols = set()
    for r in rows:
        if isinstance(r, dict):
            cols.add(r["column_name"])
        else:
            cols.add(r[0])
    return cols


def table_columns(table: str) -> set[str]:
    if _DB_KIND == "sqlite":
        return _sqlite_table_columns(table)
    return _postgres_table_columns(table)


def _add_column_if_missing(table: str, column: str, col_type: str, default_sql: str | None = None):
    cols = table_columns(table)
    if column in cols:
        return

    if _DB_KIND == "sqlite":
        if default_sql:
            execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default_sql}")
        else:
            execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    else:
        if default_sql:
            execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type} DEFAULT {default_sql}")
        else:
            execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}")


# --------------------------
# Create tables
# --------------------------

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
        observaciones TEXT,
        tipo_cobro TEXT DEFAULT 'mensual'
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL, -- 'abono' o 'prestamo'
        monto REAL DEFAULT 0,
        seguro REAL DEFAULT 0,
        monto_entregado REAL DEFAULT 0,
        interes_mensual REAL DEFAULT 20,
        frecuencia TEXT DEFAULT 'mensual',
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
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
        observaciones TEXT,
        tipo_cobro TEXT DEFAULT 'mensual'
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL, -- 'abono' o 'prestamo'
        monto DOUBLE PRECISION DEFAULT 0,
        seguro DOUBLE PRECISION DEFAULT 0,
        monto_entregado DOUBLE PRECISION DEFAULT 0,
        interes_mensual DOUBLE PRECISION DEFAULT 20,
        frecuencia TEXT DEFAULT 'mensual'
    )
    """)

    execute("CREATE INDEX IF NOT EXISTS idx_pagos_cliente_id ON pagos(cliente_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha)")


# --------------------------
# Data migrations
# --------------------------

def _backfill_documento_from_cedula():
    cols = table_columns("clientes")
    if "cedula" not in cols:
        return

    if "documento" not in cols:
        _add_column_if_missing("clientes", "documento", "TEXT")

    if _DB_KIND == "sqlite":
        execute("""
        UPDATE clientes
        SET documento = COALESCE(documento, cedula)
        WHERE (documento IS NULL OR TRIM(documento) = '')
          AND cedula IS NOT NULL AND TRIM(cedula) <> ''
        """)
    else:
        execute("""
        UPDATE clientes
        SET documento = COALESCE(documento, cedula)
        WHERE (documento IS NULL OR BTRIM(documento) = '')
          AND cedula IS NOT NULL AND BTRIM(cedula) <> ''
        """)


def _backfill_frecuencia_default():
    cols = table_columns("pagos")
    if "frecuencia" not in cols:
        return

    if _DB_KIND == "sqlite":
        execute("""
        UPDATE pagos
        SET frecuencia = 'mensual'
        WHERE frecuencia IS NULL OR TRIM(frecuencia) = ''
        """)
    else:
        execute("""
        UPDATE pagos
        SET frecuencia = 'mensual'
        WHERE frecuencia IS NULL OR BTRIM(frecuencia) = ''
        """)


def _ensure_role_column_usuarios():
    cols = table_columns("usuarios")
    if "role" not in cols:
        _add_column_if_missing("usuarios", "role", "TEXT", "'user'")


def init_db():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return

    # 1) Base tables
    if _DB_KIND == "sqlite":
        _create_tables_sqlite()
    else:
        _create_tables_postgres()

    # 2) Safe migrations
    _add_column_if_missing("clientes", "tipo_cobro", "TEXT", "'mensual'")
    _add_column_if_missing("pagos", "frecuencia", "TEXT", "'mensual'")
    _add_column_if_missing("clientes", "documento", "TEXT")

    _ensure_role_column_usuarios()

    # 3) Backfills
    _backfill_documento_from_cedula()
    _backfill_frecuencia_default()

    _DB_INITIALIZED = True


def ensure_admin(username: str, password: str):
    """
    Crea admin si no existe.
    Mantiene password tal cual (como venías haciendo), para NO romper tu login.
    """
    if not username or not password:
        return

    init_db()

    if _DB_KIND == "sqlite":
        row = fetch_one("SELECT id FROM usuarios WHERE username = ?", [username])
        if row:
            return
        execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            [username, password, "admin"],
        )
    else:
        row = fetch_one("SELECT id FROM usuarios WHERE username = %s", [username])
        if row:
            return
        execute(
            "INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)",
            [username, password, "admin"],
        )


# Import-time init (para que migre solo al arrancar)
init_db()
