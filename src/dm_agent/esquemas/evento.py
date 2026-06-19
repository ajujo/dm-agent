"""Esquema de Evento auditable (F3.1).

Un `Evento` es el registro inmutable de "algo que pasó", pensado para auditoría
(cada cambio mecánico futuro emitirá uno). En F3.1 solo se define el esquema y
un helper de construcción; el log JSONL auditable de eventos por cada cambio de
estado es F3.5.

Nota: convive con `dm_agent.nucleo.eventos.Evento`, que es un dataclass ligero
usado por las herramientas en tiempo de ejecución. Este `Evento` (pydantic) es
el modelo persistible/auditable. Se mantienen separados a propósito mientras no
se unifiquen en F3.5.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from dm_agent.esquemas.comun import CadenaNoVacia


def _ahora_utc() -> str:
    return datetime.now(UTC).isoformat()


class Evento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CadenaNoVacia
    timestamp: str = Field(default_factory=_ahora_utc)
    tipo: CadenaNoVacia
    actor: str | None = None
    objetivo: str | None = None
    tool: str | None = None
    datos: dict[str, Any] = Field(default_factory=dict)
    motivo: str | None = None
    version_schema: int = 1


def crear_evento(tipo: str, *, id: str | None = None, **kwargs: Any) -> Evento:
    """Construye un `Evento` generando `id` (uuid4) y `timestamp` si no se dan."""
    return Evento(id=id or uuid.uuid4().hex, tipo=tipo, **kwargs)
