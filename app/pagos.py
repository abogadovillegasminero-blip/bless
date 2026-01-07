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


def _apply_reglas_negocio(tipo: str, valor: float, nota: str):
    """
    Regla:
    - Préstamo: seguro 10% (una vez), se descuenta del entregado, interés mensual 20%
    - Abono: sin seguro, sin interés
    """
    tipo = (tipo or "abono").strip().lower()
    if tipo not in ("abono", "prestamo"):
        tipo = "abono"

    valor = float(valor or 0)

    seguro = 0.0
    monto_entregado = 0.0
    interes_mensual = 0.0

    if tipo == "prestamo":
        seguro = round(valor * SEGURO, 2)
        monto_entregado = round(valor - seguro, 2)
        interes_mensual = INTERES_MENSUAL

        if not (nota or "").strip():
            nota = f"Préstamo: seguro 10%={seguro} | entregado={monto_entregado} | interés mensual=20%"

    return tipo, round(valor, 2), (nota or "").strip(), seguro, monto_entregado, interes_mensual


@router.post("/crear")
def crear_pago(
    request: Request,
    cliente_id: int = Form(...),
    fecha: str = Form(""),
    valor: float = Form(...),
    nota: str = Form(""),
    tipo: str = Form("abono"),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if not (fecha or "").strip():
        fecha = datetime.utcnow().date().isoformat()

    tipo, valor, nota, seguro, monto_entregado, interes_mensual = _apply_reglas_negocio(tipo, valor, nota)

    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO pagos (cliente_id, fecha, valor, nota, tipo, seguro, monto_entregado, interes_mensual)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cliente_id, fecha.strip(), valor, nota, tipo, seguro, monto_entregado, interes_mensual),
            )
        except sqlite3.OperationalError:
            # fallback si aún no existen columnas (pero con db.py de arriba ya no debería pasar)
            cur.execute(
                "INSERT INTO pagos (cliente_id, fecha, valor, nota) VALUES (?, ?, ?, ?)",
                (cliente_id, fecha.strip(), valor, nota),
            )
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/pagos", status_code=303)


@router.get("/editar/{pago_id}")
def editar_pago_page(request: Request, pago_id: int):
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
              COALESCE(p.tipo, 'abono') AS tipo
            FROM pagos p
            WHERE p.id = ?
        """, (pago_id,))
        pago = cur.fetchone()
    finally:
        conn.close()

    if not pago:
        return RedirectResponse(url="/pagos", status_code=303)

    return templates.TemplateResponse(
        "pago_editar.html",
        {"request": request, "user": user, "clientes": clientes, "pago": pago},
    )


@router.post("/editar/{pago_id}")
def editar_pago(
    request: Request,
    pago_id: int,
    cliente_id: int = Form(...),
    fecha: str = Form(""),
    valor: float = Form(...),
    nota: str = Form(""),
    tipo: str = Form("abono"),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if not (fecha or "").strip():
        fecha = datetime.utcnow().date().isoformat()

    tipo, valor, nota, seguro, monto_entregado, interes_mensual = _apply_reglas_negocio(tipo, valor, nota)

    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE pagos
                SET cliente_id=?, fecha=?, valor=?, nota=?, tipo=?, seguro=?, monto_entregado=?, interes_mensual=?
                WHERE id=?
            """, (cliente_id, fecha.strip(), valor, nota, tipo, seguro, monto_entregado, interes_mensual, pago_id))
        except sqlite3.OperationalError:
            cur.execute("""
                UPDATE pagos
                SET cliente_id=?, fecha=?, valor=?, nota=?
                WHERE id=?
            """, (cliente_id, fecha.strip(), valor, nota, pago_id))

        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/pagos", status_code=303)


# ✅ Eliminar por POST (recomendado)
@router.post("/eliminar")
def eliminar_pago_post(request: Request, pago_id: int = Form(...)):
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


# ✅ Mantengo también el GET por compatibilidad si ya lo usabas
@router.get("/eliminar/{pago_id}")
def eliminar_pago_get(request: Request, pago_id: int):
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
