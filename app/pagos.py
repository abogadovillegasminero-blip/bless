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
    return df


def _load_pagos():
    if not os.path.exists(PAGOS):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "valor", "tipo_cobro"])
    df = pd.read_excel(PAGOS)

    # Compatibilidad por si guardaste antes como "monto"
    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    for col in ["cedula", "cliente", "fecha", "valor", "tipo_cobro"]:
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

    # ✅ ID estable por fila para poder borrar: row_id = índice
    pagos_df = pagos_df.reset_index().rename(columns={"index": "row_id"})

    # ordenar recientes primero (si quieres)
    if "fecha" in pagos_df.columns:
        try:
            pagos_df["fecha"] = pd.to_datetime(pagos_df["fecha"], errors="coerce")
            pagos_df = pagos_df.sort_values(by="fecha", ascending=False)
            pagos_df["fecha"] = pagos_df["fecha"].dt.strftime("%Y-%m-%d")
        except Exception:
            pass

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
        "cedula": cedula,
        "cliente": cliente_nombre,
        "fecha": fecha,
        "valor": float(valor),
        "tipo_cobro": tipo_cobro,
    }

    pagos_df = _load_pagos()
    pagos_df = pd.concat([pagos_df, pd.DataFrame([nuevo])], ignore_index=True)
    pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)


@router.post("/pagos/eliminar")
def eliminar_pago(request: Request, row_id: int = Form(...)):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if not os.path.exists(PAGOS):
        return RedirectResponse("/pagos", status_code=303)

    df = _load_pagos()

    # 🔒 borrar por índice (row_id)
    if row_id < 0 or row_id >= len(df):
        return RedirectResponse("/pagos", status_code=303)

    df = df.drop(index=row_id).reset_index(drop=True)
    df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)
