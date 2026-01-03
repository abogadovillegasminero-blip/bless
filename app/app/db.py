import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/var/data/bless.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # CLIENTES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        cedula TEXT NOT NULL,
        telefono TEXT NOT NULL,
        monto REAL NOT NULL,
        tipo_cobro TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # PAGOS (por si ya lo quieres listo)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_cedula TEXT NOT NULL,
        fecha TEXT NOT NULL,
        monto REAL NOT NULL,
        nota TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # SALDOS (opcional, si manejas saldo calculado/guardado)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saldos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_cedula TEXT NOT NULL,
        saldo REAL NOT NULL,
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)

    conn.commit()
    conn.close()
