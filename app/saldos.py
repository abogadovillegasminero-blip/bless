from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user
from app.db import get_connection

router = APIRouter(prefix="/saldos", tags=["Saldos"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def ver_saldos(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    cur = conn.cursor()

    # clientes + total pagado + último pago
    cur.execute("""
        SELECT
            c.id,
            c.nombre,
            c.cedula,
            c.telefono,
            c.monto,
            c.tipo_cobro,

            COALESCE(SUM(p.valor), 0) AS pagado_total,
            COALESCE(MAX(p.fecha), '') AS ultimo_pago

        FROM clientes c
        LEFT JOIN pagos p ON p.cedula = c.cedula
        GROUP BY c.id, c.nombre, c.cedula, c.telefono, c.monto, c.tipo_cobro
        ORDER BY (c.monto - COALESCE(SUM(p.valor), 0)) DESC
    """)

    rows = cur.fetchall()
    conn.close()

    filas = []
    total_prestado = 0.0
    total_pagado = 0.0
    total_saldo = 0.0

    for r in rows:
        monto = float(r["monto"] or 0)
        pagado = float(r["pagado_total"] or 0)
        saldo = monto - pagado
        if saldo < 0:
            saldo = 0.0

        total_prestado += monto
        total_pagado += pagado
        total_saldo += saldo

        filas.append({
            "id": r["id"],
            "nombre": r["nombre"],
            "cedula": r["cedula"],
            "telefono": r["telefono"],
            "monto": monto,
            "tipo_cobro": r["tipo_cobro"],
            "pagado_total": pagado,
            "saldo": saldo,
            "ultimo_pago": r["ultimo_pago"] or "",
        })

    totales = {
        "prestado": total_prestado,
        "pagado": total_pagado,
        "saldo": total_saldo,
    }

    return templates.TemplateResponse(
        "saldos.html",
        {"request": request, "user": user, "filas": filas, "totales": totales}
    )
