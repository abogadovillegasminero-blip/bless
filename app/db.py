import os
import sqlite3

try:
    import psycopg2
except ImportError:
    psycopg2 = None


def get_db_url() -> str | None:
    url = os.getenv("DATABASE_URL")
    if not url:
        return None

    # Render a veces da postgres://, psycopg2 prefiere postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


def init_db():
    db_url = get_db_url()

    # ✅ Si hay Postgres configurado, crea tabla allá
    if db_url:
        if psycopg2 is None:
            raise RuntimeError(
                "psycopg2-binary no está instalado. Agrégalo a requirements.txt"
            )

        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        return

    # ✅ Fallback SQLite (no persistente en Render Free)
    db_path = "/tmp/bless.db"
    conn = sqlite3.connect(db_path, check_same_thread=False)
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
