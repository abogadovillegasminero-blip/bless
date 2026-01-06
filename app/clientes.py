# app/clientes.py
import os
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter(prefix="/clientes", tags=["clientes"])
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
def listar_clientes(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY id DESC')
        clientes = cur.fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse(
        "clientes.html",
        {"request": request, "user": user, "clientes": clientes},
    )


@router.post("/crear")
def crear_cliente(
    request: Request,
    nombre: str = Form(...),
    documento: str = Form(""),
    telefono: str = Form(""),
    direccion: str = Form(""),
    codigo_postal: str = Form(""),
    observaciones: str = Form(""),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()

        # created_at ✅ (init_db ya asegura que la columna exista)
        cur.execute(
            """
            INSERT INTO clientes (nombre, documento, telefono, direccion, codigo_postal, observaciones, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre.strip(),
                documento.strip(),
                telefono.strip(),
                direccion.strip(),
                codigo_postal.strip(),
                observaciones.strip(),
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/clientes", status_code=303)


@router.get("/eliminar/{cliente_id}")
def eliminar_cliente(request: Request, cliente_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/clientes", status_code=303)
