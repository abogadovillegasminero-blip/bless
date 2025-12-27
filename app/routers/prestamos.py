from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.schemas.prestamo import PrestamoCreate

router = APIRouter(prefix="/prestamos", tags=["Préstamos"])

@router.post("/")
def crear_prestamo(data: PrestamoCreate, db: Session = Depends(get_db)):

    prestamo = Prestamo(**data.dict())
    db.add(prestamo)
    db.commit()
    db.refresh(prestamo)

    # 🔹 CÁLCULO DE CUOTAS
    interes_total = prestamo.monto * (prestamo.interes / 100)
    total_pagar = prestamo.monto + interes_total
    valor_cuota = total_pagar / prestamo.plazo_meses

    for n in range(1, prestamo.plazo_meses + 1):
        cuota = Cuota(
            prestamo_id=prestamo.id,
            numero_cuota=n,
            valor=round(valor_cuota, 2)
        )
        db.add(cuota)

    db.commit()

    return {"mensaje": "Préstamo y cuotas creadas correctamente"}
