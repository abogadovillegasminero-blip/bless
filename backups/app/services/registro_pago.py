from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Pago, Cuota

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"]
)


@router.post("/")
def registrar_pago(
    cuota_id: int,
    monto: float,
    db: Session = Depends(get_db)
):
    # Buscar la cuota
    cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()

    if not cuota:
        return {"error": "La cuota no existe"}

    if cuota.estado == "pagada":
        return {"error": "La cuota ya está pagada"}

    # Registrar el pago
    pago = Pago(
        cuota_id=cuota.id,
        monto=monto,
        fecha=cuota.fecha
    )

    db.add(pago)

    # Actualizar cuota
    cuota.estado = "pagada"

    db.commit()

    return {
        "mensaje": "Pago registrado correctamente",
        "cuota_id": cuota.id,
        "monto": monto
    }
