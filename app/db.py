import os
import sqlite3

import psycopg2


SQLITE_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def is_postgres() -> bool:
    return DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")


def get_connection():
    if is_postgres():
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(SQLITE_PATH, check_same_thread=False)


def init_db():
    conn = get_connection()
    try:
        cur = conn.cursor()

        if is_postgres():
            cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
            """)
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
            """)

        conn.commit()
    finally:
        conn.close()


def ensure_admin(username: str, password: str):
    if not username or not password:
        return

    conn = get_connection()
    try:
        cur = conn.cursor()

        if is_postgres():
            cur.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        else:
            cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))

        row = cur.fetchone()
        if row:
            return

        if is_postgres():
            cur.execute(
                "INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)",
                (username, password, "admin")
            )
        else:
            cur.execute(
                "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                (username, password, "admin")
            )

        conn.commit()
    finally:
        conn.close()
