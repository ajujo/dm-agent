"""Esquemas de datos compartidos (pydantic v2).

F3.1: esquemas base de estado mecánico — `Ficha`, `EstadoPartida`, `Evento`.
Solo modelos y validaciones; las tools que los manipulan llegan en F3.3+.
"""

from dm_agent.esquemas.estado import EstadoPartida, FaseActual
from dm_agent.esquemas.evento import Evento, crear_evento
from dm_agent.esquemas.ficha import Atributos, Ficha, ObjetoInventario

__all__ = [
    "Atributos",
    "EstadoPartida",
    "Evento",
    "FaseActual",
    "Ficha",
    "ObjetoInventario",
    "crear_evento",
]
