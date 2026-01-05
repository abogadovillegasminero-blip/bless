# app/db.py
import os
import sqlite3
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Tabla de usuarios (incluye rol)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)

    # Tabla clientes (si no existe)
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

    # Tabla pagos (si no existe)
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
    conn.close()


def ensure_admin(username: str, password: str):
    """
    Crea el admin si no existe.
    NOTA: guarda password tal cual (sin hash) para no romper tu login actual.
    """
    if not username or not password:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()

    if not row:
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
            (username, password)
        )
        conn.commit()

    conn.close()


def migrate_excel_to_sqlite(*args, **kwargs):
    """
    ✅ FUNCIÓN DE SEGURIDAD PARA QUE RENDER NO SE CAIGA.

    Si en algún momento en main.py la importas, Render no fallará por ImportError.
    Hoy NO es necesaria para correr Bless, así que solo deja esto como 'placeholder'.
    """
    return
