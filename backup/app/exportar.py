from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, HTMLResponse
import pandas as pd
import os
from app.auth import get_current_user
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet

router = APIRouter(prefix="/exportar")

CLIENTES_FILE = "clientes.xlsx"

@router.get("/excel")
def exportar_excel(user=Depends(get_current_user)):
    if not os.path.exists(CLIENTES_FILE):
        df = pd.DataFrame(columns=["nombre", "saldo"])
    else:
        df = pd.read_excel(CLIENTES_FILE)

    salida = "reporte_clientes.xlsx"
    df.to_excel(salida, index=False)
    return FileResponse(salida, filename=salida)

@router.get("/pdf", response_class=FileResponse)
def exportar_pdf(user=Depends(get_current_user)):
    if not os.path.exists(CLIENTES_FILE):
        df = pd.DataFrame(columns=["nombre", "saldo"])
    else:
        df = pd.read_excel(CLIENTES_FILE)

    salida = "reporte_clientes.pdf"
    doc = SimpleDocTemplate(salida)
    styles = getSampleStyleSheet()

    elementos = [
        Paragraph("Reporte de Clientes", styles["Title"]),
        Table([df.columns.tolist()] + df.values.tolist())
    ]

    doc.build(elementos)
    return FileResponse(salida, filename=salida)
