# app/pagos.py
from datetime import datetime
import sqlite3

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user
from app.db import get_connection

router = APIRouter(prefix="/pagos", tags=["pagos"])
templates = Jinja2Templates(directory="templates")

INTERES_MENSUAL = 0.20
SEGURO = 0.10


@router.get("")
def pagos_page(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre ASC")
        clientes = cur.fetchall()

        cur.execute("""
            SELECT
              p.id, p.cliente_id, p.fecha, p.valor, p.nota,
              COALESCE(p.tipo, 'abono') AS tipo,
              COALESCE(p.seguro, 0) AS seguro,
              COALESCE(p.monto_entregado, 0) AS monto_entregado,
              COALESCE(p.interes_mensual, 0) AS interes_mensual,
              c.nombre AS cliente_nombre
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
    tipo: str = Form("abono"),  # 'abono' o 'prestamo'
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    tipo = (tipo or "abono").strip().lower()
    if tipo not in ("abono", "prestamo"):
        tipo = "abono"

    if not (fecha or "").strip():
        fecha = datetime.utcnow().date().isoformat()

    valor = float(valor or 0)

    seguro = 0.0
    monto_entregado = 0.0
    interes_mensual = 0.0

    # ✅ Reglas del negocio (tal como pediste)
    if tipo == "prestamo":
        seguro = round(valor * SEGURO, 2)                 # 10% una sola vez
        monto_entregado = round(valor - seguro, 2)        # se descuenta del dinero entregado
        interes_mensual = INTERES_MENSUAL                 # 20% mensual

        # Si no ponen nota, dejamos evidencia automática
        if not (nota or "").strip():
            nota = f"Préstamo: seguro 10%={seguro} | entregado={monto_entregado} | interés mensual=20%"

    conn = get_connection()
    try:
        cur = conn.cursor()

        # ✅ Insert con columnas nuevas (si existen)
        try:
            cur.execute(
                """
                INSERT INTO pagos (cliente_id, fecha, valor, nota, tipo, seguro, monto_entregado, interes_mensual)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cliente_id,
                    fecha.strip(),
                    round(valor, 2),
                    (nota or "").strip(),
                    tipo,
                    seguro,
                    monto_entregado,
                    interes_mensual,
                ),
            )
        except sqlite3.OperationalError:
            # ✅ Fallback si por alguna razón aún no están las columnas
            cur.execute(
                """
                INSERT INTO pagos (cliente_id, fecha, valor, nota)
                VALUES (?, ?, ?, ?)
                """,
                (
                    cliente_id,
                    fecha.strip(),
                    round(valor, 2),
                    (nota or "").strip(),
                ),
            )

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
