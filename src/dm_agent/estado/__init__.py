"""Estado mecánico de partida.

F3.2: `GestorEstado` (persistencia JSON de `Ficha`/`EstadoPartida` con escritura
atómica y snapshots opcionales). Las tools que lo manipulan llegan en F3.3+.
"""

from dm_agent.estado.gestor import (
    ErrorEstado,
    ErrorEstadoInvalido,
    ErrorEstadoNoEncontrado,
    GestorEstado,
)

__all__ = [
    "ErrorEstado",
    "ErrorEstadoInvalido",
    "ErrorEstadoNoEncontrado",
    "GestorEstado",
]
