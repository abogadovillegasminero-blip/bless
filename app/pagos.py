# app/pagos.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

from app import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

FRECUENCIAS = ["diario", "semanal", "quincenal", "mensual"]


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@router.get("/pagos")
def pagos_home(request: Request):
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
        LIMIT 30
    """)

    resp = templates.TemplateResponse(
        "pagos.html",
        {
            "request": request,
            "clientes": clientes,
            "movimientos": movimientos,
            "frecuencias": FRECUENCIAS,
        },
    )

    # Anti-cache (especialmente útil si hay service worker / PWA)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@router.post("/pagos/crear")
def crear_pago(
    request: Request,
    cliente_id: int = Form(...),
    tipo: str = Form(...),  # "abono" o "prestamo"
    monto: float = Form(0),  # abono
    seguro: float = Form(0),
    monto_entregado: float = Form(0),  # prestamo
    interes_mensual: float = Form(20),
    frecuencia: str = Form("mensual"),
):
    tipo = (tipo or "").strip().lower()

    frecuencia = (frecuencia or "").strip().lower()
    if frecuencia not in FRECUENCIAS:
        frecuencia = "mensual"

    if tipo == "abono":
        frecuencia_db = None
        monto_entregado_db = 0
        interes_mensual_db = 0
        monto_db = float(monto or 0)
    else:
        tipo = "prestamo"
        frecuencia_db = frecuencia
        monto_entregado_db = float(monto_entregado or 0)
        interes_mensual_db = float(interes_mensual or 20)
        monto_db = 0

    seguro_db = float(seguro or 0)
    fecha = _now_str()

    if db.db_kind() == "sqlite":
        db.execute("""
            INSERT INTO pagos (cliente_id, fecha, tipo, monto, seguro, monto_entregado, interes_mensual, frecuencia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [cliente_id, fecha, tipo, monto_db, seguro_db, monto_entregado_db, interes_mensual_db, frecuencia_db])
    else:
        db.execute("""
            INSERT INTO pagos (cliente_id, fecha, tipo, monto, seguro, monto_entregado, interes_mensual, frecuencia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, [cliente_id, fecha, tipo, monto_db, seguro_db, monto_entregado_db, interes_mensual_db, frecuencia_db])

    return RedirectResponse("/pagos", status_code=303)


@router.post("/pagos/eliminar/{pago_id}")
def eliminar_pago(pago_id: int):
    if db.db_kind() == "sqlite":
        db.execute("DELETE FROM pagos WHERE id = ?", [pago_id])
    else:
        db.execute("DELETE FROM pagos WHERE id = %s", [pago_id])

    return RedirectResponse("/pagos", status_code=303)
