import sqlite3
import os

BASE_DIR = "/var/data"
DB_PATH = os.path.join(BASE_DIR, "bless.db")

os.makedirs(BASE_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cedula TEXT,
            telefono TEXT,
            monto REAL,
            tipo_cobro TEXT
        )
    """)

    conn.commit()
    conn.close()
