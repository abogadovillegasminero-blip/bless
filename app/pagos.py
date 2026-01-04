import os
from datetime import datetime

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
    return df


@router.get("/pagos", response_class=HTMLResponse)
def pagos_form(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes_df = _load_clientes()
    clientes = clientes_df.to_dict(orient="records")

    pagos_df = _load_pagos()
    pagos = pagos_df.to_dict(orient="records")

    return templates.TemplateResponse(
        "pagos.html",
        {"request": request, "clientes": clientes, "pagos": pagos, "user": user}
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

    cedula = str(cedula)

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
