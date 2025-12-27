from fastapi import APIRouter
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Cliente

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/")
def crear_cliente(nombre: str, documento: str):
    db: Session = SessionLocal()

    cliente = Cliente(nombre=nombre, documento=documento)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    db.close()
    return cliente


@router.get("/")
def listar_clientes():
    db: Session = SessionLocal()
    clientes = db.query(Cliente).all()
    db.close()
    return clientes
