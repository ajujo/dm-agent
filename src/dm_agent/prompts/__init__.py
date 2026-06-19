"""Prompts del agente, cargados desde ficheros Markdown vecinos.

Decisión (F2.2): los prompts viven dentro del paquete (`src/dm_agent/prompts/`)
para que se distribuyan junto al código; se exponen como `package-data` en
`pyproject.toml`. Se cargan con `cargar_prompt(nombre)`.
"""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).resolve().parent


def cargar_prompt(nombre: str) -> str:
    """Carga un prompt por nombre de fichero (con o sin extensión `.md`)."""
    fichero = nombre if nombre.endswith(".md") else f"{nombre}.md"
    return (_DIR / fichero).read_text(encoding="utf-8").strip()


SYSTEM_DM_MINIMO = "system_dm_minimo"
