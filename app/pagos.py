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

    df["cedula"] = df["cedula"].astype(str)
    df["nombre"] = df["nombre"].astype(str).replace(["nan", "NaT", "None"], "")
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    return df


def _load_pagos():
    if not os.path.exists(PAGOS):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "valor", "tipo_cobro"])

    df = pd.read_excel(PAGOS)

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


def _save_pagos(df: pd.DataFrame):
    df.to_excel(PAGOS, index=False)


@router.get("/pagos", response_class=HTMLResponse)
def pagos_form(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pre_cedula = (request.query_params.get("cedula") or "").strip()

    clientes_df = _load_clientes()
    clientes = clientes_df.to_dict(orient="records")

    pagos_df = _load_pagos()
    try:
        pagos_df["_fecha_dt"] = pd.to_datetime(pagos_df["fecha"], errors="coerce")
        pagos_df = pagos_df.sort_values(by="_fecha_dt", ascending=False).drop(columns=["_fecha_dt"])
    except Exception:
        pass

    pagos = pagos_df.to_dict(orient="records")

    return templates.TemplateResponse(
        "pagos.html",
        {
            "request": request,
            "clientes": clientes,
            "pagos": pagos,
            "user": user,
            "pre_cedula": pre_cedula,
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

    clientes_df = _load_clientes()
    cedula = str(cedula)

    match = clientes_df[clientes_df["cedula"].astype(str) == cedula]
    if match.empty:
        return RedirectResponse("/pagos", status_code=303)

    cliente_nombre = str(match.iloc[0]["nombre"])
    tipo_cobro = str(match.iloc[0]["tipo_cobro"])

    nuevo = {
        "cedula": cedula,
        "cliente": cliente_nombre,
        "fecha": str(fecha),
        "valor": float(valor),
        "tipo_cobro": tipo_cobro,
    }

    pagos_df = _load_pagos()
    pagos_df = pd.concat([pagos_df, pd.DataFrame([nuevo])], ignore_index=True)
    _save_pagos(pagos_df)

    return RedirectResponse(f"/pagos?cedula={cedula}", status_code=303)


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
    _save_pagos(pagos_df)

    return RedirectResponse("/pagos", status_code=303)


@router.get("/pagos/editar", response_class=HTMLResponse)
def editar_pago(request: Request, row_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pagos_df = _load_pagos()
    if row_id < 0 or row_id >= len(pagos_df):
        return RedirectResponse("/pagos", status_code=303)

    row = pagos_df.iloc[row_id].to_dict()

    fecha = str(row.get("fecha", ""))
    if fecha in ["nan", "NaT", "None"]:
        fecha = ""

    pago = {
        "row_id": row_id,
        "cliente": str(row.get("cliente", "")),
        "cedula": str(row.get("cedula", "")),
        "fecha": fecha,
        "valor": float(row.get("valor", 0)),
        "tipo_cobro": str(row.get("tipo_cobro", "")),
    }

    clientes_df = _load_clientes()
    clientes = clientes_df.to_dict(orient="records")

    return templates.TemplateResponse(
        "pagos_editar.html",
        {"request": request, "pago": pago, "clientes": clientes, "user": user}
    )


@router.post("/pagos/actualizar")
def actualizar_pago(
    request: Request,
    row_id: int = Form(...),
    cedula: str = Form(...),          # ✅ ahora se puede cambiar cliente
    valor: float = Form(...),
    fecha: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pagos_df = _load_pagos()
    if row_id < 0 or row_id >= len(pagos_df):
        return RedirectResponse("/pagos", status_code=303)

    clientes_df = _load_clientes()
    cedula = str(cedula)

    match = clientes_df[clientes_df["cedula"].astype(str) == cedula]
    if match.empty:
        return RedirectResponse("/pagos", status_code=303)

    cliente_nombre = str(match.iloc[0]["nombre"])
    tipo_cobro = str(match.iloc[0]["tipo_cobro"])

    pagos_df.loc[row_id, "cedula"] = cedula
    pagos_df.loc[row_id, "cliente"] = cliente_nombre
    pagos_df.loc[row_id, "tipo_cobro"] = tipo_cobro
    pagos_df.loc[row_id, "valor"] = float(valor)
    pagos_df.loc[row_id, "fecha"] = str(fecha)

    _save_pagos(pagos_df)

    return RedirectResponse("/pagos", status_code=303)
