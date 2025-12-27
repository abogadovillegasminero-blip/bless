import pandas as pd
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

data = [
    {
        "username": "admin",
        "password_hash": pwd_context.hash("admin123")
    }
]

df = pd.DataFrame(data)
df.to_excel("usuarios.xlsx", index=False)

print("usuarios.xlsx creado correctamente")
