"""Memoria persistente tipada.

F4.1: memoria narrativa por campaña (`GestorMemoriaNarrativa`), bitácora
append-only en Markdown + JSONL. Distinta de los eventos mecánicos.
"""

from dm_agent.memoria.cierre_sesion import (
    CierreSesionNarrativa,
    CierreVacio,
    ErrorCierre,
    TextoSesionVacio,
)
from dm_agent.memoria.contexto import ConstructorContextoMemoria
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.memoria.resumen import (
    ErrorResumen,
    MaterialVacio,
    ResumenVacio,
    ResumidorNarrativo,
    SinEntradasParaResumir,
)

__all__ = [
    "CierreSesionNarrativa",
    "CierreVacio",
    "ConstructorContextoMemoria",
    "ErrorCierre",
    "ErrorResumen",
    "GestorMemoriaNarrativa",
    "MaterialVacio",
    "ResumenVacio",
    "ResumidorNarrativo",
    "SinEntradasParaResumir",
    "TextoSesionVacio",
]
