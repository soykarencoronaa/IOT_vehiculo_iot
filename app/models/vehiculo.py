# app/models/vehiculo.py

from pydantic import BaseModel, Field


class VehiculoCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    modelo: str | None = Field(default=None, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)
    microcontrolador: str | None = Field(default=None, max_length=50)


class VehiculoActualizar(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    modelo: str | None = Field(default=None, max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)
    microcontrolador: str | None = Field(default=None, max_length=50)
    activo: bool


class ComandoCrear(BaseModel):
    id_vehiculo: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=60)
    codigo: int
    descripcion: str | None = Field(default=None, max_length=255)


class ComandoActualizar(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    codigo: int
    descripcion: str | None = Field(default=None, max_length=255)
    activo: bool


class HistorialCrear(BaseModel):
    id_vehiculo: int = Field(gt=0)
    id_comando: int | None = Field(default=None, gt=0)
    origen: str = Field(default="MANUAL", min_length=1, max_length=30)


class EstadoVehiculoActualizar(BaseModel):
    id_comando: int | None = Field(default=None, gt=0)
    conectado: bool
    origen: str = Field(default="WEBSOCKET", min_length=1, max_length=30)
