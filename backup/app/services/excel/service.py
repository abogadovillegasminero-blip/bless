import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = BASE_DIR / "clientes.xlsx"

def guardar_cliente(data: dict):
    df_nuevo = pd.DataFrame([data])

    if EXCEL_PATH.exists():
        df = pd.read_excel(EXCEL_PATH)
        df = pd.concat([df, df_nuevo], ignore_index=True)
    else:
        df = df_nuevo

    df.to_excel(EXCEL_PATH, index=False)
