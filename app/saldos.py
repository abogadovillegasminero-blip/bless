import os
import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter(prefix="/saldos", tags=["Saldos"])
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
CLIENTES_XLSX = f"{DATA_DIR}/clientes.xlsx"
PAGOS_XLSX = f"{DATA_DIR}/pagos.xlsx"


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
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "").str.lower().str.strip()
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

    return df


def _load_pagos():
    if not os.path.exists(PAGOS_XLSX):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"])

    df = pd.read_excel(PAGOS_XLSX)

    # compatibilidad si antes guardaste como "monto"
    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    for col in ["cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["fecha"] = df["fecha"].astype(str).replace(["nan", "NaT", "None"], "")
    df["hora"] = df["hora"].astype(str).replace(["nan", "NaT", "None"], "")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    df["_dt"] = pd.to_datetime(df["fecha"] + " " + df["hora"], errors="coerce")
    return df


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def ver_saldos(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes = _load_clientes()
    pagos = _load_pagos()

    if clientes.empty:
        filas = []
        totales = {"prestado": 0.0, "pagado": 0.0, "saldo": 0.0}
        return templates.TemplateResponse(
            "saldos.html",
            {"request": request, "user": user, "filas": filas, "totales": totales}
        )

    # total pagado por cédula
    pagos_sum = (
        pagos.groupby("cedula", as_index=False)["valor"].sum()
        .rename(columns={"valor": "pagado_total"})
    )

    # último pago por cédula
    pagos_last = (
        pagos.sort_values(by="_dt", ascending=False)
        .groupby("cedula", as_index=False)
        .first()[["cedula", "fecha"]]
        .rename(columns={"fecha": "ultimo_pago"})
    )

    df = clientes.merge(pagos_sum, on="cedula", how="left").merge(pagos_last, on="cedula", how="left")
    df["pagado_total"] = df["pagado_total"].fillna(0)
    df["ultimo_pago"] = df["ultimo_pago"].fillna("")

    df["saldo"] = (df["monto"] - df["pagado_total"]).clip(lower=0)

    # orden: mayor saldo primero
    df = df.sort_values(by=["saldo"], ascending=False).reset_index(drop=True)

    filas = df.to_dict(orient="records")

    totales = {
        "prestado": float(df["monto"].sum()) if "monto" in df.columns else 0.0,
        "pagado": float(df["pagado_total"].sum()) if "pagado_total" in df.columns else 0.0,
        "saldo": float(df["saldo"].sum()) if "saldo" in df.columns else 0.0,
    }

    return templates.TemplateResponse(
        "saldos.html",
        {"request": request, "user": user, "filas": filas, "totales": totales}
    )
