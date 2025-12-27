from fastapi import APIRouter
from fastapi.responses import FileResponse
import pandas as pd
import os

router = APIRouter()

PAGOS_FILE = "pagos.xlsx"
EXPORT_FILE = "reporte_pagos.xlsx"

@router.get("/exportar")
def exportar_pagos():
    if not os.path.exists(PAGOS_FILE):
        return {"error": "No hay pagos"}

    df = pd.read_excel(PAGOS_FILE)
    df.to_excel(EXPORT_FILE, index=False)

    return FileResponse(
        EXPORT_FILE,
        filename=EXPORT_FILE,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
