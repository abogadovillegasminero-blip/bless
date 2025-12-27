from fastapi import APIRouter
from fastapi.responses import JSONResponse
import pandas as pd
import os

router = APIRouter()

@router.get("/graficos/pagos")
def grafico_pagos():
    ruta = "data/pagos.xlsx"
    if not os.path.exists(ruta):
        return JSONResponse([])

    df = pd.read_excel(ruta)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    resumen = df.groupby("fecha")["valor"].sum().reset_index()

    return JSONResponse(resumen.to_dict(orient="records"))
