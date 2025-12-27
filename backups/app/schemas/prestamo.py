from pydantic import BaseModel

class PrestamoCreate(BaseModel):
    cliente_id: int
    monto: float
    interes: float
    plazo_meses: int

class PrestamoResponse(PrestamoCreate):
    id: int
