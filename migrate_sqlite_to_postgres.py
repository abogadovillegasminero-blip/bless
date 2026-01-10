# scripts/migrate_sqlite_to_postgres.py
import os
import sqlite3

# Requiere psycopg (v3) instalado en tu entorno local:
# pip install "psycopg[binary]"

import psycopg
from psycopg.rows import dict_row


SQLITE_PATH = os.getenv("DB_PATH", "bless.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    raise SystemExit("ERROR: Falta DATABASE_URL (Postgres). Exporta la variable en PowerShell antes de ejecutar.")

if "sslmode=" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"


def sqlite_rows(conn, table: str):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} ORDER BY id ASC")
    return [dict(r) for r in cur.fetchall()]


def ensure_tables(pg):
    # Crea tablas si no existen (igual que app/db.py)
    with pg.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            documento TEXT,
            telefono TEXT,
            direccion TEXT,
            observaciones TEXT,
            tipo_cobro TEXT DEFAULT 'mensual'
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            monto DOUBLE PRECISION DEFAULT 0,
            seguro DOUBLE PRECISION DEFAULT 0,
            monto_entregado DOUBLE PRECISION DEFAULT 0,
            interes_mensual DOUBLE PRECISION DEFAULT 20,
            frecuencia TEXT DEFAULT 'mensual'
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pagos_cliente_id ON pagos(cliente_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha)")


def set_sequence(pg, table: str):
    # Ajusta la secuencia al MAX(id) para que nuevos inserts sigan bien
    with pg.cursor() as cur:
        cur.execute(f"SELECT COALESCE(MAX(id), 0) AS m FROM {table}")
        m = cur.fetchone()["m"]
        # nombre secuencia: <table>_id_seq (convención por SERIAL)
        cur.execute(f"SELECT setval('{table}_id_seq', %s, true)", [m])


def main():
    print("SQLite:", SQLITE_PATH)
    print("Postgres:", DATABASE_URL.split("@")[-1].split("?")[0])

    # Leer SQLite
    sconn = sqlite3.connect(SQLITE_PATH)
    usuarios = sqlite_rows(sconn, "usuarios") if _sqlite_has_table(sconn, "usuarios") else []
    clientes = sqlite_rows(sconn, "clientes") if _sqlite_has_table(sconn, "clientes") else []
    pagos = sqlite_rows(sconn, "pagos") if _sqlite_has_table(sconn, "pagos") else []
    sconn.close()

    print(f"SQLite rows -> usuarios={len(usuarios)} clientes={len(clientes)} pagos={len(pagos)}")

    # Conectar Postgres
    pg = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    try:
        with pg.transaction():
            ensure_tables(pg)

            # MIGRAR USUARIOS (por username único)
            with pg.cursor() as cur:
                for u in usuarios:
                    cur.execute("""
                        INSERT INTO usuarios (id, username, password, role)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (username) DO UPDATE
                        SET password = EXCLUDED.password,
                            role = EXCLUDED.role
                    """, [
                        u.get("id"),
                        u.get("username"),
                        u.get("password"),
                        u.get("role") or "user"
                    ])

            # MIGRAR CLIENTES (por id)
            with pg.cursor() as cur:
                for c in clientes:
                    # Compat: si en SQLite existía cedula y no documento
                    documento = c.get("documento") or c.get("cedula")
                    cur.execute("""
                        INSERT INTO clientes (id, nombre, documento, telefono, direccion, observaciones, tipo_cobro)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET nombre = EXCLUDED.nombre,
                            documento = EXCLUDED.documento,
                            telefono = EXCLUDED.telefono,
                            direccion = EXCLUDED.direccion,
                            observaciones = EXCLUDED.observaciones,
                            tipo_cobro = EXCLUDED.tipo_cobro
                    """, [
                        c.get("id"),
                        c.get("nombre"),
                        documento,
                        c.get("telefono"),
                        c.get("direccion"),
                        c.get("observaciones"),
                        (c.get("tipo_cobro") or "mensual")
                    ])

            # MIGRAR PAGOS (por id)
            with pg.cursor() as cur:
                for p in pagos:
                    frecuencia = p.get("frecuencia") or "mensual"
                    # en abono puede venir null -> ok
                    cur.execute("""
                        INSERT INTO pagos (id, cliente_id, fecha, tipo, monto, seguro, monto_entregado, interes_mensual, frecuencia)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET cliente_id = EXCLUDED.cliente_id,
                            fecha = EXCLUDED.fecha,
                            tipo = EXCLUDED.tipo,
                            monto = EXCLUDED.monto,
                            seguro = EXCLUDED.seguro,
                            monto_entregado = EXCLUDED.monto_entregado,
                            interes_mensual = EXCLUDED.interes_mensual,
                            frecuencia = EXCLUDED.frecuencia
                    """, [
                        p.get("id"),
                        p.get("cliente_id"),
                        p.get("fecha"),
                        p.get("tipo"),
                        p.get("monto") or 0,
                        p.get("seguro") or 0,
                        p.get("monto_entregado") or 0,
                        p.get("interes_mensual") or 0,
                        frecuencia
                    ])

            # Ajustar secuencias
            set_sequence(pg, "usuarios")
            set_sequence(pg, "clientes")
            set_sequence(pg, "pagos")

        print("✅ Migración terminada OK.")
    finally:
        pg.close()


def _sqlite_has_table(conn, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


if __name__ == "__main__":
    main()
