# app/pagos.py
import os
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter(prefix="/pagos", tags=["pagos"])
templates = Jinja2Templates(directory="templates")

DB_PATH = os.getenv("DB_PATH", "/tmp/bless.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    return conn


@router.get("")
def ver_pagos(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Clientes para el select
        cur.execute('SELECT id, nombre FROM clientes ORDER BY nombre ASC')
        clientes = cur.fetchall()

        # Pagos con nombre del cliente
        cur.execute("""
            SELECT
                p.id,
                p.cliente_id,
                c.nombre AS cliente_nombre,
                p.fecha,
                p.valor,
                p.nota
            FROM pagos p
            LEFT JOIN clientes c ON c.id = p.cliente_id
            ORDER BY p.id DESC
        """)
        pagos = cur.fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse(
        "pagos.html",
        {"request": request, "user": user, "clientes": clientes, "pagos": pagos},
    )


@router.post("/crear")
def crear_pago(
    request: Request,
    cliente_id: int = Form(...),
    fecha: str = Form(""),
    valor: float = Form(...),
    nota: str = Form(""),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    # Si no mandan fecha, usa hoy
    fecha_final = (fecha or "").strip()
    if not fecha_final:
        fecha_final = datetime.utcnow().date().isoformat()

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pagos (cliente_id, fecha, valor, nota, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            int(cliente_id),
            fecha_final,
            float(valor),
            (nota or "").strip(),
            datetime.utcnow().isoformat(timespec="seconds"),
        ))
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/pagos", status_code=303)


@router.get("/eliminar/{pago_id}")
def eliminar_pago(request: Request, pago_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM pagos WHERE id = ?", (pago_id,))
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/pagos", status_code=303)
