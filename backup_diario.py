import zipfile
import os
from datetime import datetime

ARCHIVOS = ["clientes.xlsx", "pagos.xlsx"]
CARPETA_BACKUP = "backups"

os.makedirs(CARPETA_BACKUP, exist_ok=True)

nombre = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
ruta = os.path.join(CARPETA_BACKUP, nombre)

with zipfile.ZipFile(ruta, "w") as zipf:
    for a in ARCHIVOS:
        if os.path.exists(a):
            zipf.write(a)

print("Backup creado:", ruta)
