from fastapi import Request
from jose import jwt

SECRET_KEY = "bless-secret"
ALGORITHM = "HS256"

def requiere_rol(rol: str):
    def checker(request: Request):
        token = request.cookies.get("token")
        if not token:
            return False
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data.get("rol") == rol
    return checker
