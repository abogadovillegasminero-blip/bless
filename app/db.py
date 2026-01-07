# app/db.py
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str):
    """
    Agrega una columna si no existe.
    """
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    cols = [row[1] for row in cur.fetchall()]
    if column not in cols:
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}')
        conn.commit()


def init_db():
    conn = get_connection()
    cur = conn.cursor()

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

    # Si tu código inserta created_at, esta columna debe existir
    try:
        _ensure_column(conn, "clientes", "created_at", "TEXT")
    except Exception:
        pass

    conn.close()


def ensure_admin(username: str, password: str):
    """
    ✅ Admin 'blindado':
    - Si NO existe: lo crea con rol admin
    - Si YA existe: fuerza rol=admin y sincroniza password desde ENV
    Guarda la password hasheada (más seguro) y compatible con tu auth.py.
    """
    if not username or not password:
        return

    # Intentar hashear (recomendado). Si algo falla, cae a texto plano.
    try:
        from app.security import hash_password  # debe existir en tu proyecto
        password_to_store = hash_password(password)
    except Exception:
        password_to_store = password

    conn = get_connection()
    cur = conn.cursor()

    # UPSERT (si tu SQLite lo soporta). Si no, hacemos fallback.
    try:
        cur.execute("""
        INSERT INTO usuarios (username, password, role)
        VALUES (?, ?, 'admin')
        ON CONFLICT(username) DO UPDATE SET
            password = excluded.password,
            role = 'admin'
        """, (username, password_to_store))
    except sqlite3.OperationalError:
        # Fallback: update/insert clásico
        cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE usuarios SET password = ?, role = 'admin' WHERE username = ?",
                (password_to_store, username),
            )
        else:
            cur.execute(
                "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
                (username, password_to_store),
            )

    conn.commit()
    conn.close()


def migrate_excel_to_sqlite(*args, **kwargs):
    """
    Placeholder de seguridad para que Render NO se caiga si alguien lo importa.
    """
    return
