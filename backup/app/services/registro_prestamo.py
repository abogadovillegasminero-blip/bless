from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Prestamo, Cuota
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/registrar")
def registrar_prestamo(
    cliente_id: int, 
    monto: float, 
    interes: float, 
    total: float, 
    fecha_inicio: datetime, 
    db: Session = Depends(get_db)
):
    # Crear el préstamo
    prestamo = Prestamo(
        cliente_id=cliente_id, 
        monto=monto, 
        interes=interes, 
        total=total, 
        fecha_inicio=fecha_inicio
    )
    
    db.add(prestamo)
    db.commit()
    
    # Calcular las cuotas (suponiendo cuotas mensuales)
    cuotas = []
    fecha_cuota = fecha_inicio
    for i in range(12):  # Suponiendo 12 cuotas
        fecha_cuota = fecha_cuota + timedelta(days=30)
        cuota = Cuota(
            prestamo_id=prestamo.id, 
            numero=i+1, 
            valor=total / 12, 
            fecha_pago=fecha_cuota, 
            estado="pendiente"
        )
        cuotas.append(cuota)
    
    db.add_all(cuotas)
    db.commit()
    
    return {"mensaje": "Préstamo registrado con cuotas", "prestamo_id": prestamo.id}
