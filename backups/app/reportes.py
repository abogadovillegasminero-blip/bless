from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.auth_utils import get_current_user
import pandas as pd
import os

router = APIRouter()

@router.get("/reportes", response_class=HTMLResponse)
def reportes(user=Depends(get_current_user)):
    pagos = pd.read_excel("data/pagos.xlsx") if os.path.exists("data/pagos.xlsx") else pd.DataFrame()
    if pagos.empty:
        return "<h3>No hay pagos registrados</h3>"

    resumen = pagos.groupby("cliente")["valor"].sum().reset_index()
    return resumen.to_html(index=False)
