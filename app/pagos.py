# app/pagos.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

from app import db
from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

FRECUENCIAS = ["diario", "semanal", "quincenal", "mensual"]

def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@router.get("/pagos")
def pagos_home(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes = db.fetch_all("""
        SELECT id, nombre, documento
        FROM clientes
        ORDER BY nombre ASC
    """)

    movimientos = db.fetch_all("""
        SELECT
            p.id,
            p.fecha,
            p.tipo,
            p.monto,
            p.seguro,
            p.monto_entregado,
            p.interes_mensual,
            COALESCE(NULLIF(p.frecuencia, ''), 'mensual') AS frecuencia,
            c.nombre AS cliente_nombre
        FROM pagos p
        JOIN clientes c ON c.id = p.cliente_id
        ORDER BY p.id DESC
        LIMIT 50
    """)

    return templates.TemplateResponse(
        "pagos.html",
        {"request": request, "user": user, "clientes": clientes, "movimientos": movimientos, "frecuencias": FRECUENCIAS},
    )

@router.post("/pagos/crear")
def crear_pago(
    request: Request,
    cliente_id: int = Form(...),
    tipo: str = Form(...),  # abono | prestamo
    monto: float = Form(0),
    seguro: float = Form(0),
    monto_entregado: float = Form(0),
    interes_mensual: float = Form(20),
    frecuencia: str = Form("mensual"),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    tipo = (tipo or "").strip().lower()
    frecuencia = (frecuencia or "").strip().lower()
    if frecuencia not in FRECUENCIAS:
        frecuencia = "mensual"

    fecha = _now_str()

    if tipo == "abono":
        # abono: frecuencia no aplica
        params = [cliente_id, fecha, "abono", float(monto or 0), float(seguro or 0), 0, 0, None]
    else:
        # prestamo
        params = [cliente_id, fecha, "prestamo", 0, float(seguro or 0), float(monto_entregado or 0), float(interes_mensual or 20), frecuencia]

    if db.db_kind() == "sqlite":
        db.execute("""
            INSERT INTO pagos (cliente_id, fecha, tipo, monto, seguro, monto_entregado, interes_mensual, frecuencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, params)
    else:
        db.execute("""
            INSERT INTO pagos (cliente_id, fecha, tipo, monto, seguro, monto_entregado, interes_mensual, frecuencia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, params)

    return RedirectResponse("/pagos", status_code=303)

@router.post("/pagos/eliminar/{pago_id}")
def eliminar_pago(request: Request, pago_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if db.db_kind() == "sqlite":
        db.execute("DELETE FROM pagos WHERE id = ?", [pago_id])
    else:
        db.execute("DELETE FROM pagos WHERE id = %s", [pago_id])

    return RedirectResponse("/pagos", status_code=303)
