import os
from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
CLIENTES_XLSX = f"{DATA_DIR}/clientes.xlsx"
PAGOS_XLSX = f"{DATA_DIR}/pagos.xlsx"

# ✅ Reglas simples (configurables)
DAILY_TERM_DAYS = 30
WEEKLY_TERM_WEEKS = 12


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
    df["tipo_cobro"] = (
        df["tipo_cobro"]
        .astype(str)
        .replace(["nan", "NaT", "None"], "")
        .str.lower()
        .str.strip()
    )
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

    return df


def _load_pagos():
    if not os.path.exists(PAGOS_XLSX):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "valor", "tipo_cobro", "_fecha_dt"])

    df = pd.read_excel(PAGOS_XLSX)

    # compatibilidad si antes guardaste como "monto"
    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    for col in ["cedula", "cliente", "fecha", "valor", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["cliente"] = df["cliente"].astype(str).replace(["nan", "NaT", "None"], "")
    df["fecha"] = df["fecha"].astype(str).replace(["nan", "NaT", "None"], "")
    df["tipo_cobro"] = (
        df["tipo_cobro"]
        .astype(str)
        .replace(["nan", "NaT", "None"], "")
        .str.lower()
        .str.strip()
    )
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    # parse fecha a date para filtros
    df["_fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date

    return df


def _save_pagos(df: pd.DataFrame):
    # quitar columna auxiliar antes de guardar
    if "_fecha_dt" in df.columns:
        df = df.drop(columns=["_fecha_dt"])
    df.to_excel(PAGOS_XLSX, index=False)


def _start_of_week(d: date) -> date:
    # lunes como inicio de semana
    return d - timedelta(days=d.weekday())


@router.post("/cobros/pago_rapido")
def pago_rapido(
    request: Request,
    cedula: str = Form(...),
    valor: float = Form(...),
    fecha: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cedula = str(cedula).strip()
    fecha = str(fecha).strip()

    # validar cliente existe
    clientes = _load_clientes()
    match = clientes[clientes["cedula"].astype(str) == cedula]
    if match.empty:
        return RedirectResponse("/cobros", status_code=303)

    cliente_nombre = str(match.iloc[0]["nombre"])
    tipo_cobro = str(match.iloc[0]["tipo_cobro"])

    # guardar pago
    pagos_df = _load_pagos()
    nuevo = {
        "cedula": cedula,
        "cliente": cliente_nombre,
        "fecha": fecha,
        "valor": float(valor),
        "tipo_cobro": tipo_cobro,
    }

    # aseguramos que existan columnas mínimas (por compatibilidad)
    for col in ["cedula", "cliente", "fecha", "valor", "tipo_cobro"]:
        if col not in pagos_df.columns:
            pagos_df[col] = ""

    pagos_df = pd.concat([pagos_df.drop(columns=["_fecha_dt"], errors="ignore"), pd.DataFrame([nuevo])], ignore_index=True)
    _save_pagos(pagos_df)

    return RedirectResponse("/cobros", status_code=303)


@router.get("/cobros", response_class=HTMLResponse)
def ver_cobros(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    today = date.today()
    week_start = _start_of_week(today)

    clientes = _load_clientes()
    pagos = _load_pagos()

    # pagos hoy
    pagos_hoy = (
        pagos[pagos["_fecha_dt"] == today]
        .groupby("cedula", as_index=False)["valor"].sum()
        .rename(columns={"valor": "pagado_hoy"})
    )

    # pagos semana actual
    pagos_semana = (
        pagos[
            (pagos["_fecha_dt"].notna())
            & (pagos["_fecha_dt"] >= week_start)
            & (pagos["_fecha_dt"] <= today)
        ]
        .groupby("cedula", as_index=False)["valor"].sum()
        .rename(columns={"valor": "pagado_semana"})
    )

    # pagos total
    pagos_total = (
        pagos.groupby("cedula", as_index=False)["valor"].sum()
        .rename(columns={"valor": "pagado_total"})
    )

    df = (
        clientes
        .merge(pagos_hoy, on="cedula", how="left")
        .merge(pagos_semana, on="cedula", how="left")
        .merge(pagos_total, on="cedula", how="left")
    )

    df["pagado_hoy"] = df["pagado_hoy"].fillna(0)
    df["pagado_semana"] = df["pagado_semana"].fillna(0)
    df["pagado_total"] = df["pagado_total"].fillna(0)

    df["saldo"] = (df["monto"] - df["pagado_total"]).clip(lower=0)

    # cuota sugerida por tipo
    def cuota_sugerida(row):
        tipo = (row.get("tipo_cobro") or "").strip().lower()
        monto = float(row.get("monto") or 0)

        if tipo == "diario":
            return round(monto / DAILY_TERM_DAYS, 2) if DAILY_TERM_DAYS > 0 else 0
        if tipo == "semanal":
            return round(monto / WEEKLY_TERM_WEEKS, 2) if WEEKLY_TERM_WEEKS > 0 else 0
        return 0

    df["cuota_sugerida"] = df.apply(cuota_sugerida, axis=1)

    # debe según tipo
    def debe(row):
        tipo = (row.get("tipo_cobro") or "").strip().lower()
        cuota = float(row.get("cuota_sugerida") or 0)

        if tipo == "diario":
            return max(cuota - float(row.get("pagado_hoy") or 0), 0)
        if tipo == "semanal":
            return max(cuota - float(row.get("pagado_semana") or 0), 0)
        return 0

    df["debe"] = df.apply(debe, axis=1)

    # alerta: saldo>0 y no pagó en el periodo
    def alerta(row):
        tipo = (row.get("tipo_cobro") or "").strip().lower()
        saldo = float(row.get("saldo") or 0)

        if saldo <= 0:
            return False

        if tipo == "diario":
            return float(row.get("pagado_hoy") or 0) <= 0
        if tipo == "semanal":
            return float(row.get("pagado_semana") or 0) <= 0

        return False

    df["alerta"] = df.apply(alerta, axis=1)

    # ordenar: alertas primero
    df = df.sort_values(by=["alerta", "debe", "saldo"], ascending=[False, False, False])

    filas = df.to_dict(orient="records")
    total_alertas = int(df["alerta"].sum()) if "alerta" in df.columns else 0

    return templates.TemplateResponse(
        "cobros.html",
        {
            "request": request,
            "user": user,
            "filas": filas,
            "today": today.isoformat(),
            "week_start": week_start.isoformat(),
            "total_alertas": total_alertas,
        }
    )
