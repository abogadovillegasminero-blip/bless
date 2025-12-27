from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey
from app.database import Base

class Cuota(Base):
    __tablename__ = "cuotas"

    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"))
    numero = Column(Integer)
    monto = Column(Float)
    pagada = Column(Boolean, default=False)
