from pydantic import BaseModel, Field


class DemoCrear(BaseModel):
    id_vehiculo: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)


class DemoActualizar(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)
    activo: bool


class MovimientoDemoCrear(BaseModel):
    id_comando: int = Field(gt=0)
    orden: int = Field(ge=0)
    duracion_ms: int = Field(ge=0)
    pausa_ms: int = Field(ge=0)


class MovimientoDemoActualizar(BaseModel):
    id_comando: int = Field(gt=0)
    orden: int = Field(ge=0)
    duracion_ms: int = Field(ge=0)
    pausa_ms: int = Field(ge=0)
