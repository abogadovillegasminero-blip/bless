from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cuota import Cuota

router = APIRouter(
    prefix="/cuotas",
    tags=["Cuotas"]
)

# 🔹 Listar todas las cuotas
@router.get("/", summary="Listar cuotas")
def listar_cuotas(db: Session = Depends(get_db)):
    return db.query(Cuota).all()


# 🔹 Marcar una cuota como pagada
@router.put("/{cuota_id}/pagar", summary="Marcar cuota como pagada")
def pagar_cuota(cuota_id: int, db: Session = Depends(get_db)):
    cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()

    if not cuota:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")

    if cuota.pagada:
        return {"mensaje": "La cuota ya estaba pagada"}

    cuota.pagada = True
    db.commit()
    db.refresh(cuota)

    return {
        "mensaje": "Cuota marcada como pagada",
        "cuota_id": cuota.id
    }
from datetime import date
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from app.database import get_db
from app.models.cuota import Cuota

router = APIRouter(
    prefix="/cuotas",
    tags=["Cuotas"]
)

@router.get("/hoy")
def cuotas_de_hoy(db: Session = Depends(get_db)):
    hoy = date.today()

    cuotas = db.query(Cuota).filter(
        Cuota.pagada == False,
        Cuota.fecha == hoy
    ).all()

    return cuotas
from fastapi import HTTPException

@router.put("/{cuota_id}/pagar")
def pagar_cuota(cuota_id: int, db: Session = Depends(get_db)):
    cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()

    if not cuota:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")

    if cuota.pagada:
        return {"mensaje": "La cuota ya estaba pagada"}

    cuota.pagada = True
    db.commit()

    return {
        "mensaje": "Cuota pagada correctamente",
        "cuota_id": cuota.id
    }
