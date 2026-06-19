"""Contrato base de herramientas (tools).

Una `Herramienta` es un handler determinista con:
- nombre único (`<toolset>.<accion>`)
- schema JSON de parámetros
- declaración de qué lee y qué modifica del estado
- gate de disponibilidad
- ejecución que devuelve `ResultadoHerramienta`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from dm_agent.nucleo.eventos import Evento


@dataclass(slots=True)
class ResultadoHerramienta:
    ok: bool
    datos: dict[str, Any] = field(default_factory=dict)
    eventos: list[Evento] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


@runtime_checkable
class Herramienta(Protocol):
    nombre: str
    descripcion: str
    schema: dict[str, Any]
    requiere: list[str]
    modifica: list[str]

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        ...

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        ...
