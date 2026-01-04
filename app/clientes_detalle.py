import os
import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CLIENTES_XLSX = "data/clientes.xlsx"
PAGOS_XLSX = "data/pagos.xlsx"


def _load_clientes():
    if not os.path.exists(CLIENTES_XLSX):
        return pd.DataFrame(columns=["nombre", "cedula", "telefono", "monto", "tipo_cobro"])

    df = pd.read_excel(CLIENTES_XLSX)
    for col in ["nombre", "cedula", "telefono", "monto", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["nombre"] = df["nombre"].astype(str).replace(["nan", "NaT", "None"], "")
    df["telefono"] = df["telefono"].astype(str).replace(["nan", "NaT", "None"], "")
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    return df


def _load_pagos():
    if not os.path.exists(PAGOS_XLSX):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "valor", "tipo_cobro"])

    df = pd.read_excel(PAGOS_XLSX)

    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    for col in ["cedula", "cliente", "fecha", "valor", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["cliente"] = df["cliente"].astype(str).replace(["nan", "NaT", "None"], "")
    df["fecha"] = df["fecha"].astype(str).replace(["nan", "NaT", "None"], "")
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    return df


@router.get("/clientes/ver", response_class=HTMLResponse)
def ver_cliente(request: Request, cedula: str):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cedula = str(cedula).strip()

    clientes_df = _load_clientes()
    match = clientes_df[clientes_df["cedula"].astype(str) == cedula]

    if match.empty:
        return RedirectResponse("/clientes", status_code=303)

    c = match.iloc[0].to_dict()

    pagos_df = _load_pagos()
    pagos_cliente = pagos_df[pagos_df["cedula"].astype(str) == cedula].copy()

    # Ordenar pagos por fecha desc
    try:
        pagos_cliente["_fecha_dt"] = pd.to_datetime(pagos_cliente["fecha"], errors="coerce")
        pagos_cliente = pagos_cliente.sort_values(by="_fecha_dt", ascending=False).drop(columns=["_fecha_dt"])
    except Exception:
        pass

    total_pagado = float(pagos_cliente["valor"].sum()) if not pagos_cliente.empty else 0.0
    prestamo = float(c.get("monto", 0) or 0)
    saldo = prestamo - total_pagado

    resumen = {
        "nombre": str(c.get("nombre", "")),
        "cedula": cedula,
        "telefono": str(c.get("telefono", "")),
        "tipo_cobro": str(c.get("tipo_cobro", "")),
        "prestamo": prestamo,
        "pagado": total_pagado,
        "saldo": saldo,
    }

    pagos = pagos_cliente.to_dict(orient="records")

    return templates.TemplateResponse(
        "cliente_ver.html",
        {"request": request, "user": user, "cliente": resumen, "pagos": pagos}
    )
