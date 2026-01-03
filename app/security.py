from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, stored: str) -> bool:
    return pwd_context.verify(plain, stored)

def looks_hashed(stored: str) -> bool:
    return stored.startswith("$2a$") or stored.startswith("$2b$") or stored.startswith("$2y$")

