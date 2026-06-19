"""Herramientas deterministas que el LLM puede invocar via tool_call."""

from dm_agent.herramientas.base import Herramienta, ResultadoHerramienta
from dm_agent.herramientas.registro import RegistroHerramientas

__all__ = ["Herramienta", "ResultadoHerramienta", "RegistroHerramientas"]
