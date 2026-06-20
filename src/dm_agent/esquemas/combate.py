"""Esquemas de combate narrativo mínimo (F5.1, distancias revisadas en F5.1.1,
iniciativa/turnos en F5.2, ataques/ventaja en F5.3-F5.4, acciones y
propuestas de reacción en F5.5).

Pensado para teatro de la mente (D17): sin grid, sin casillas, sin economía
de acciones completa. La posición se modela como una distancia relativa
(`cuerpo_a_cuerpo`, `corta`, `media`, `larga`, `fuera_de_alcance`), no
coordenadas. Conserva vocabulario de combate de D&D (enemigo, ataque, daño,
estado, iniciativa, turno, reacción) pero lo resuelve de forma
narrativa/conversacional, sin geometría exacta.

`EnemigoCombate` es el enemigo simple dentro de una escena de combate.
`EntradaIniciativa` es una entrada del orden de iniciativa de un combate
(personaje o enemigo). `AccionTurno` es un registro narrativo mínimo de lo
que hace un participante en su turno (sin validar economía de acciones).
`PropuestaReaccion` es una reacción/ataque de oportunidad **propuesto**
(D-COMBATE-04): nunca se aplica por sí sola, solo queda pendiente hasta que
el jugador confirma o rechaza. `CombateNarrativo` es la escena en sí: quién
participa, en qué estado está cada uno, el orden de iniciativa y si la
escena sigue activa.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dm_agent.esquemas.comun import CadenaNoVacia

Distancia = Literal["cuerpo_a_cuerpo", "corta", "media", "larga", "fuera_de_alcance"]


def _ahora_utc() -> str:
    return datetime.now(UTC).isoformat()


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


class AccionTurno(BaseModel):
    """Registro narrativo mínimo de una acción en un turno (F5.5).

    No valida economía de acciones (acción/acción adicional/reacción/
    movimiento): `tipo` es texto libre, solo a título de vocabulario sugerido
    (`accion`, `movimiento`, `accion_adicional`, `reaccion`, `interaccion`,
    `narrativa`). Sirve para que el DM recuerde qué hizo cada participante,
    no para arbitrar si "le quedaba acción".
    """

    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    turno_participante_id: CadenaNoVacia
    tipo: CadenaNoVacia
    descripcion: str = ""
    consumida: bool = False
    timestamp: str = Field(default_factory=_ahora_utc)
    version_schema: int = 1


class PropuestaReaccion(BaseModel):
    """Reacción o ataque de oportunidad **propuesto** (F5.5, D-COMBATE-04).

    Nunca se aplica por sí sola: ni tira dados ni hace daño. Queda
    `pendiente` hasta que `combate.resolver_reaccion` la mueve a
    `confirmada`/`rechazada`/`caducada`. Si el DM quiere aplicar de verdad
    una reacción confirmada, debe llamar explícitamente a la tool de ataque
    correspondiente (`combate.atacar_personaje`/`combate.atacar_enemigo`);
    esta propuesta por sí misma no dispara nada.

    `tipo` es texto libre (vocabulario sugerido: `ataque_oportunidad`,
    `reaccion`, `ventaja_narrativa`, `desventaja_narrativa`,
    `flanqueo_narrativo`, `cobertura_narrativa`), igual que `AccionTurno.tipo`.
    """

    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    combate_id: CadenaNoVacia
    ronda: int = Field(ge=1)
    turno_participante_id: str | None = None
    tipo: CadenaNoVacia
    quien_reacciona_id: CadenaNoVacia
    objetivo_id: CadenaNoVacia
    descripcion: str = ""
    motivo: str | None = None
    estado: Literal["pendiente", "confirmada", "rechazada", "aplicada", "caducada"] = "pendiente"
    confirmada: bool = False
    timestamp: str = Field(default_factory=_ahora_utc)
    version_schema: int = 1


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
    acciones_turno: list[AccionTurno] = Field(default_factory=list)
    propuestas_reaccion: list[PropuestaReaccion] = Field(default_factory=list)
    notas: str = ""
    version_schema: int = 1
