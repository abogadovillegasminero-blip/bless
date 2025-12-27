from pydantic import BaseModel


class ClienteBase(BaseModel):
    nombre: str
    documento: str
    telefono: str


class ClienteCreate(ClienteBase):
    pass


class ClienteResponse(ClienteBase):
    id: int
