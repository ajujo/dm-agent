"""Esquemas de entidades narrativas estructuradas (F4.6).

Complementan la bitácora narrativa (F4.1): la bitácora responde **qué pasó**;
las entidades responden **quién existe, dónde está, qué sabemos y qué queda
pendiente**. Son estado estructurado *actual* (no append-only): guardar con un
`id` ya existente reemplaza la entidad.

Tipos mínimos: `PNJ`, `Lugar`, `Pista`, `Objetivo`, `FrenteAbierto`. Sin
relaciones complejas, sin facciones, sin mapas: solo lo necesario para dar
continuidad a una campaña narrativa en solitario (D17).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from dm_agent.esquemas.comun import CadenaNoVacia


class EntidadBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    nombre: CadenaNoVacia
    descripcion: str = ""
    estado: str = ""
    tags: list[str] = Field(default_factory=list)
    importancia: int = Field(ge=1, le=5, default=3)
    notas: str = ""
    version_schema: int = 1


class PNJ(EntidadBase):
    rol: str | None = None
    actitud: str | None = None
    ubicacion_id: str | None = None
    relacion_con_personaje: str | None = None


class Lugar(EntidadBase):
    tipo: str | None = None
    conectado_con: list[str] = Field(default_factory=list)


class Pista(EntidadBase):
    origen: str | None = None
    relacionada_con: str | None = None
    resuelta: bool = False


class Objetivo(EntidadBase):
    prioridad: int | None = None
    relacionado_con: str | None = None


class FrenteAbierto(EntidadBase):
    amenaza: str | None = None
    reloj: int | None = Field(default=None, ge=0, le=6)
    consecuencias: str | None = None
    relacionado_con: str | None = None
