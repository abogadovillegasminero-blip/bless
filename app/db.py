import os

DATABASE_URL = os.getenv("DATABASE_URL")

# Si no hay DATABASE_URL, cae a SQLite temporal (solo para pruebas)
USE_SQLITE = not DATABASE_URL

if USE_SQLITE:
    import sqlite3

    DB_PATH = "/tmp/bless.db"

    def get_connection():
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    def init_db():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
        """)
        conn.commit()
        conn.close()

else:
    import psycopg2

    def get_connection():
        # psycopg2 usa DATABASE_URL tal cual la entrega Render
        return psycopg2.connect(DATABASE_URL)

    def init_db():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
        """)
        conn.commit()
        cur.close()
        conn.close()
