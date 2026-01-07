# app/saldos.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user
from app.db import get_connection

router = APIRouter(prefix="/saldos", tags=["saldos"])
templates = Jinja2Templates(directory="templates")


@router.get("")
def ver_saldos(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        # Total pagos por cliente (si no hay pagos => 0)
        cur.execute("""
            SELECT
                c.id,
                c.nombre,
                c.documento,
                c.telefono,
                COALESCE(SUM(p.valor), 0) AS total_pagado,
                COUNT(p.id) AS n_pagos
            FROM clientes c
            LEFT JOIN pagos p ON p.cliente_id = c.id
            GROUP BY c.id
            ORDER BY c.id DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse(
        "saldos.html",
        {"request": request, "user": user, "rows": rows},
    )
