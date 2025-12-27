from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteResponse

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"]
)

# LISTAR CLIENTES
@router.get("/", response_model=List[ClienteResponse], summary="Listar clientes")
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).all()

# CREAR CLIENTE
@router.post("/", response_model=ClienteResponse, summary="Crear cliente")
def crear_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    nuevo = Cliente(**cliente.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

# EDITAR CLIENTE
@router.put("/{id}", response_model=ClienteResponse, summary="Editar cliente")
def editar_cliente(id: int, cliente: ClienteCreate, db: Session = Depends(get_db)):
    db_cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db_cliente.nombre = cliente.nombre
    db_cliente.email = cliente.email
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

# ELIMINAR CLIENTE
@router.delete("/{id}", summary="Eliminar cliente")
def eliminar_cliente(id: int, db: Session = Depends(get_db)):
    db_cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db.delete(db_cliente)
    db.commit()
    return {"mensaje": "Cliente eliminado correctamente"}
