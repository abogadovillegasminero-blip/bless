# app/db.py
import os
import sqlite3
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# =========================
# SQLITE (local o fallback)
# =========================
DEFAULT_DB = "/var/data/bless.db"
FALLBACK_LOCAL = str(Path(__file__).resolve().parent.parent / "data" / "bless.db")
DB_PATH = os.getenv("DB_PATH", DEFAULT_DB)


def _safe_db_path() -> str:
    p = Path(DB_PATH)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    except Exception:
        p2 = Path(FALLBACK_LOCAL)
        p2.parent.mkdir(parents=True, exist_ok=True)
        return str(p2)


# =========================
# POSTGRES (Render Free OK)
# =========================
def _replace_qmarks_outside_quotes(sql: str) -> str:
    # Reemplaza ? -> %s solo fuera de strings '...'
    parts = sql.split("'")
    for i in range(0, len(parts), 2):
        parts[i] = parts[i].replace("?", "%s")
    return "'".join(parts)


class _PGCompatCursor:
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, params=None):
        sql = _replace_qmarks_outside_quotes(sql)
        return self._cur.execute(sql, params or ())

    def executemany(self, sql, seq_of_params):
        sql = _replace_qmarks_outside_quotes(sql)
        return self._cur.executemany(sql, seq_of_params)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __getattr__(self, name):
        return getattr(self._cur, name)


class _PGCompatConn:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        # RealDictCursor: filas como dict (compat con tu app)
        from psycopg2.extras import RealDictCursor
        return _PGCompatCursor(self._conn.cursor(cursor_factory=RealDictCursor))

    def commit(self):
        return self._conn.commit()

    def close(self):
        return self._conn.close()

    def execute(self, *a, **kw):
        cur = self.cursor()
        cur.execute(*a, **kw)
        return cur

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_connection():
    # Si hay Postgres, úsalo SIEMPRE (esto evita que se borre la info en Render Free)
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return _PGCompatConn(conn)

    # Si no hay DATABASE_URL, usa sqlite (local)
    db_file = _safe_db_path()
    conn = sqlite3.connect(db_file, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    if DATABASE_URL:
        # ===== POSTGRES =====
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
            created_at TEXT
        )
        """)

        # ✅ Pagos (y préstamos) + ✅ frecuencia
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER REFERENCES clientes(id),
            fecha TEXT,
            valor DOUBLE PRECISION,
            nota TEXT,
            tipo TEXT,
            seguro DOUBLE PRECISION,
            monto_entregado DOUBLE PRECISION,
            interes_mensual DOUBLE PRECISION,
            frecuencia TEXT
        )
        """)

        # “Migraciones seguras”
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS created_at TEXT")

        cur.execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS tipo TEXT")
        cur.execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS seguro DOUBLE PRECISION")
        cur.execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS monto_entregado DOUBLE PRECISION")
        cur.execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS interes_mensual DOUBLE PRECISION")
        # ✅ NUEVO
        cur.execute("ALTER TABLE pagos ADD COLUMN IF NOT EXISTS frecuencia TEXT")

        conn.commit()
        conn.close()
        return

    # ===== SQLITE =====
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
        observaciones TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        fecha TEXT,
        valor REAL,
        nota TEXT,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    """)

    conn.commit()

    # Migraciones seguras en sqlite
    def _ensure_column_sqlite(connection, table, column, col_type):
        c = connection.cursor()
        c.execute(f'PRAGMA table_info("{table}")')
        cols = [row[1] for row in c.fetchall()]
        if column not in cols:
            c.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}')
            connection.commit()

    try:
        _ensure_column_sqlite(conn, "clientes", "created_at", "TEXT")

        _ensure_column_sqlite(conn, "pagos", "tipo", "TEXT")
        _ensure_column_sqlite(conn, "pagos", "seguro", "REAL")
        _ensure_column_sqlite(conn, "pagos", "monto_entregado", "REAL")
        _ensure_column_sqlite(conn, "pagos", "interes_mensual", "REAL")
        # ✅ NUEVO
        _ensure_column_sqlite(conn, "pagos", "frecuencia", "TEXT")
    except Exception:
        pass

    conn.close()


def ensure_admin(username: str, password: str):
    if not username or not password:
        return

    conn = get_connection()
    cur = conn.cursor()

    # (El wrapper de Postgres convierte ? -> %s automáticamente)
    cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()

    if not row:
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
            (username, password),
        )
        conn.commit()

    conn.close()


def migrate_excel_to_sqlite(*args, **kwargs):
    return
