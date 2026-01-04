import os
from datetime import datetime, date

import pandas as pd
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
CLIENTES = f"{DATA_DIR}/clientes.xlsx"
PAGOS = f"{DATA_DIR}/pagos.xlsx"

os.makedirs(DATA_DIR, exist_ok=True)


def _load_clientes():
    if not os.path.exists(CLIENTES):
        return pd.DataFrame(columns=["nombre", "cedula", "telefono", "monto", "tipo_cobro"])
    df = pd.read_excel(CLIENTES)

    for col in ["nombre", "cedula", "telefono", "monto", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["nombre"] = df["nombre"].astype(str).replace(["nan", "NaT", "None"], "")
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "").str.lower().str.strip()
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

    return df


def _load_pagos():
    if not os.path.exists(PAGOS):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "hora", "valor", "tipo_cobro", "registrado_por"])

    df = pd.read_excel(PAGOS)

    # compatibilidad si antes guardaste como "monto"
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

    # ordenar: últimos primero (fecha + hora)
    df["_dt"] = pd.to_datetime(df["fecha"] + " " + df["hora"], errors="coerce")
    df = df.sort_values(by="_dt", ascending=False).drop(columns=["_dt"])

    return df


@router.get("/pagos", response_class=HTMLResponse)
def pagos_form(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes_df = _load_clientes()
    clientes = clientes_df.to_dict(orient="records")

    pagos_df = _load_pagos()

    # filtros por querystring
    solo_hoy = request.query_params.get("hoy")  # "1"
    cedula_filtro = (request.query_params.get("cedula") or "").strip()

    hoy_str = date.today().isoformat()

    if solo_hoy == "1":
        pagos_df = pagos_df[pagos_df["fecha"].astype(str) == hoy_str]

    if cedula_filtro:
        pagos_df = pagos_df[pagos_df["cedula"].astype(str).str.contains(cedula_filtro, na=False)]

    pagos = pagos_df.to_dict(orient="records")

    return templates.TemplateResponse(
        "pagos.html",
        {
            "request": request,
            "clientes": clientes,
            "pagos": pagos,
            "user": user,
            "hoy": hoy_str,
            "solo_hoy": (solo_hoy == "1"),
            "cedula_filtro": cedula_filtro,
        }
    )


@router.post("/pagos/guardar")
def guardar_pago(
    request: Request,
    cedula: str = Form(...),
    valor: float = Form(...),
    fecha: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cedula = str(cedula).strip()

    clientes_df = _load_clientes()
    match = clientes_df[clientes_df["cedula"].astype(str) == cedula]
    if match.empty:
        return RedirectResponse("/pagos", status_code=303)

    cliente_nombre = str(match.iloc[0]["nombre"])
    tipo_cobro = str(match.iloc[0]["tipo_cobro"])

    now = datetime.now()
    hora = now.strftime("%H:%M:%S")
    registrado_por = str(user.get("username") or "")

    nuevo = {
        "cedula": cedula,
        "cliente": cliente_nombre,
        "fecha": str(fecha),
        "hora": hora,
        "valor": float(valor),
        "tipo_cobro": tipo_cobro,
        "registrado_por": registrado_por,
    }

    pagos_df = _load_pagos()
    pagos_df = pd.concat([pagos_df, pd.DataFrame([nuevo])], ignore_index=True)
    pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)


@router.post("/pagos/eliminar")
def eliminar_pago(
    request: Request,
    row_id: int = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pagos_df = _load_pagos()

    if row_id < 0 or row_id >= len(pagos_df):
        return RedirectResponse("/pagos", status_code=303)

    pagos_df = pagos_df.drop(index=row_id).reset_index(drop=True)
    pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)


# =========================
# EDITAR PAGO (GET)
# =========================
@router.get("/pagos/editar/{row_id}", response_class=HTMLResponse)
def editar_pago(request: Request, row_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pagos_df = _load_pagos()

    if row_id < 0 or row_id >= len(pagos_df):
        return RedirectResponse("/pagos", status_code=303)

    row = pagos_df.iloc[row_id].to_dict()
    row["row_id"] = row_id

    return templates.TemplateResponse(
        "pago_editar.html",
        {"request": request, "pago": row, "user": user}
    )


# =========================
# ACTUALIZAR PAGO (POST)
# =========================
@router.post("/pagos/actualizar")
def actualizar_pago(
    request: Request,
    row_id: int = Form(...),
    valor: float = Form(...),
    fecha: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pagos_df = _load_pagos()

    if row_id < 0 or row_id >= len(pagos_df):
        return RedirectResponse("/pagos", status_code=303)

    # Solo actualiza campos permitidos
    pagos_df.at[row_id, "valor"] = float(valor)
    pagos_df.at[row_id, "fecha"] = str(fecha)

    pagos_df.to_excel(PAGOS, index=False)
    return RedirectResponse("/pagos", status_code=303)
