import os
from datetime import date, timedelta, datetime

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
NO_COBRAR_XLSX = f"{DATA_DIR}/no_cobrar_hoy.xlsx"

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
        return pd.DataFrame(columns=[
            "cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por", "_fecha_dt"
        ])

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
    df["tipo_cobro"] = (
        df["tipo_cobro"]
        .astype(str)
        .replace(["nan", "NaT", "None"], "")
        .str.lower()
        .str.strip()
    )
    df["registrado_por"] = df["registrado_por"].astype(str).replace(["nan", "NaT", "None"], "")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    df["_fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date

    return df


def _save_pagos(df: pd.DataFrame):
    if "_fecha_dt" in df.columns:
        df = df.drop(columns=["_fecha_dt"])
    df.to_excel(PAGOS_XLSX, index=False)


def _start_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _load_no_cobrar():
    if not os.path.exists(NO_COBRAR_XLSX):
        return pd.DataFrame(columns=["cedula", "fecha", "hora", "registrado_por"])

    df = pd.read_excel(NO_COBRAR_XLSX)

    for col in ["cedula", "fecha", "hora", "registrado_por"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["fecha"] = df["fecha"].astype(str).replace(["nan", "NaT", "None"], "")
    df["hora"] = df["hora"].astype(str).replace(["nan", "NaT", "None"], "")
    df["registrado_por"] = df["registrado_por"].astype(str).replace(["nan", "NaT", "None"], "")

    return df


def _save_no_cobrar(df: pd.DataFrame):
    df.to_excel(NO_COBRAR_XLSX, index=False)


def _saldo_actual(cedula: str) -> float:
    cedula = str(cedula).strip()

    clientes = _load_clientes()
    match = clientes[clientes["cedula"].astype(str) == cedula]
    if match.empty:
        return 0.0

    monto = float(match.iloc[0].get("monto") or 0)

    pagos = _load_pagos()
    pagos_cliente = pagos[pagos["cedula"].astype(str) == cedula]
    pagado_total = float(pagos_cliente["valor"].sum()) if not pagos_cliente.empty else 0.0

    saldo = monto - pagado_total
    if saldo < 0:
        saldo = 0.0
    return float(saldo)


# =========================
# NO COBRAR HOY (AGREGAR)
# =========================
@router.post("/cobros/no_cobrar_hoy")
def no_cobrar_hoy(
    request: Request,
    cedula: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cedula = str(cedula).strip()
    hoy = date.today().isoformat()

    now = datetime.now()
    hora = now.strftime("%H:%M:%S")
    registrado_por = str(user.get("username") or "")

    df = _load_no_cobrar()

    ya = df[
        (df["cedula"].astype(str) == cedula) &
        (df["fecha"].astype(str) == hoy)
    ]
    if not ya.empty:
        return RedirectResponse("/cobros", status_code=303)

    nuevo = {
        "cedula": cedula,
        "fecha": hoy,
        "hora": hora,
        "registrado_por": registrado_por,
    }

    df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
    _save_no_cobrar(df)

    return RedirectResponse("/cobros", status_code=303)


# =========================
# DESHACER NO COBRAR HOY (ELIMINAR)
# =========================
@router.post("/cobros/deshacer_no_cobrar_hoy")
def deshacer_no_cobrar_hoy(
    request: Request,
    cedula: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cedula = str(cedula).strip()
    hoy = date.today().isoformat()

    df = _load_no_cobrar()

    before = len(df)
    df = df[~((df["cedula"].astype(str) == cedula) & (df["fecha"].astype(str) == hoy))]

    if len(df) != before:
        _save_no_cobrar(df)

    return RedirectResponse("/cobros", status_code=303)


# =========================
# PAGO RÁPIDO (HOY)
# =========================
@router.post("/cobros/pago_rapido")
def pago_rapido(
    request: Request,
    cedula: str = Form(...),
    valor: float = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cedula = str(cedula).strip()

    now = datetime.now()
    fecha_hoy = now.date().isoformat()
    hora = now.strftime("%H:%M:%S")
    registrado_por = str(user.get("username") or "")

    clientes = _load_clientes()
    match = clientes[clientes["cedula"].astype(str) == cedula]
    if match.empty:
        return RedirectResponse("/cobros", status_code=303)

    saldo = _saldo_actual(cedula)
    if saldo <= 0:
        return RedirectResponse("/cobros", status_code=303)

    valor_num = float(valor or 0)
    if valor_num <= 0:
        return RedirectResponse("/cobros", status_code=303)

    if valor_num > saldo:
        valor_num = saldo

    cliente_nombre = str(match.iloc[0]["nombre"])
    tipo_cobro = str(match.iloc[0]["tipo_cobro"])

    pagos_df = _load_pagos()

    nuevo = {
        "cedula": cedula,
        "cliente": cliente_nombre,
        "fecha": fecha_hoy,
        "hora": hora,
        "valor": float(valor_num),
        "tipo_cobro": tipo_cobro,
        "registrado_por": registrado_por,
    }

    for col in ["cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"]:
        if col not in pagos_df.columns:
            pagos_df[col] = ""

    pagos_df = pd.concat(
        [pagos_df.drop(columns=["_fecha_dt"], errors="ignore"), pd.DataFrame([nuevo])],
        ignore_index=True
    )
    _save_pagos(pagos_df)

    return RedirectResponse("/cobros", status_code=303)


# =========================
# PANTALLA COBROS
# =========================
@router.get("/cobros", response_class=HTMLResponse)
def ver_cobros(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    today = date.today()
    today_str = today.isoformat()
    week_start = _start_of_week(today)

    clientes = _load_clientes()
    pagos = _load_pagos()

    no_cobrar_df = _load_no_cobrar()
    omitidos_hoy = set(
        no_cobrar_df[no_cobrar_df["fecha"].astype(str) == today_str]["cedula"].astype(str).tolist()
    )

    pagos_hoy = (
        pagos[pagos["_fecha_dt"] == today]
        .groupby("cedula", as_index=False)["valor"].sum()
        .rename(columns={"valor": "pagado_hoy"})
    )

    pagos_semana = (
        pagos[
            (pagos["_fecha_dt"].notna())
            & (pagos["_fecha_dt"] >= week_start)
            & (pagos["_fecha_dt"] <= today)
        ]
        .groupby("cedula", as_index=False)["valor"].sum()
        .rename(columns={"valor": "pagado_semana"})
    )

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

    def cuota_sugerida(row):
        tipo = (row.get("tipo_cobro") or "").strip().lower()
        monto = float(row.get("monto") or 0)
        if tipo == "diario":
            return round(monto / DAILY_TERM_DAYS, 2) if DAILY_TERM_DAYS > 0 else 0
        if tipo == "semanal":
            return round(monto / WEEKLY_TERM_WEEKS, 2) if WEEKLY_TERM_WEEKS > 0 else 0
        return 0

    df["cuota_sugerida"] = df.apply(cuota_sugerida, axis=1)

    def debe(row):
        tipo = (row.get("tipo_cobro") or "").strip().lower()
        cuota = float(row.get("cuota_sugerida") or 0)
        if tipo == "diario":
            return max(cuota - float(row.get("pagado_hoy") or 0), 0)
        if tipo == "semanal":
            return max(cuota - float(row.get("pagado_semana") or 0), 0)
        return 0

    df["debe"] = df.apply(debe, axis=1)

    df["omitido_hoy"] = df["cedula"].astype(str).isin(omitidos_hoy)

    def alerta(row):
        ced = str(row.get("cedula") or "")
        if ced in omitidos_hoy:
            return False

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

    df["valor_sugerido"] = df.apply(
        lambda r: min(float(r.get("debe") or 0), float(r.get("saldo") or 0)),
        axis=1
    )

    total_alertas = int(df["alerta"].sum()) if "alerta" in df.columns else 0

    df = df.sort_values(by=["alerta", "omitido_hoy", "debe", "saldo"], ascending=[False, True, False, False])

    filas = df.to_dict(orient="records")

    return templates.TemplateResponse(
        "cobros.html",
        {
            "request": request,
            "user": user,
            "filas": filas,
            "today": today_str,
            "week_start": week_start.isoformat(),
            "total_alertas": total_alertas,
        }
    )
