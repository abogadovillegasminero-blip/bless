import pandas as pd
from datetime import date
import os

def cierre_diario():
    if not os.path.exists("data/pagos.xlsx"):
        return

    df = pd.read_excel("data/pagos.xlsx")
    hoy = str(date.today())

    cierre = df[df["fecha"] == hoy]
    if cierre.empty:
        return

    cierre.to_excel(f"data/cierre_{hoy}.xlsx", index=False)
