import os
from datetime import date

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_admin

router = APIRouter(prefix="/reportes", tags=["Reportes"])
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
PAGOS_XLSX = f"{DATA_DIR}/pagos.xlsx"
EXPORT_XLSX = f"{DATA_DIR}/reporte_pagos.xlsx"


def _load_pagos():
    if not os.path.exists(PAGOS_XLSX):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"])

    df = pd.read_excel(PAGOS_XLSX)

    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    for col in ["cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["cliente"] = df["cliente"].astype(str).replace(["nan", "NaT", "None"], "")
    df["fecha"] = df["fecha"].astype(str).replace(["nan", "NaT", "None"], "")
    df["hora"] = df["hora"].astype(str).replace(["nan", "NaT", "None"], "")
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "").str.lower().str.strip()
    df["registrado_por"] = df["registrado_por"].astype(str).replace(["nan", "NaT", "None"], "")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    df["_dt"] = pd.to_datetime(df["fecha"] + " " + df["hora"], errors="coerce")
    df = df.sort_values(by="_dt", ascending=False)

    return df


def _apply_filters(df: pd.DataFrame, hoy: str, desde: str, hasta: str, cedula: str):
    # hoy = "1" para filtrar por fecha actual
    if hoy == "1":
        hoy_str = date.today().isoformat()
        df = df[df["fecha"].astype(str) == hoy_str]

    # rango (si vienen ambos)
    if desde and hasta:
        df["_fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
        d1 = pd.to_datetime(desde, errors="coerce").date() if desde else None
        d2 = pd.to_datetime(hasta, errors="coerce").date() if hasta else None
        if d1 and d2:
            df = df[(df["_fecha_dt"] >= d1) & (df["_fecha_dt"] <= d2)]
        df = df.drop(columns=["_fecha_dt"], errors="ignore")

    # cédula
    if cedula:
        cedula = str(cedula).strip()
        df = df[df["cedula"].astype(str).str.contains(cedula, na=False)]

    return df


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

    df = _load_pagos()
    df_f = _apply_filters(df.copy(), hoy, desde, hasta, cedula)

    pagos = df_f.drop(columns=["_dt"], errors="ignore").to_dict(orient="records")

    total = float(df_f["valor"].sum()) if "valor" in df_f.columns else 0.0
    cantidad = int(len(df_f))

    return templates.TemplateResponse(
        "reportes.html",
        {
            "request": request,
            "user": user,
            "pagos": pagos,
            "total": total,
            "cantidad": cantidad,
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

    df = _load_pagos()
    df_f = _apply_filters(df.copy(), hoy, desde, hasta, cedula)

    if df_f.empty:
        return RedirectResponse("/reportes?error=1", status_code=303)

    df_export = df_f.drop(columns=["_dt"], errors="ignore")
    df_export.to_excel(EXPORT_XLSX, index=False)

    return FileResponse(
        EXPORT_XLSX,
        filename="reporte_pagos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
