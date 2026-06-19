"""Esquema de EstadoPartida (F3.1).

Estado mecánico mínimo de "dónde está la partida": qué personaje juega, en qué
fase y escena, y qué turno. NO modela todavía el mundo, ni el combate completo,
ni la línea temporal: eso llega en fases posteriores.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from dm_agent.esquemas.comun import CadenaNoVacia


class FaseActual(StrEnum):
    EXPLORACION = "exploracion"
    SOCIAL = "social"
    COMBATE = "combate"
    DESCANSO = "descanso"
    VIAJE = "viaje"
    GESTION = "gestion"


class EstadoPartida(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    campaña_id: CadenaNoVacia
    personaje_activo_id: CadenaNoVacia | None = None
    fase_actual: FaseActual = FaseActual.EXPLORACION
    escena_actual: str = ""
    turno: int = Field(ge=0, default=0)
    sesion_id: str | None = None
    version_schema: int = 1
