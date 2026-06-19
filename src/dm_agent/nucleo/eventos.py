"""Sistema de eventos del agente.

Versión Fase 1: dataclass + bus pub/sub mínimo en memoria.
Fase 3 añadirá subscribers reales (logger, bitácora narrativa).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Evento:
    tipo: str
    actor: str | None = None
    objetivo: str | None = None
    datos: dict[str, Any] = field(default_factory=dict)
    motivo_llm: str | None = None
    semilla_dados: int | None = None
    momento: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


Subscriber = Callable[[Evento], None]


class BusEventos:
    def __init__(self) -> None:
        self._subs: list[Subscriber] = []

    def subscribirse(self, fn: Subscriber) -> None:
        self._subs.append(fn)

    def publicar(self, evento: Evento) -> None:
        for fn in self._subs:
            fn(evento)

    def limpiar(self) -> None:
        self._subs.clear()


bus = BusEventos()
