# app/clientes.py
from datetime import datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user, require_admin
from app.db import get_connection

router = APIRouter(prefix="/clientes", tags=["clientes"])
templates = Jinja2Templates(directory="templates")


@router.get("")
def clientes_page(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
              id,
              COALESCE(nombre,'') AS nombre,
              COALESCE(documento,'') AS documento,
              COALESCE(telefono,'') AS telefono,
              COALESCE(direccion,'') AS direccion,
              COALESCE(codigo_postal,'') AS codigo_postal,
              COALESCE(observaciones,'') AS observaciones,
              COALESCE(created_at,'') AS created_at
            FROM clientes
            ORDER BY id DESC
        """)
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

    nombre = (nombre or "").strip()
    documento = (documento or "").strip()
    telefono = (telefono or "").strip()
    direccion = (direccion or "").strip()
    codigo_postal = (codigo_postal or "").strip()
    observaciones = (observaciones or "").strip()

    if not nombre:
        return RedirectResponse("/clientes", status_code=303)

    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO clientes (nombre, documento, telefono, direccion, codigo_postal, observaciones, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (nombre, documento, telefono, direccion, codigo_postal, observaciones, created_at),
            )
            conn.commit()
        except Exception:
            # Si hay error por duplicado u otra cosa, no tumbamos la app
            pass
    finally:
        conn.close()

    return RedirectResponse("/clientes", status_code=303)


# ✅ SOLO ADMIN puede eliminar
@router.post("/eliminar")
def eliminar_cliente(
    request: Request,
    cliente_id: int = Form(...),
):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse("/clientes", status_code=303)
