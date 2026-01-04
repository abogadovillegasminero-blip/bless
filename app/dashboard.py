import os
import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CLIENTES_XLSX = "data/clientes.xlsx"
PAGOS_XLSX = "data/pagos.xlsx"


def _load_clientes():
    if not os.path.exists(CLIENTES_XLSX):
        return pd.DataFrame(columns=["nombre", "cedula", "telefono", "monto", "tipo_cobro"])

    df = pd.read_excel(CLIENTES_XLSX)

    for col in ["nombre", "cedula", "telefono", "monto", "tipo_cobro"]:
        if col not in df.columns:
            df[col] = ""

    df["cedula"] = df["cedula"].astype(str)
    df["nombre"] = df["nombre"].astype(str).replace(["nan", "NaT", "None"], "")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    df["tipo_cobro"] = df["tipo_cobro"].astype(str).replace(["nan", "NaT", "None"], "")
    return df


def _load_pagos_full():
    if not os.path.exists(PAGOS_XLSX):
        return pd.DataFrame(columns=["cedula", "cliente", "fecha", "valor", "tipo_cobro"])

    df = pd.read_excel(PAGOS_XLSX)

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


def _compute_saldos(clientes: pd.DataFrame, pagos: pd.DataFrame) -> pd.DataFrame:
    pagos_sum = pagos.groupby("cedula", as_index=False)["valor"].sum()
    pagos_sum.rename(columns={"valor": "pagado"}, inplace=True)

    if clientes.empty:
        df = pd.DataFrame(columns=["nombre", "cedula", "monto", "pagado", "saldo", "tipo_cobro"])
    else:
        df = clientes.merge(pagos_sum, on="cedula", how="left")
        df["pagado"] = df["pagado"].fillna(0)
        df["saldo"] = df["monto"] - df["pagado"]

    return df


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    q = (request.query_params.get("q") or "").strip()

    clientes = _load_clientes()
    pagos = _load_pagos_full()

    df = _compute_saldos(clientes, pagos)

    total_clientes = int(len(clientes))
    total_prestado = float(clientes["monto"].sum()) if not clientes.empty else 0.0
    total_pagado = float(df["pagado"].sum()) if not df.empty else 0.0
    total_saldo = float(df["saldo"].sum()) if not df.empty else 0.0

    # Top saldos
    top_saldos = df.sort_values(by="saldo", ascending=False).head(10).to_dict(orient="records")

    # Últimos pagos
    pagos_recent = pagos.copy()
    try:
        pagos_recent["_fecha_dt"] = pd.to_datetime(pagos_recent["fecha"], errors="coerce")
        pagos_recent = pagos_recent.sort_values(by="_fecha_dt", ascending=False).drop(columns=["_fecha_dt"])
    except Exception:
        pass
    ultimos_pagos = pagos_recent.head(10).to_dict(orient="records")

    # ==========================
    # BUSCADOR DE CLIENTE
    # ==========================
    cliente_sel = None
    pagos_cliente = []
    resumen_cliente = None

    if q:
        q_low = q.lower()

        # Buscar en clientes por cédula exacta o por nombre contiene
        candidatos = clientes[
            (clientes["cedula"].astype(str) == q) |
            (clientes["nombre"].astype(str).str.lower().str.contains(q_low, na=False))
        ]

        if not candidatos.empty:
            cliente_sel = candidatos.iloc[0].to_dict()
            cedula_sel = str(cliente_sel.get("cedula", ""))

            # Resumen saldo cliente
            row = df[df["cedula"].astype(str) == cedula_sel]
            if not row.empty:
                r = row.iloc[0]
                resumen_cliente = {
                    "nombre": r.get("nombre", ""),
                    "cedula": r.get("cedula", ""),
                    "monto": float(r.get("monto", 0)),
                    "pagado": float(r.get("pagado", 0)),
                    "saldo": float(r.get("saldo", 0)),
                    "tipo_cobro": r.get("tipo_cobro", ""),
                }

            # Pagos del cliente
            pagos_c = pagos[pagos["cedula"].astype(str) == cedula_sel].copy()
            try:
                pagos_c["_fecha_dt"] = pd.to_datetime(pagos_c["fecha"], errors="coerce")
                pagos_c = pagos_c.sort_values(by="_fecha_dt", ascending=False).drop(columns=["_fecha_dt"])
            except Exception:
                pass
            pagos_cliente = pagos_c.to_dict(orient="records")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "q": q,

            "total_clientes": total_clientes,
            "total_prestado": total_prestado,
            "total_pagado": total_pagado,
            "total_saldo": total_saldo,

            "top_saldos": top_saldos,
            "ultimos_pagos": ultimos_pagos,

            "resumen_cliente": resumen_cliente,
            "pagos_cliente": pagos_cliente,
        }
    )
