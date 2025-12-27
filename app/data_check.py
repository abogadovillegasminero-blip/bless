import os

FILES = ["clientes.xlsx", "pagos.xlsx"]

for f in FILES:
    if not os.path.exists(f):
        open(f, "wb").close()
