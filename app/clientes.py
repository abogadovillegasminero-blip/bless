# app/clientes.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

TIPOS_COBRO = ["diario", "semanal", "quincenal", "mensual"]

@router.get("/clientes")
def listar_clientes(request: Request, edit_id: int | None = None):
    clientes = db.fetch_all("""
        SELECT
            id, nombre, documento, telefono, direccion, observaciones,
            COALESCE(NULLIF(tipo_cobro,''), 'mensual') AS tipo_cobro
        FROM clientes
        ORDER BY nombre ASC
    """)

    edit_cliente = None
    if edit_id:
        edit_cliente = db.fetch_one("""
            SELECT
                id, nombre, documento, telefono, direccion, observaciones,
                COALESCE(NULLIF(tipo_cobro,''), 'mensual') AS tipo_cobro
            FROM clientes
            WHERE id = ?
        """, (edit_id,))

    return templates.TemplateResponse(
        "clientes.html",
        {
            "request": request,
            "clientes": clientes,
            "edit_cliente": edit_cliente,
            "tipos_cobro": TIPOS_COBRO,
        }
    )

@router.post("/clientes/crear")
def crear_cliente(
    nombre: str = Form(...),
    documento: str = Form(""),
    telefono: str = Form(""),
    direccion: str = Form(""),
    observaciones: str = Form(""),
    tipo_cobro: str = Form("mensual"),
):
    tipo_cobro = (tipo_cobro or "").strip().lower()
    if tipo_cobro not in TIPOS_COBRO:
        tipo_cobro = "mensual"

    db.execute("""
        INSERT INTO clientes (nombre, documento, telefono, direccion, observaciones, tipo_cobro)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nombre, documento, telefono, direccion, observaciones, tipo_cobro))

    return RedirectResponse("/clientes", status_code=303)

@router.post("/clientes/actualizar")
def actualizar_cliente(
    cliente_id: int = Form(...),
    nombre: str = Form(...),
    documento: str = Form(""),
    telefono: str = Form(""),
    direccion: str = Form(""),
    observaciones: str = Form(""),
    tipo_cobro: str = Form("mensual"),
):
    tipo_cobro = (tipo_cobro or "").strip().lower()
    if tipo_cobro not in TIPOS_COBRO:
        tipo_cobro = "mensual"

    db.execute("""
        UPDATE clientes
        SET nombre = ?, documento = ?, telefono = ?, direccion = ?, observaciones = ?, tipo_cobro = ?
        WHERE id = ?
    """, (nombre, documento, telefono, direccion, observaciones, tipo_cobro, cliente_id))

    return RedirectResponse("/clientes", status_code=303)

@router.post("/clientes/eliminar/{cliente_id}")
def eliminar_cliente(cliente_id: int):
    # En Postgres ON DELETE CASCADE elimina pagos.
    # En SQLite por seguridad, borra pagos primero.
    if db.db_kind() == "sqlite":
        db.execute("DELETE FROM pagos WHERE cliente_id = ?", (cliente_id,))
    db.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    return RedirectResponse("/clientes", status_code=303)
