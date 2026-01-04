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

os.makedirs(DATA_DIR, exist_ok=True)


def _load_clientes():
    if not os.path.exists(ARCHIVO):
        return pd.DataFrame(columns=["nombre", "cedula", "telefono", "monto", "tipo_cobro"])

    df = pd.read_excel(ARCHIVO)

    # normaliza columnas
    for col in ["nombre", "cedula", "telefono", "monto", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    # limpia
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


def _save_clientes(df: pd.DataFrame):
    df.to_excel(ARCHIVO, index=False)


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

    nombre = str(nombre).strip()
    cedula = str(cedula).strip()
    telefono = str(telefono).strip()
    tipo_cobro = str(tipo_cobro).strip().lower()

    nuevo = {
        "nombre": nombre,
        "cedula": cedula,
        "telefono": telefono,
        "monto": float(monto),
        "tipo_cobro": tipo_cobro,
    }

    df = _load_clientes()

    # evita duplicado por cédula (si existe, lo actualiza)
    existe = df[df["cedula"].astype(str) == cedula]
    if not existe.empty:
        idx = existe.index[0]
        df.at[idx, "nombre"] = nombre
        df.at[idx, "telefono"] = telefono
        df.at[idx, "monto"] = float(monto)
        df.at[idx, "tipo_cobro"] = tipo_cobro
    else:
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)

    _save_clientes(df)
    return RedirectResponse("/clientes", status_code=303)


@router.get("/clientes/ver", response_class=HTMLResponse)
def ver_cliente(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    cedula = (request.query_params.get("cedula") or "").strip()
    if not cedula:
        return RedirectResponse("/clientes", status_code=303)

    df = _load_clientes()
    match = df[df["cedula"].astype(str) == cedula]

    if match.empty:
        return RedirectResponse("/clientes", status_code=303)

    cliente = match.iloc[0].to_dict()

    return templates.TemplateResponse(
        "cliente_ver.html",
        {"request": request, "cliente": cliente, "user": user}
    )
