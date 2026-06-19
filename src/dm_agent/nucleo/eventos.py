"""Bus de eventos en memoria (runtime).

F3.5 — unificación: el modelo de `Evento` es **canónico** y vive en
`dm_agent.esquemas.evento`. Este módulo lo **re-exporta** (no hay ya un dataclass
paralelo) y ofrece un bus pub/sub mínimo que publica ese mismo modelo Pydantic.

    from dm_agent.nucleo.eventos import Evento  # == dm_agent.esquemas.evento.Evento

Para construir eventos usa `crear_evento(tipo, ...)` (genera `id` y `timestamp`).
"""

from __future__ import annotations

from collections.abc import Callable

from dm_agent.esquemas.evento import Evento, crear_evento

__all__ = ["BusEventos", "Evento", "Subscriber", "bus", "crear_evento"]


Subscriber = Callable[[Evento], None]


class BusEventos:
    """Bus pub/sub mínimo en memoria. Publica `Evento` canónicos."""

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
