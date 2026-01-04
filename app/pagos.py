import os
import uuid
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

    df["cedula"] = df["cedula"].astype(str).fillna("")
    return df


def _load_pagos():
    if not os.path.exists(PAGOS):
        return pd.DataFrame(columns=["id", "cedula", "cliente", "fecha", "valor", "tipo_cobro"])

    df = pd.read_excel(PAGOS)

    # Compatibilidad por si guardaste antes como "monto"
    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    # Asegura columnas
    for col in ["id", "cedula", "cliente", "fecha", "valor", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    # Limpieza para evitar 'nan'
    df["id"] = df["id"].astype(str).fillna("")
    df["cedula"] = df["cedula"].astype(str).fillna("")
    df["cliente"] = df["cliente"].astype(str).fillna("")
    df["fecha"] = df["fecha"].astype(str).fillna("")
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).fillna("")

    # Valor numérico seguro
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    return df


@router.get("/pagos", response_class=HTMLResponse)
def pagos_form(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes_df = _load_clientes()
    clientes = clientes_df.to_dict(orient="records")

    pagos_df = _load_pagos()

    # Orden: último primero (por si fecha viene como string, se ordena "lo mejor posible")
    pagos_df = pagos_df.iloc[::-1].reset_index(drop=True)

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

    clientes_df = _load_clientes()
    cedula = str(cedula)

    match = clientes_df[clientes_df["cedula"].astype(str) == cedula]
    if match.empty:
        return RedirectResponse("/pagos", status_code=303)

    cliente_nombre = str(match.iloc[0]["nombre"])
    tipo_cobro = str(match.iloc[0]["tipo_cobro"])

    nuevo = {
        "id": str(uuid.uuid4()),
        "cedula": cedula,
        "cliente": cliente_nombre,
        "fecha": str(fecha),
        "valor": float(valor),
        "tipo_cobro": tipo_cobro,
    }

    pagos_df = _load_pagos()

    # Importante: guardamos en el orden real (append al final)
    pagos_df = pd.concat([pagos_df, pd.DataFrame([nuevo])], ignore_index=True)
    pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)


@router.post("/pagos/eliminar")
def eliminar_pago(
    request: Request,
    pago_id: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pagos_df = _load_pagos()

    pago_id = str(pago_id)
    if not pago_id:
        return RedirectResponse("/pagos", status_code=303)

    # Filtra por id exacto
    pagos_df = pagos_df[pagos_df["id"].astype(str) != pago_id].reset_index(drop=True)
    pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)
