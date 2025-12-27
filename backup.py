import os
import shutil
from datetime import datetime

ORIGEN = "data"
DESTINO = "backups"

os.makedirs(DESTINO, exist_ok=True)

fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
archivo = f"backup_{fecha}"

ruta = os.path.join(DESTINO, archivo)

shutil.make_archive(ruta, "zip", ORIGEN)

print("✅ Backup creado en:", ruta + ".zip")
