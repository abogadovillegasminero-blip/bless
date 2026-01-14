# app/db.py
import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# =========================
# Config
# =========================
DB_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_RENDER") or os.getenv("DATABASE")

# =========================
# Helpers
# =========================
def _normalize_database_url(url: str) -> str:
    """
    Render a veces entrega 'postgres://'. psycopg3 acepta 'postgresql://'.
    También forzamos sslmode=require si no viene.
    """
    if not url:
        return url

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    parsed = urlparse(url)
    qs = dict(parse_qsl(parsed.query))

    if "sslmode" not in qs:
        qs["sslmode"] = "require"

    new_query = urlencode(qs)
    return urlunparse(parsed._replace(query=new_query))


def using_postgres() -> bool:
    return bool(DATABASE_URL)


def _sqlite_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _postgres_conn():
    # psycopg3
    import psycopg

    url = _normalize_database_url(DATABASE_URL)
    # sslmode ya va en la URL (pero Render exige SSL)
    return psycopg.connect(url)


# =========================
# Public API (Compat)
# =========================
def get_connection():
    """
    IMPORTANTE: algunos módulos importan `get_connection` directo.
    Retorna una conexión "directa" (NO contextmanager).
    """
    if using_postgres():
        return _postgres_conn()
    return _sqlite_conn()


@contextmanager
def get_conn():
    """
    Context manager correcto: SIEMPRE hace yield de la conexión.
    Esto evita el error: TypeError: 'NoneType' object is not an iterator
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def execute(sql: str, params=None, *, fetchone=False, fetchall=False):
    """
    Ejecuta SQL con commit y opcional fetch.
    Compatible con sqlite3.Row y psycopg3.
    """
    if params is None:
        params = ()

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)

        # commit para INSERT/UPDATE/DDL
        try:
            conn.commit()
        except Exception:
            pass

        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return None


# =========================
# Schema
# =========================
def _create_tables_sqlite():
    execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """
    )

    execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            documento TEXT,
            telefono TEXT,
            direccion TEXT,
            codigo_postal TEXT,
            observaciones TEXT,
            tipo_cobro TEXT DEFAULT 'mensual',
            creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    execute(
        """
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            monto REAL NOT NULL DEFAULT 0,
            seguro REAL NOT NULL DEFAULT 0,
            monto_entregado REAL NOT NULL DEFAULT 0,
            interes_mensual REAL NOT NULL DEFAULT 0,
            frecuencia TEXT DEFAULT 'mensual',
            FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
        )
        """
    )


def _create_tables_postgres():
    # Nota: SERIAL para ids, y timestamp default.
    execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """
    )

    execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            documento TEXT,
            telefono TEXT,
            direccion TEXT,
            codigo_postal TEXT,
            observaciones TEXT,
            tipo_cobro TEXT DEFAULT 'mensual',
            creado TIMESTAMP DEFAULT NOW()
        )
        """
    )

    execute(
        """
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            monto DOUBLE PRECISION NOT NULL DEFAULT 0,
            seguro DOUBLE PRECISION NOT NULL DEFAULT 0,
            monto_entregado DOUBLE PRECISION NOT NULL DEFAULT 0,
            interes_mensual DOUBLE PRECISION NOT NULL DEFAULT 0,
            frecuencia TEXT DEFAULT 'mensual'
        )
        """
    )


def init_db():
    """
    Crea tablas en SQLite o Postgres según exista DATABASE_URL.
    """
    if using_postgres():
        _create_tables_postgres()
    else:
        _create_tables_sqlite()


# =========================
# Admin bootstrap
# =========================
def ensure_admin(username: str, password: str):
    """
    Crea el admin si no existe.
    """
    if not username or not password:
        return

    row = execute(
        "SELECT id FROM usuarios WHERE username = %s" if using_postgres() else "SELECT id FROM usuarios WHERE username = ?",
        (username,),
        fetchone=True,
    )

    if row:
        return

    if using_postgres():
        execute(
            "INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)",
            (username, password, "admin"),
        )
    else:
        execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            (username, password, "admin"),
        )
