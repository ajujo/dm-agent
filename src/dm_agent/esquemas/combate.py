"""Esquemas de combate narrativo mínimo (F5.1, distancias revisadas en F5.1.1,
iniciativa/turnos añadidos en F5.2).

Pensado para teatro de la mente (D17): sin grid, sin casillas, sin economía
de acciones completa. La posición se modela como una distancia relativa
(`cuerpo_a_cuerpo`, `corta`, `media`, `larga`, `fuera_de_alcance`), no
coordenadas. Conserva vocabulario de combate de D&D (enemigo, ataque, daño,
estado, iniciativa, turno) pero lo resuelve de forma narrativa/conversacional,
sin geometría exacta.

`EnemigoCombate` es el enemigo simple dentro de una escena de combate.
`EntradaIniciativa` es una entrada del orden de iniciativa de un combate
(personaje o enemigo). `CombateNarrativo` es la escena en sí: quién
participa, en qué estado está cada uno, el orden de iniciativa y si la
escena sigue activa.
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
    mod_destreza: int | None = Field(default=None, ge=-10, le=10)
    iniciativa: int | None = None
    version_schema: int = 1

    @model_validator(mode="after")
    def _validar_hp(self) -> EnemigoCombate:
        if self.hp_actual > self.hp_max:
            raise ValueError(
                f"hp_actual ({self.hp_actual}) no puede superar hp_max ({self.hp_max})"
            )
        return self


class EntradaIniciativa(BaseModel):
    """Una entrada del orden de iniciativa (personaje o enemigo)."""

    model_config = ConfigDict(extra="forbid")

    participante_id: CadenaNoVacia
    nombre: CadenaNoVacia
    tipo: Literal["personaje", "enemigo"]
    iniciativa: int
    es_personaje: bool = False


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
    orden_iniciativa: list[EntradaIniciativa] = Field(default_factory=list)
    indice_turno_actual: int = Field(ge=0, default=0)
    ronda: int = Field(ge=1, default=1)
    notas: str = ""
    version_schema: int = 1
