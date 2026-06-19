"""Esquema de Ficha de personaje (F3.1).

Esquemas mínimos pero sólidos. NO incluyen todavía cálculo automático de nada
(p. ej. el bonificador de competencia es un campo explícito), ni tools que
modifiquen la ficha (eso es F3.3+).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dm_agent.esquemas.comun import CadenaNoVacia


class Atributos(BaseModel):
    """Las seis características de D&D 5e. Cada una entre 1 y 30."""

    model_config = ConfigDict(extra="forbid")

    fuerza: int = Field(ge=1, le=30)
    destreza: int = Field(ge=1, le=30)
    constitucion: int = Field(ge=1, le=30)
    inteligencia: int = Field(ge=1, le=30)
    sabiduria: int = Field(ge=1, le=30)
    carisma: int = Field(ge=1, le=30)


class ObjetoInventario(BaseModel):
    """Entrada de inventario simple (F3.1). El inventario rico llega más tarde."""

    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    nombre: CadenaNoVacia
    cantidad: int = Field(ge=1)
    descripcion: str | None = None
    equipado: bool = False


class Ficha(BaseModel):
    """Ficha de personaje mínima con estado mecánico básico."""

    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    nombre: CadenaNoVacia
    clase: CadenaNoVacia
    nivel: int = Field(ge=1, le=20)
    raza: CadenaNoVacia
    trasfondo: str = ""
    atributos: Atributos
    hp_max: int = Field(gt=0)
    hp_actual: int = Field(ge=0)
    ca: int = Field(gt=0)
    bonificador_competencia: int = Field(ge=2)
    xp: int = Field(ge=0, default=0)
    condiciones: list[str] = Field(default_factory=list)
    inventario: list[ObjetoInventario] = Field(default_factory=list)
    notas: str = ""
    version_schema: int = 1

    @model_validator(mode="after")
    def _validar_hp(self) -> Ficha:
        if self.hp_actual > self.hp_max:
            raise ValueError(
                f"hp_actual ({self.hp_actual}) no puede superar hp_max ({self.hp_max})"
            )
        return self
