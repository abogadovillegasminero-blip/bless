import os
import pandas as pd
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
ARCHIVO = f"{DATA_DIR}/clientes.xlsx"
PAGOS_XLSX = f"{DATA_DIR}/pagos.xlsx"   # ✅ para borrar pagos del cliente

os.makedirs(DATA_DIR, exist_ok=True)


def _load_clientes():
    if not os.path.exists(ARCHIVO):
        return pd.DataFrame(columns=["nombre", "cedula", "telefono", "monto", "tipo_cobro"])

    df = pd.read_excel(ARCHIVO)

    # Normaliza columnas esperadas
    for col in ["nombre", "cedula", "telefono", "monto", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["nombre"] = df["nombre"].astype(str).replace(["nan", "NaT", "None"], "")
    df["telefono"] = df["telefono"].astype(str).replace(["nan", "NaT", "None"], "")
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

    return df


def _save_clientes(df: pd.DataFrame):
    df.to_excel(ARCHIVO, index=False)


def _delete_pagos_by_cedula(cedula: str):
    """
    ✅ Borra todos los pagos del cliente en data/pagos.xlsx.
    Compatible si antes guardaste pagos con columna "monto".
    """
    if not os.path.exists(PAGOS_XLSX):
        return

    df = pd.read_excel(PAGOS_XLSX)

    # Compatibilidad por si antes guardaste como "monto"
    if "monto" in df.columns and "valor" not in df.columns:
        df.rename(columns={"monto": "valor"}, inplace=True)

    if "cedula" not in df.columns:
        # Si no hay columna cédula no podemos filtrar -> no tocamos nada
        return

    df["cedula"] = df["cedula"].astype(str)
    cedula = str(cedula)

    df = df[df["cedula"] != cedula].reset_index(drop=True)
    df.to_excel(PAGOS_XLSX, index=False)


@router.get("/clientes", response_class=HTMLResponse)
def ver_clientes(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    df = _load_clientes()
    clientes = df.to_dict(orient="records")

    return templates.TemplateResponse(
        "clientes.html",
        {"request": request, "clientes": clientes, "user": user}
    )


@router.post("/clientes/guardar")
def guardar_cliente(
    request: Request,
    nombre: str = Form(...),
    cedula: str = Form(...),
    telefono: str = Form(...),
    monto: float = Form(...),
    tipo_cobro: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    df = _load_clientes()

    cedula = str(cedula).strip()
    nombre = str(nombre).strip()
    telefono = str(telefono).strip()
    tipo_cobro = str(tipo_cobro).strip()

    # Evitar duplicados por cédula
    if not df[df["cedula"].astype(str) == cedula].empty:
        return RedirectResponse("/clientes", status_code=303)

    nuevo = {
        "nombre": nombre,
        "cedula": cedula,
        "telefono": telefono,
        "monto": float(monto),
        "tipo_cobro": tipo_cobro,
    }

    df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
    _save_clientes(df)

    return RedirectResponse("/clientes", status_code=303)


@router.get("/clientes/editar", response_class=HTMLResponse)
def editar_cliente(request: Request, row_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    df = _load_clientes()
    if row_id < 0 or row_id >= len(df):
        return RedirectResponse("/clientes", status_code=303)

    row = df.iloc[row_id].to_dict()

    cliente = {
        "row_id": row_id,
        "nombre": str(row.get("nombre", "")),
        "cedula": str(row.get("cedula", "")),
        "telefono": str(row.get("telefono", "")),
        "monto": float(row.get("monto", 0)),
        "tipo_cobro": str(row.get("tipo_cobro", "")),
    }

    return templates.TemplateResponse(
        "clientes_editar.html",
        {"request": request, "cliente": cliente, "user": user}
    )


@router.post("/clientes/actualizar")
def actualizar_cliente(
    request: Request,
    row_id: int = Form(...),
    nombre: str = Form(...),
    cedula: str = Form(...),
    telefono: str = Form(...),
    monto: float = Form(...),
    tipo_cobro: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    df = _load_clientes()
    if row_id < 0 or row_id >= len(df):
        return RedirectResponse("/clientes", status_code=303)

    cedula = str(cedula).strip()

    # Validar duplicado de cédula con otra fila
    mask = (df["cedula"].astype(str) == cedula) & (df.index != row_id)
    if mask.any():
        return RedirectResponse("/clientes", status_code=303)

    df.loc[row_id, "nombre"] = str(nombre).strip()
    df.loc[row_id, "cedula"] = cedula
    df.loc[row_id, "telefono"] = str(telefono).strip()
    df.loc[row_id, "monto"] = float(monto)
    df.loc[row_id, "tipo_cobro"] = str(tipo_cobro).strip()

    _save_clientes(df)
    return RedirectResponse("/clientes", status_code=303)


@router.post("/clientes/eliminar")
def eliminar_cliente(
    request: Request,
    row_id: int = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    df = _load_clientes()
    if row_id < 0 or row_id >= len(df):
        return RedirectResponse("/clientes", status_code=303)

    # ✅ Capturar la cédula ANTES de borrar el cliente
    cedula = str(df.iloc[row_id].get("cedula", "")).strip()

    # ✅ Borrar cliente
    df = df.drop(index=row_id).reset_index(drop=True)
    _save_clientes(df)

    # ✅ Borrar pagos del cliente
    if cedula:
        _delete_pagos_by_cedula(cedula)

    return RedirectResponse("/clientes", status_code=303)
