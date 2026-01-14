# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

DB_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL")  # Render Postgres
ALLOW_SQLITE_FALLBACK = os.getenv("ALLOW_SQLITE_FALLBACK", "1") == "1"


def _is_postgres_url(url: str | None) -> bool:
    if not url:
        return False
    u = url.lower()
    return u.startswith("postgres://") or u.startswith("postgresql://")


def _normalize_database_url(url: str | None) -> str | None:
    """
    - Render a veces entrega postgres://
    - psycopg acepta postgresql://
    - Forzamos sslmode=require si no viene
    """
    if not url:
        return url

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    parsed = urlparse(url)
    qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "sslmode" not in qs:
        qs["sslmode"] = "require"

    new_query = urlencode(qs, doseq=True)
    parsed = parsed._replace(query=new_query)
    return urlunparse(parsed)


def using_postgres() -> bool:
    return _is_postgres_url(DATABASE_URL)


def get_connection():
    """
    Devuelve conexión (sqlite3 o psycopg) con una interfaz compatible:
    - conn.cursor()
    - commit / rollback / close
    """
    if using_postgres():
        url = _normalize_database_url(DATABASE_URL)
        try:
            import psycopg  # psycopg3
            from psycopg.rows import dict_row
            conn = psycopg.connect(url, row_factory=dict_row)
            return conn
        except Exception as e:
            # Si Postgres está mal (DNS, URL, etc), evitamos tumbar el deploy si se permite fallback.
            if ALLOW_SQLITE_FALLBACK:
                return _sqlite_conn()
            raise e

    return _sqlite_conn()


def _sqlite_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn():
    """
    Context manager seguro:
    - SIEMPRE yield una conexión válida
    - commit/rollback automático
    """
    conn = get_connection()
    try:
        yield conn
        try:
            conn.commit()
        except Exception:
            # Algunas conexiones/operaciones pueden no requerir commit explícito
            pass
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


def _sqlite_has_column(conn, table: str, col: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r["name"] for r in cur.fetchall()]
    return col in cols


def _sqlite_add_column(conn, table: str, col: str, coltype: str, default_sql: str | None = None):
    if _sqlite_has_column(conn, table, col):
        return
    cur = conn.cursor()
    sql = f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"
    if default_sql:
        sql += f" DEFAULT {default_sql}"
    cur.execute(sql)


def _create_tables_sqlite(conn):
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
        tipo TEXT DEFAULT 'abono',
        monto REAL DEFAULT 0,
        seguro REAL DEFAULT 0,
        monto_entregado REAL DEFAULT 0,
        interes_mensual REAL DEFAULT 0,
        frecuencia TEXT DEFAULT 'mensual',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    )
    """)

    # Mini-migraciones: por si vienes de versiones anteriores
    _sqlite_add_column(conn, "clientes", "codigo_postal", "TEXT")
    _sqlite_add_column(conn, "clientes", "tipo_cobro", "TEXT", "'mensual'")
    _sqlite_add_column(conn, "pagos", "frecuencia", "TEXT", "'mensual'")
    _sqlite_add_column(conn, "pagos", "monto_entregado", "REAL", "0")
    _sqlite_add_column(conn, "pagos", "interes_mensual", "REAL", "0")

    conn.commit()


def _create_tables_postgres(conn):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT NOW()
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
        created_at TIMESTAMP DEFAULT NOW()
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
        fecha DATE NOT NULL,
        tipo TEXT DEFAULT 'abono',
        monto NUMERIC DEFAULT 0,
        seguro NUMERIC DEFAULT 0,
        monto_entregado NUMERIC DEFAULT 0,
        interes_mensual NUMERIC DEFAULT 0,
        frecuencia TEXT DEFAULT 'mensual',
        created_at TIMESTAMP DEFAULT NOW()
    )
    """)

    # Mini-migraciones Postgres (ADD COLUMN IF NOT EXISTS)
    cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_postal TEXT;")
    cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tipo_cobro TEXT DEFAULT 'mensual';")
    cur.execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS frecuencia TEXT DEFAULT 'mensual';")
    cur.execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS monto_entregado NUMERIC DEFAULT 0;")
    cur.execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS interes_mensual NUMERIC DEFAULT 0;")

    conn.commit()


def init_db():
    """
    Inicializa DB según backend:
    - Postgres si DATABASE_URL es postgres*
    - Si falla y ALLOW_SQLITE_FALLBACK=1, cae a SQLite para no tumbar Render.
    """
    if using_postgres():
        try:
            with get_conn() as conn:
                _create_tables_postgres(conn)
            return
        except Exception:
            if not ALLOW_SQLITE_FALLBACK:
                raise
            # fallback
            with get_conn() as conn:
                _create_tables_sqlite(conn)
            return

    with get_conn() as conn:
        _create_tables_sqlite(conn)


def ensure_admin(username: str, password: str):
    if not username or not password:
        return

    with get_conn() as conn:
        cur = conn.cursor()

        # sqlite devuelve Row; postgres devuelve dict_row (ya dict)
        def _fetchone():
            r = cur.fetchone()
            if r is None:
                return None
            try:
                return dict(r)
            except Exception:
                return r

        # Buscar admin
        try:
            cur.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        except Exception:
            cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))

        row = _fetchone()
        if row:
            return

        # Insertar admin
        try:
            cur.execute(
                "INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)",
                (username, password, "admin"),
            )
        except Exception:
            cur.execute(
                "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                (username, password, "admin"),
            )
