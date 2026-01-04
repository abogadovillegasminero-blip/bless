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
EXPORT_PAGOS_XLSX = f"{DATA_DIR}/reporte_pagos.xlsx"
EXPORT_TODO_XLSX = f"{DATA_DIR}/backup_bless.xlsx"


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


def _fetch_all_clientes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nombre, cedula, telefono, monto, tipo_cobro, created_at
        FROM clientes
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _fetch_all_pagos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, cedula, cliente, fecha, hora, valor, tipo_cobro, registrado_por, created_at
        FROM pagos
        ORDER BY id DESC
    """)
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
    error = request.query_params.get("error") or ""

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
            "error": error,
        },
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
    cols = ["cliente", "cedula", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"]
    df = df[[c for c in cols if c in df.columns]]
    df.to_excel(EXPORT_PAGOS_XLSX, index=False)

    return FileResponse(
        EXPORT_PAGOS_XLSX,
        filename="reporte_pagos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/exportar_todo")
def exportar_todo_excel(request: Request):
    """
    ✅ BACKUP COMPLETO DE LA BD
    Genera un .xlsx con 2 hojas: CLIENTES y PAGOS.
    """
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    os.makedirs(DATA_DIR, exist_ok=True)

    clientes = _fetch_all_clientes()
    pagos = _fetch_all_pagos()

    if not clientes and not pagos:
        return RedirectResponse("/reportes?error=1", status_code=303)

    df_clientes = pd.DataFrame(clientes)
    df_pagos = pd.DataFrame(pagos)

    # Orden sugerido
    if not df_clientes.empty:
        cols_c = ["id", "nombre", "cedula", "telefono", "monto", "tipo_cobro", "created_at"]
        df_clientes = df_clientes[[c for c in cols_c if c in df_clientes.columns]]

    if not df_pagos.empty:
        cols_p = ["id", "cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por", "created_at"]
        df_pagos = df_pagos[[c for c in cols_p if c in df_pagos.columns]]

    with pd.ExcelWriter(EXPORT_TODO_XLSX, engine="openpyxl") as writer:
        df_clientes.to_excel(writer, sheet_name="CLIENTES", index=False)
        df_pagos.to_excel(writer, sheet_name="PAGOS", index=False)

    return FileResponse(
        EXPORT_TODO_XLSX,
        filename="backup_bless.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
