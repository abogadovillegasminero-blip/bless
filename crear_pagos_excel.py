import pandas as pd
import os

ruta = "app/data"
os.makedirs(ruta, exist_ok=True)

df = pd.DataFrame({
    "cliente": ["Juan", "Ana", "Juan"],
    "monto": [12000, 18000, 15000],
    "fecha": ["2025-01-01", "2025-01-01", "2025-01-02"]
})

df.to_excel("app/data/pagos.xlsx", index=False)
print("pagos.xlsx creado correctamente")
