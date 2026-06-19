"""Esquema de memoria narrativa (F4.1).

`EntradaNarrativa` es una anotación de **ficción**: qué pasó en la historia, qué
decidió el jugador, qué pistas/PNJ/lugares aparecieron y qué consecuencias quedan
abiertas. Es distinta y complementaria de los `Evento` mecánicos
(`esquemas.evento.Evento`), que registran cambios de estado del juego.

Coherente con D17 (D&D 5.5 narrativo en solitario): favorece continuidad,
decisiones, consecuencias, pistas, PNJ, lugares y ritmo — no es un log táctico.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from dm_agent.esquemas.comun import CadenaNoVacia

Origen = Literal["usuario", "agente", "sistema", "resumen"]


def _ahora_utc() -> str:
    return datetime.now(UTC).isoformat()


class EntradaNarrativa(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    timestamp: str = Field(default_factory=_ahora_utc)
    campaña_id: CadenaNoVacia
    sesion_id: str | None = None
    tipo: CadenaNoVacia  # escena|decision|pista|pnj|lugar|consecuencia|nota|resumen (libre)
    titulo: str = ""
    contenido: CadenaNoVacia
    tags: list[str] = Field(default_factory=list)
    importancia: int = Field(ge=1, le=5, default=3)
    origen: Origen | None = None
    version_schema: int = 1


def crear_entrada(
    campaña_id: str,
    tipo: str,
    contenido: str,
    *,
    id: str | None = None,
    **kwargs: Any,
) -> EntradaNarrativa:
    """Construye una `EntradaNarrativa` generando `id` (uuid4) y `timestamp`."""
    return EntradaNarrativa(
        id=id or uuid.uuid4().hex,
        campaña_id=campaña_id,
        tipo=tipo,
        contenido=contenido,
        **kwargs,
    )
