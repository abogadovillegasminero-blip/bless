# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse

# Detecta Postgres por DATABASE_URL (Render) o usa SQLite por DB_PATH
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = os.getenv("DB_PATH", "bless.db")

_DB_KIND = "postgres" if DATABASE_URL else "sqlite"

# Para evitar re-ejecutar init_db en cada import raro
_DB_INITIALIZED = False


def db_kind() -> str:
    return _DB_KIND


def _sqlite_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _postgres_conn():
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # Render suele dar postgres://...
    # psycopg2 acepta postgres:// sin problema, pero forzamos sslmode si no viene.
    dsn = DATABASE_URL
    if "sslmode=" not in dsn:
        sep = "&" if "?" in dsn else "?"
        dsn = f"{dsn}{sep}sslmode=require"

    return psycopg2.connect(dsn, cursor_factory=RealDictCursor)


@contextmanager
def get_conn():
    """
    Context manager unificado.
    - SQLite: sqlite3.Connection
    - Postgres: psycopg2.Connection
    """
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


def _placeholders(n: int) -> str:
    """
    Devuelve placeholders según motor:
    - sqlite: ?,?,?
    - postgres: %s,%s,%s
    """
    if n <= 0:
        return ""
    ph = "?" if _DB_KIND == "sqlite" else "%s"
    return ",".join([ph] * n)


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


def execute(sql: str, params=None) -> int:
    """
    Ejecuta SQL y retorna rowcount.
    """
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.rowcount


def insert_and_get_id(sql_sqlite: str, sql_postgres: str, params=None) -> int:
    """
    Inserta y retorna ID.
    - SQLite: usa lastrowid
    - Postgres: requiere RETURNING id
    """
    params = params or []
    with get_conn() as conn:
        cur = conn.cursor()
        if _DB_KIND == "sqlite":
            cur.execute(sql_sqlite, params)
            return int(cur.lastrowid)
        else:
            cur.execute(sql_postgres, params)
            row = cur.fetchone()
            return int(row["id"]) if isinstance(row, dict) else int(row[0])


# --------------------------
# MIGRACIÓN / SCHEMA SEGURO
# --------------------------

def _sqlite_table_columns(table: str) -> set[str]:
    rows = fetch_all(f"PRAGMA table_info({table})")
    cols = set()
    for r in rows:
        # sqlite3.Row: r["name"]
        cols.add(r["name"])
    return cols


def _postgres_table_columns(table: str) -> set[str]:
    sql = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name=%s
    """
    rows = fetch_all(sql, [table])
    cols = set()
    for r in rows:
        # RealDictCursor => dict
        if isinstance(r, dict):
            cols.add(r["column_name"])
        else:
            cols.add(r[0])
    return cols


def table_columns(table: str) -> set[str]:
    if _DB_KIND == "sqlite":
        return _sqlite_table_columns(table)
    return _postgres_table_columns(table)


def _create_tables_sqlite():
    # Nota: SQLite no soporta DROP COLUMN fácil -> solo dejamos de usar codigo_postal.
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
        monto REAL DEFAULT 0, -- abono
        seguro REAL DEFAULT 0,
        monto_entregado REAL DEFAULT 0, -- prestamo
        interes_mensual REAL DEFAULT 20, -- porcentaje
        frecuencia TEXT DEFAULT 'mensual',
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    """)

    # Índices útiles
    execute("CREATE INDEX IF NOT EXISTS idx_pagos_cliente_id ON pagos(cliente_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha)")


def _create_tables_postgres():
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


def _add_column_if_missing(table: str, column: str, col_type: str, default_sql: str | None = None):
    cols = table_columns(table)
    if column in cols:
        return

    if _DB_KIND == "sqlite":
        # SQLite: ALTER TABLE ADD COLUMN permite DEFAULT literal
        if default_sql:
            execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default_sql}")
        else:
            execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    else:
        # Postgres: ADD COLUMN IF NOT EXISTS
        if default_sql:
            execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type} DEFAULT {default_sql}")
        else:
            execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}")


def _backfill_documento_from_cedula():
    """
    Si existía clientes.cedula y no existe documento (o documento vacío), copiar.
    """
    cols = table_columns("clientes")
    if "cedula" not in cols:
        return
    if "documento" not in cols:
        _add_column_if_missing("clientes", "documento", "TEXT")

    # Copiar cedula -> documento donde documento esté NULL o vacío
    if _DB_KIND == "sqlite":
        execute("""
        UPDATE clientes
        SET documento = COALESCE(documento, cedula)
        WHERE (documento IS NULL OR TRIM(documento) = '') AND cedula IS NOT NULL AND TRIM(cedula) <> ''
        """)
    else:
        execute("""
        UPDATE clientes
        SET documento = COALESCE(documento, cedula)
        WHERE (documento IS NULL OR BTRIM(documento) = '') AND cedula IS NOT NULL AND BTRIM(cedula) <> ''
        """)


def _backfill_frecuencia_default():
    """
    Si pagos.frecuencia está NULL/vacía, dejar 'mensual' (requisito: si vacío, asumir mensual).
    """
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


def init_db():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return

    # 1) Crear tablas base
    if _DB_KIND == "sqlite":
        _create_tables_sqlite()
    else:
        _create_tables_postgres()

    # 2) Migraciones seguras (ADD COLUMN sin tumbar)
    _add_column_if_missing("clientes", "tipo_cobro", "TEXT", "'mensual'")
    _add_column_if_missing("pagos", "frecuencia", "TEXT", "'mensual'")

    # 3) Normalizaciones
    _backfill_documento_from_cedula()
    _backfill_frecuencia_default()

    _DB_INITIALIZED = True


# Ejecuta migración automáticamente (seguro)
init_db()
