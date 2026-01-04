import os
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

    df["cedula"] = df["cedula"].fillna("").astype(str)
    df["nombre"] = df["nombre"].fillna("").astype(str)
    df["telefono"] = df["telefono"].fillna("").astype(str)
    df["tipo_cobro"] = df["tipo_cobro"].fillna("").astype(str)

    return df


def _load_pagos():
    if not os.path.exists(PAGOS):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "valor", "tipo_cobro"])

    df = pd.read_excel(PAGOS)

    # Compatibilidad: si antes guardaste como "monto"
    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    for col in ["cedula", "cliente", "fecha", "valor", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].fillna("").astype(str)
    df["cliente"] = df["cliente"].fillna("").astype(str)
    df["fecha"] = df["fecha"].fillna("").astype(str)
    df["tipo_cobro"] = df["tipo_cobro"].fillna("").astype(str)

    # valor numérico
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

    # Agrega row_id para poder borrar por fila
    pagos = []
    for idx, row in pagos_df.iterrows():
        item = row.to_dict()
        item["row_id"] = int(idx)
        pagos.append(item)

    ok = request.query_params.get("ok")
    error = request.query_params.get("error")

    return templates.TemplateResponse(
        "pagos.html",
        {"request": request, "clientes": clientes, "pagos": pagos, "user": user, "ok": ok, "error": error}
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
        return RedirectResponse("/pagos?error=cliente", status_code=303)

    cliente_nombre = str(match.iloc[0]["nombre"])
    tipo_cobro = str(match.iloc[0]["tipo_cobro"])

    nuevo = {
        "cedula": cedula,
        "cliente": cliente_nombre,
        "fecha": fecha,
        "valor": float(valor),
        "tipo_cobro": tipo_cobro,
    }

    pagos_df = _load_pagos()
    pagos_df = pd.concat([pagos_df, pd.DataFrame([nuevo])], ignore_index=True)
    pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos?ok=1", status_code=303)


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
        return RedirectResponse("/pagos?error=no_existe", status_code=303)

    pagos_df = pagos_df.drop(index=row_id).reset_index(drop=True)
    pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos?ok=deleted", status_code=303)
