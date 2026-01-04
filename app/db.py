import os
import sqlite3
from datetime import datetime

import pandas as pd

from app.security import hash_password, looks_hashed  # ya lo tienes

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # USUARIOS
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    """)

    # =========================
    # CLIENTES
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        cedula TEXT UNIQUE NOT NULL,
        telefono TEXT NOT NULL,
        monto REAL NOT NULL DEFAULT 0,
        tipo_cobro TEXT NOT NULL DEFAULT 'diario',
        created_at TEXT NOT NULL
    )
    """)

    # =========================
    # PAGOS
    # (guardamos snapshot: cliente/cedula/tipo_cobro para reportes rápidos)
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cedula TEXT NOT NULL,
        cliente TEXT NOT NULL,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        tipo_cobro TEXT NOT NULL,
        registrado_por TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_clientes_cedula ON clientes(cedula)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pagos_cedula ON pagos(cedula)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha)")

    conn.commit()
    conn.close()


def ensure_admin(username: str, password: str):
    """
    Crea el admin si no existe.
    - Si lo crea por primera vez: guarda password HASHEADO.
    - Si ya existe: no toca nada.
    """
    if not username or not password:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()

    if row is None:
        hashed = hash_password(password)
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
            (username, hashed)
        )
        conn.commit()

    conn.close()


def migrate_excel_to_sqlite():
    """
    IMPORTA data/clientes.xlsx y data/pagos.xlsx a SQLite
    SOLO si las tablas están vacías.
    """
    data_dir = "data"
    clientes_xlsx = os.path.join(data_dir, "clientes.xlsx")
    pagos_xlsx = os.path.join(data_dir, "pagos.xlsx")

    os.makedirs(data_dir, exist_ok=True)

    conn = get_connection()
    cur = conn.cursor()

    # ====== clientes ======
    cur.execute("SELECT COUNT(1) AS c FROM clientes")
    clientes_count = int(cur.fetchone()["c"])

    if clientes_count == 0 and os.path.exists(clientes_xlsx):
        df = pd.read_excel(clientes_xlsx)

        # normaliza columnas
        for col in ["nombre", "cedula", "telefono", "monto", "tipo_cobro"]:
            if col not in df.columns:
                df[col] = ""

        df["cedula"] = df["cedula"].astype(str)
        df["nombre"] = df["nombre"].astype(str).replace(["nan", "NaT", "None"], "")
        df["telefono"] = df["telefono"].astype(str).replace(["nan", "NaT", "None"], "")
        df["tipo_cobro"] = (
            df["tipo_cobro"]
            .astype(str)
            .replace(["nan", "NaT", "None"], "")
            .str.lower()
            .str.strip()
        )
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

        now = datetime.now().isoformat(timespec="seconds")

        for _, r in df.iterrows():
            cedula = str(r["cedula"]).strip()
            if not cedula:
                continue

            nombre = str(r["nombre"]).strip() or "SIN_NOMBRE"
            telefono = str(r["telefono"]).strip() or "N/A"
            tipo_cobro = (str(r["tipo_cobro"]).strip().lower() or "diario")
            monto = float(r["monto"]) if str(r["monto"]).strip() != "" else 0.0

            # insert ignore duplicates
            cur.execute("""
                INSERT OR IGNORE INTO clientes (nombre, cedula, telefono, monto, tipo_cobro, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nombre, cedula, telefono, monto, tipo_cobro, now))

        conn.commit()

    # ====== pagos ======
    cur.execute("SELECT COUNT(1) AS c FROM pagos")
    pagos_count = int(cur.fetchone()["c"])

    if pagos_count == 0 and os.path.exists(pagos_xlsx):
        df = pd.read_excel(pagos_xlsx)

        # compatibilidad: "monto" -> "valor"
        if "monto" in df.columns and "valor" not in df.columns:
            df.rename(columns={"monto": "valor"}, inplace=True)

        for col in ["cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"]:
            if col not in df.columns:
                df[col] = ""

        df["cedula"] = df["cedula"].astype(str)
        df["cliente"] = df["cliente"].astype(str).replace(["nan", "NaT", "None"], "")
        df["fecha"] = df["fecha"].astype(str).replace(["nan", "NaT", "None"], "")
        df["hora"] = df["hora"].astype(str).replace(["nan", "NaT", "None"], "")
        df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "").str.lower().str.strip()
        df["registrado_por"] = df["registrado_por"].astype(str).replace(["nan", "NaT", "None"], "")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

        now = datetime.now().isoformat(timespec="seconds")

        for _, r in df.iterrows():
            cedula = str(r["cedula"]).strip()
            if not cedula:
                continue

            cliente = str(r["cliente"]).strip() or "SIN_CLIENTE"
            fecha = str(r["fecha"]).strip() or ""
            hora = str(r["hora"]).strip() or "00:00:00"
            tipo_cobro = str(r["tipo_cobro"]).strip().lower() or "diario"
            registrado_por = str(r["registrado_por"]).strip() or ""
            valor = float(r["valor"])

            if not fecha:
                continue  # sin fecha no lo importamos

            cur.execute("""
                INSERT INTO pagos (cedula, cliente, fecha, hora, valor, tipo_cobro, registrado_por, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cedula, cliente, fecha, hora, valor, tipo_cobro, registrado_por, now))

        conn.commit()

    conn.close()
