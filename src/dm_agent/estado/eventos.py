"""Registro append-only de eventos auditables por campaña (F3.4).

Cada campaña tiene un `eventos.jsonl` bajo su carpeta de storage. Cada línea es
un `dm_agent.esquemas.evento.Evento` (pydantic) serializado a JSON.

    storage/
    └── campañas/
        └── <campaña_id>/
            └── eventos.jsonl

Nota (F3.5): existen dos `Evento` en el proyecto —el dataclass de runtime
`dm_agent.nucleo.eventos.Evento` y este persistible `dm_agent.esquemas.evento.
Evento`—. F3.4 usa el persistible para `eventos.jsonl`. La unificación
runtime/persistible queda pendiente para F3.5.
"""

from __future__ import annotations

import json
from pathlib import Path

from dm_agent.esquemas.evento import Evento

_SUBDIR_CAMPAÑAS = "campañas"
_FICHERO_EVENTOS = "eventos.jsonl"


class RegistroEventosEstado:
    def __init__(self, raiz_storage: Path | str) -> None:
        self.raiz = Path(raiz_storage)

    def ruta_eventos(self, campaña_id: str) -> Path:
        return self.raiz / _SUBDIR_CAMPAÑAS / campaña_id / _FICHERO_EVENTOS

    def registrar(self, campaña_id: str, evento: Evento) -> Path:
        ruta = self.ruta_eventos(campaña_id)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as f:
            f.write(evento.model_dump_json() + "\n")
        return ruta

    def listar(self, campaña_id: str) -> list[Evento]:
        ruta = self.ruta_eventos(campaña_id)
        if not ruta.is_file():
            return []
        eventos: list[Evento] = []
        with ruta.open(encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                eventos.append(Evento.model_validate(json.loads(linea)))
        return eventos
