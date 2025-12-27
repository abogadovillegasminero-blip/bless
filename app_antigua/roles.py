from fastapi import Depends
from app.auth import get_current_user

def solo_admin(user=Depends(get_current_user)):
    if user["rol"] != "admin":
        raise Exception("Acceso denegado")
    return user
