import os
from datetime import date

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_admin
from app.db import get_connection

router = APIRouter(prefix="/reportes", tags=["Reportes"])
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
EXPORT_XLSX = f"{DATA_DIR}/reporte_pagos.xlsx"


def _fetch_pagos(hoy: str, desde: str, hasta: str, cedula: str):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        SELECT
            id, cedula, cliente, fecha, hora, valor, tipo_cobro, registrado_por
        FROM pagos
        WHERE 1=1
    """
    params = []

    if hoy == "1":
        sql += " AND fecha = ?"
        params.append(date.today().isoformat())

    if desde and hasta:
        sql += " AND fecha >= ? AND fecha <= ?"
        params.extend([desde, hasta])

    if cedula:
        sql += " AND cedula LIKE ?"
        params.append(f"%{cedula.strip()}%")

    sql += " ORDER BY id DESC"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def ver_reportes(request: Request):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    hoy = request.query_params.get("hoy") or ""
    desde = (request.query_params.get("desde") or "").strip()
    hasta = (request.query_params.get("hasta") or "").strip()
    cedula = (request.query_params.get("cedula") or "").strip()

    pagos = _fetch_pagos(hoy, desde, hasta, cedula)

    cantidad = len(pagos)
    total = sum(float(p.get("valor", 0) or 0) for p in pagos)

    return templates.TemplateResponse(
        "reportes.html",
        {
            "request": request,
            "user": user,
            "pagos": pagos,
            "cantidad": cantidad,
            "total": total,
            "hoy": hoy,
            "desde": desde,
            "hasta": hasta,
            "cedula": cedula,
        }
    )


@router.get("/exportar")
def exportar_excel(request: Request):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    hoy = request.query_params.get("hoy") or ""
    desde = (request.query_params.get("desde") or "").strip()
    hasta = (request.query_params.get("hasta") or "").strip()
    cedula = (request.query_params.get("cedula") or "").strip()

    pagos = _fetch_pagos(hoy, desde, hasta, cedula)

    if not pagos:
        return RedirectResponse("/reportes?error=1", status_code=303)

    os.makedirs(DATA_DIR, exist_ok=True)

    df = pd.DataFrame(pagos)
    # orden bonito de columnas
    cols = ["cliente", "cedula", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"]
    df = df[[c for c in cols if c in df.columns]]

    df.to_excel(EXPORT_XLSX, index=False)

    return FileResponse(
        EXPORT_XLSX,
        filename="reporte_pagos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
