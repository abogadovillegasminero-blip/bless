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
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    return df


def _load_pagos():
    if not os.path.exists(PAGOS_XLSX):
        return pd.DataFrame(columns=["cedula", "valor"])

    df = pd.read_excel(PAGOS_XLSX)

    # Compatibilidad si alguna vez guardaste como "monto"
    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    for col in ["cedula", "valor"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    return df


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes = _load_clientes()
    pagos = _load_pagos()

    total_clientes = int(len(clientes))

    total_prestado = float(clientes["monto"].sum()) if not clientes.empty else 0.0

    pagos_sum = pagos.groupby("cedula", as_index=False)["valor"].sum()
    pagos_sum.rename(columns={"valor": "pagado"}, inplace=True)

    if clientes.empty:
        df = pd.DataFrame(columns=["nombre", "cedula", "monto", "pagado", "saldo", "tipo_cobro"])
    else:
        df = clientes.merge(pagos_sum, on="cedula", how="left")
        df["pagado"] = df["pagado"].fillna(0)
        df["saldo"] = df["monto"] - df["pagado"]

    total_pagado = float(df["pagado"].sum()) if not df.empty else 0.0
    total_saldo = float(df["saldo"].sum()) if not df.empty else 0.0

    # Top 10 con más saldo
    top = df.sort_values(by="saldo", ascending=False).head(10).to_dict(orient="records")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "total_clientes": total_clientes,
            "total_prestado": total_prestado,
            "total_pagado": total_pagado,
            "total_saldo": total_saldo,
            "top": top,
        }
    )
