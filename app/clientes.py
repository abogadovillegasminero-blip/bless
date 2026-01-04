from datetime import datetime

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user
from app.db import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _list_clientes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, cedula, telefono, monto, tipo_cobro FROM clientes ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _get_cliente_by_cedula(cedula: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, cedula, telefono, monto, tipo_cobro FROM clientes WHERE cedula = ?", (cedula,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def _get_cliente_by_id(cliente_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, cedula, telefono, monto, tipo_cobro FROM clientes WHERE id = ?", (cliente_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


@router.get("/clientes", response_class=HTMLResponse)
def ver_clientes(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes = _list_clientes()
    return templates.TemplateResponse("clientes.html", {"request": request, "clientes": clientes, "user": user})


@router.post("/clientes/guardar")
def guardar_cliente(
    request: Request,
    nombre: str = Form(...),
    cedula: str = Form(...),
    telefono: str = Form(...),
    monto: float = Form(...),
    tipo_cobro: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    nombre = str(nombre).strip()
    cedula = str(cedula).strip()
    telefono = str(telefono).strip()
    tipo_cobro = str(tipo_cobro).strip().lower()
    monto = float(monto)

    if not cedula or not nombre:
        return RedirectResponse("/clientes", status_code=303)

    now = datetime.now().isoformat(timespec="seconds")

    conn = get_connection()
    cur = conn.cursor()

    # UPSERT por cédula: si existe, actualiza
    cur.execute("SELECT id FROM clientes WHERE cedula = ?", (cedula,))
    row = cur.fetchone()

    if row:
        cur.execute("""
            UPDATE clientes
            SET nombre = ?, telefono = ?, monto = ?, tipo_cobro = ?
            WHERE cedula = ?
        """, (nombre, telefono, monto, tipo_cobro, cedula))
    else:
        cur.execute("""
            INSERT INTO clientes (nombre, cedula, telefono, monto, tipo_cobro, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, cedula, telefono, monto, tipo_cobro, now))

    conn.commit()
    conn.close()

    return RedirectResponse("/clientes", status_code=303)


@router.get("/clientes/ver", response_class=HTMLResponse)
def ver_cliente(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cedula = (request.query_params.get("cedula") or "").strip()
    if not cedula:
        return RedirectResponse("/clientes", status_code=303)

    cliente = _get_cliente_by_cedula(cedula)
    if not cliente:
        return RedirectResponse("/clientes", status_code=303)

    return templates.TemplateResponse("cliente_ver.html", {"request": request, "cliente": cliente, "user": user})


@router.get("/clientes/editar/{cliente_id}", response_class=HTMLResponse)
def editar_cliente(request: Request, cliente_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cliente = _get_cliente_by_id(cliente_id)
    if not cliente:
        return RedirectResponse("/clientes", status_code=303)

    return templates.TemplateResponse("cliente_editar.html", {"request": request, "cliente": cliente, "user": user})


@router.post("/clientes/actualizar")
def actualizar_cliente(
    request: Request,
    cliente_id: int = Form(...),
    nombre: str = Form(...),
    cedula: str = Form(...),
    telefono: str = Form(...),
    monto: float = Form(...),
    tipo_cobro: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    nombre = str(nombre).strip()
    cedula = str(cedula).strip()
    telefono = str(telefono).strip()
    tipo_cobro = str(tipo_cobro).strip().lower()
    monto = float(monto)

    conn = get_connection()
    cur = conn.cursor()

    # evitar duplicar cédula en otro id
    cur.execute("SELECT id FROM clientes WHERE cedula = ? AND id <> ?", (cedula, cliente_id))
    dup = cur.fetchone()
    if dup:
        conn.close()
        return RedirectResponse("/clientes?error=cedula", status_code=303)

    cur.execute("""
        UPDATE clientes
        SET nombre = ?, cedula = ?, telefono = ?, monto = ?, tipo_cobro = ?
        WHERE id = ?
    """, (nombre, cedula, telefono, monto, tipo_cobro, cliente_id))

    conn.commit()
    conn.close()

    return RedirectResponse("/clientes", status_code=303)


@router.post("/clientes/eliminar")
def eliminar_cliente(request: Request, cliente_id: int = Form(...)):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()
    conn.close()

    return RedirectResponse("/clientes", status_code=303)
