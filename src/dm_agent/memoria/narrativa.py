"""Gestor de memoria narrativa por campaña (F4.1).

Bitácora append-only en dos formatos complementarios:

    storage/
    └── campañas/
        └── <campaña_id>/
            └── narrativa/
                ├── bitacora.md      (legible por humanos)
                └── entradas.jsonl   (estructurado, una EntradaNarrativa por línea)

Distinto de `eventos.jsonl` (cambios mecánicos): aquí va la ficción
(decisiones, pistas, PNJ, lugares, consecuencias). No mezclar ambos.
"""

from __future__ import annotations

import json
from pathlib import Path

from dm_agent.esquemas.narrativa import EntradaNarrativa

_SUBDIR_CAMPAÑAS = "campañas"
_SUBDIR_NARRATIVA = "narrativa"
_FICHERO_BITACORA = "bitacora.md"
_FICHERO_ENTRADAS = "entradas.jsonl"


def _seccion_markdown(e: EntradaNarrativa) -> str:
    encabezado = f"## {e.timestamp} — {e.tipo.capitalize()}"
    if e.titulo:
        encabezado += f": {e.titulo}"
    lineas = [encabezado, "", e.contenido, ""]
    if e.tags:
        lineas.append(f"Tags: {', '.join(e.tags)}")
    lineas.append(f"Importancia: {e.importancia}")
    if e.origen:
        lineas.append(f"Origen: {e.origen}")
    return "\n".join(lineas) + "\n"


class GestorMemoriaNarrativa:
    def __init__(self, raiz_storage: Path | str) -> None:
        self.raiz = Path(raiz_storage)

    # -- Rutas -----------------------------------------------------------------

    def _dir_narrativa(self, campaña_id: str) -> Path:
        return self.raiz / _SUBDIR_CAMPAÑAS / campaña_id / _SUBDIR_NARRATIVA

    def ruta_bitacora(self, campaña_id: str) -> Path:
        return self._dir_narrativa(campaña_id) / _FICHERO_BITACORA

    def ruta_entradas(self, campaña_id: str) -> Path:
        return self._dir_narrativa(campaña_id) / _FICHERO_ENTRADAS

    # -- Escritura -------------------------------------------------------------

    def registrar_entrada(self, entrada: EntradaNarrativa) -> Path:
        dir_narrativa = self._dir_narrativa(entrada.campaña_id)
        dir_narrativa.mkdir(parents=True, exist_ok=True)

        ruta_entradas = self.ruta_entradas(entrada.campaña_id)
        with ruta_entradas.open("a", encoding="utf-8") as f:
            f.write(entrada.model_dump_json() + "\n")

        ruta_md = self.ruta_bitacora(entrada.campaña_id)
        with ruta_md.open("a", encoding="utf-8") as f:
            f.write(_seccion_markdown(entrada) + "\n")

        return ruta_entradas

    # -- Lectura ---------------------------------------------------------------

    def listar_entradas(self, campaña_id: str, limite: int = 20) -> list[EntradaNarrativa]:
        ruta = self.ruta_entradas(campaña_id)
        if not ruta.is_file():
            return []
        entradas: list[EntradaNarrativa] = []
        with ruta.open(encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                entradas.append(EntradaNarrativa.model_validate(json.loads(linea)))
        if limite is not None and limite >= 0:
            return entradas[-limite:]
        return entradas

    def ultimas_entradas_markdown(self, campaña_id: str, limite: int = 10) -> str:
        entradas = self.listar_entradas(campaña_id, limite=limite)
        if not entradas:
            return ""
        return "\n".join(_seccion_markdown(e) for e in entradas)
