import os
import sqlite3
from urllib.parse import urlparse

import psycopg2


SQLITE_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def is_postgres() -> bool:
    return DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")


def get_connection():
    """
    Devuelve conexión DB-API.
    - Si hay DATABASE_URL (Postgres) -> psycopg2
    - Si no -> sqlite3 local (ojo: en Render, si no tienes Disk, se puede perder en redeploy)
    """
    if is_postgres():
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(SQLITE_PATH, check_same_thread=False)


def _execute(sql: str, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
    finally:
        conn.close()


def init_db():
    """
    Crea tabla de usuarios si no existe (válido tanto para SQLite como Postgres).
    """
    if is_postgres():
        _execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """)
    else:
        _execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """)


def ensure_admin(username: str, password: str):
    """
    Crea admin si no existe. (Mantiene password en texto como venías usando, para no romper login).
    """
    if not username or not password:
        return

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE username = %s" if is_postgres() else "SELECT id FROM usuarios WHERE username = ?",
                    (username,))
        row = cur.fetchone()
        if row:
            return

        insert_sql = "INSERT INTO usuarios (username, password, role) VALUES (%s,%s,%s)" if is_postgres() \
                     else "INSERT INTO usuarios (username, password, role) VALUES (?,?,?)"
        cur.execute(insert_sql, (username, password, "admin"))
        conn.commit()
    finally:
        conn.close()
