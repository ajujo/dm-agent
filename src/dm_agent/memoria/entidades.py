"""Gestor de entidades narrativas estructuradas por campaña (F4.6).

Estado estructurado *actual* (no append-only, a diferencia de la bitácora
narrativa de F4.1): un fichero JSON por tipo con la lista vigente de entidades.

    storage/
    └── campañas/
        └── <campaña_id>/
            └── entidades/
                ├── pnj.json
                ├── lugares.json
                ├── pistas.json
                ├── objetivos.json
                └── frentes.json

Guardar por `id`: si ya existe una entidad con ese `id` en el fichero, se
reemplaza. No registra eventos mecánicos ni entradas narrativas: esa
correlación, si se quiere, la hace quien llama a las tools.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from dm_agent.esquemas.entidades import PNJ, FrenteAbierto, Lugar, Objetivo, Pista

_SUBDIR_CAMPAÑAS = "campañas"
_SUBDIR_ENTIDADES = "entidades"

_FICHERO_PNJ = "pnj.json"
_FICHERO_LUGARES = "lugares.json"
_FICHERO_PISTAS = "pistas.json"
_FICHERO_OBJETIVOS = "objetivos.json"
_FICHERO_FRENTES = "frentes.json"

T = TypeVar("T", bound=BaseModel)


def _escribir_lista_atomico(ruta: Path, modelos: list[BaseModel]) -> None:
    """Serializa `modelos` y los escribe de forma atómica (tmp + replace)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps([m.model_dump(mode="json") for m in modelos], ensure_ascii=False, indent=2)
    fd, tmp_nombre = tempfile.mkstemp(dir=str(ruta.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_nombre, ruta)
    except BaseException:
        Path(tmp_nombre).unlink(missing_ok=True)
        raise


def _leer_lista(ruta: Path, modelo: type[T]) -> list[T]:
    if not ruta.is_file():
        return []
    crudo = json.loads(ruta.read_text(encoding="utf-8"))
    return [modelo.model_validate(item) for item in crudo]


def _ordenar(entidades: list[T]) -> list[T]:
    # Importancia descendente y luego nombre (orden estable y predecible).
    return sorted(entidades, key=lambda e: (-e.importancia, e.nombre))


class GestorEntidadesNarrativas:
    def __init__(self, raiz_storage: Path | str) -> None:
        self.raiz = Path(raiz_storage)

    # -- Rutas -------------------------------------------------------------

    def _dir_entidades(self, campaña_id: str) -> Path:
        return self.raiz / _SUBDIR_CAMPAÑAS / campaña_id / _SUBDIR_ENTIDADES

    def _ruta(self, campaña_id: str, fichero: str) -> Path:
        return self._dir_entidades(campaña_id) / fichero

    # -- Genéricos internos --------------------------------------------------

    def _guardar(self, campaña_id: str, fichero: str, modelo: type[T], nueva: T) -> T:
        ruta = self._ruta(campaña_id, fichero)
        actuales = _leer_lista(ruta, modelo)
        restantes = [e for e in actuales if e.id != nueva.id]
        restantes.append(nueva)
        _escribir_lista_atomico(ruta, restantes)
        return nueva

    def _listar(self, campaña_id: str, fichero: str, modelo: type[T]) -> list[T]:
        ruta = self._ruta(campaña_id, fichero)
        return _ordenar(_leer_lista(ruta, modelo))

    # -- PNJ -----------------------------------------------------------------

    def guardar_pnj(self, campaña_id: str, pnj: PNJ) -> PNJ:
        return self._guardar(campaña_id, _FICHERO_PNJ, PNJ, pnj)

    def listar_pnj(self, campaña_id: str) -> list[PNJ]:
        return self._listar(campaña_id, _FICHERO_PNJ, PNJ)

    # -- Lugares ---------------------------------------------------------------

    def guardar_lugar(self, campaña_id: str, lugar: Lugar) -> Lugar:
        return self._guardar(campaña_id, _FICHERO_LUGARES, Lugar, lugar)

    def listar_lugares(self, campaña_id: str) -> list[Lugar]:
        return self._listar(campaña_id, _FICHERO_LUGARES, Lugar)

    # -- Pistas ----------------------------------------------------------------

    def guardar_pista(self, campaña_id: str, pista: Pista) -> Pista:
        return self._guardar(campaña_id, _FICHERO_PISTAS, Pista, pista)

    def listar_pistas(self, campaña_id: str) -> list[Pista]:
        return self._listar(campaña_id, _FICHERO_PISTAS, Pista)

    # -- Objetivos ---------------------------------------------------------------

    def guardar_objetivo(self, campaña_id: str, objetivo: Objetivo) -> Objetivo:
        return self._guardar(campaña_id, _FICHERO_OBJETIVOS, Objetivo, objetivo)

    def listar_objetivos(self, campaña_id: str) -> list[Objetivo]:
        return self._listar(campaña_id, _FICHERO_OBJETIVOS, Objetivo)

    # -- Frentes abiertos --------------------------------------------------------

    def guardar_frente(self, campaña_id: str, frente: FrenteAbierto) -> FrenteAbierto:
        return self._guardar(campaña_id, _FICHERO_FRENTES, FrenteAbierto, frente)

    def listar_frentes(self, campaña_id: str) -> list[FrenteAbierto]:
        return self._listar(campaña_id, _FICHERO_FRENTES, FrenteAbierto)
