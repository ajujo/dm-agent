"""Esquemas de combate narrativo mínimo (F5.1, distancias revisadas en F5.1.1).

Pensado para teatro de la mente (D17): sin grid, sin casillas, sin iniciativa
compleja. La posición se modela como una distancia relativa (`cuerpo_a_cuerpo`,
`corta`, `media`, `larga`, `fuera_de_alcance`), no coordenadas. Conserva
vocabulario de combate de D&D (enemigo, ataque, daño, estado) pero lo resuelve
de forma narrativa/conversacional, sin geometría exacta.

`EnemigoCombate` es el enemigo simple dentro de una escena de combate.
`CombateNarrativo` es la escena en sí: quién participa, en qué estado está
cada uno y si la escena sigue activa.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dm_agent.esquemas.comun import CadenaNoVacia

Distancia = Literal["cuerpo_a_cuerpo", "corta", "media", "larga", "fuera_de_alcance"]


class EnemigoCombate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    nombre: CadenaNoVacia
    hp_max: int = Field(gt=0)
    hp_actual: int = Field(ge=0)
    ca: int = Field(gt=0)
    estado: CadenaNoVacia = "activo"
    descripcion: str = ""
    distancia: Distancia | None = None
    tags: list[str] = Field(default_factory=list)
    version_schema: int = 1

    @model_validator(mode="after")
    def _validar_hp(self) -> EnemigoCombate:
        if self.hp_actual > self.hp_max:
            raise ValueError(
                f"hp_actual ({self.hp_actual}) no puede superar hp_max ({self.hp_max})"
            )
        return self


class CombateNarrativo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    campaña_id: CadenaNoVacia
    sesion_id: str | None = None
    personaje_id: CadenaNoVacia
    estado: CadenaNoVacia = "activo"
    turno: int = Field(ge=0, default=0)
    descripcion_escena: str = ""
    enemigos: list[EnemigoCombate] = Field(default_factory=list)
    notas: str = ""
    version_schema: int = 1
