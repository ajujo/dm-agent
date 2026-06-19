"""GestorEstado: persistencia JSON de `Ficha` y `EstadoPartida` (F3.2).

Guarda y carga los esquemas de F3.1 con escritura atómica y snapshots
opcionales. NO incluye todavía tools de ficha/HP/XP, combate, inventario rico,
mundo, misiones, RAG ni memoria narrativa: solo persistencia de los esquemas.

Estructura en disco:

    <storage>/
    └── campañas/
        └── <campaña_id>/
            ├── estado_partida.json
            ├── fichas/
            │   └── <personaje_id>.json
            └── snapshots/
                ├── estado_partida_<ts>.json
                └── ficha_<personaje_id>_<ts>.json
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from dm_agent.esquemas.estado import EstadoPartida
from dm_agent.esquemas.ficha import Ficha

_SUBDIR_CAMPAÑAS = "campañas"
_FICHERO_ESTADO = "estado_partida.json"
_SUBDIR_FICHAS = "fichas"
_SUBDIR_SNAPSHOTS = "snapshots"


class ErrorEstado(Exception):
    """Base de los errores de persistencia de estado."""


class ErrorEstadoNoEncontrado(ErrorEstado):
    """No existe el fichero/campaña/ficha solicitado."""


class ErrorEstadoInvalido(ErrorEstado):
    """El contenido en disco no es JSON válido o no cumple el esquema."""


def _timestamp_archivo() -> str:
    # UTC y seguro para nombre de fichero (sin ':').
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")


def _escribir_json_atomico(ruta: Path, modelo: BaseModel) -> None:
    """Serializa `modelo` y lo escribe de forma atómica (tmp + replace)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = modelo.model_dump_json(indent=2)
    json.loads(texto)  # sanity: nunca escribir algo que no sea JSON válido
    fd, tmp_nombre = tempfile.mkstemp(dir=str(ruta.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_nombre, ruta)
    except BaseException:
        # Limpia el temporal si algo falla antes del replace.
        Path(tmp_nombre).unlink(missing_ok=True)
        raise


def _cargar_modelo(ruta: Path, modelo: type[BaseModel]) -> BaseModel:
    if not ruta.is_file():
        raise ErrorEstadoNoEncontrado(f"no existe: {ruta}")
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErrorEstadoInvalido(f"JSON inválido en {ruta}: {e}") from e
    try:
        return modelo.model_validate(crudo)
    except ValidationError as e:
        raise ErrorEstadoInvalido(f"esquema inválido en {ruta}: {e}") from e


class GestorEstado:
    def __init__(self, raiz_storage: Path | str, snapshots: bool = False) -> None:
        self.raiz = Path(raiz_storage)
        self.snapshots = snapshots

    # -- Rutas -----------------------------------------------------------------

    def ruta_campaña(self, campaña_id: str) -> Path:
        return self.raiz / _SUBDIR_CAMPAÑAS / campaña_id

    def _ruta_estado(self, campaña_id: str) -> Path:
        return self.ruta_campaña(campaña_id) / _FICHERO_ESTADO

    def _ruta_ficha(self, campaña_id: str, personaje_id: str) -> Path:
        return self.ruta_campaña(campaña_id) / _SUBDIR_FICHAS / f"{personaje_id}.json"

    def existe_campaña(self, campaña_id: str) -> bool:
        return self.ruta_campaña(campaña_id).is_dir()

    def crear_campaña_si_no_existe(self, campaña_id: str) -> Path:
        ruta = self.ruta_campaña(campaña_id)
        (ruta / _SUBDIR_FICHAS).mkdir(parents=True, exist_ok=True)
        return ruta

    # -- Snapshots -------------------------------------------------------------

    def _snapshot_si_procede(self, campaña_id: str, destino: Path, nombre_base: str) -> Path | None:
        if not self.snapshots or not destino.exists():
            return None
        snap_dir = self.ruta_campaña(campaña_id) / _SUBDIR_SNAPSHOTS
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap = snap_dir / f"{nombre_base}_{_timestamp_archivo()}.json"
        snap.write_bytes(destino.read_bytes())
        return snap

    # -- Ficha -----------------------------------------------------------------

    def guardar_ficha(self, campaña_id: str, ficha: Ficha) -> Path:
        self.crear_campaña_si_no_existe(campaña_id)
        destino = self._ruta_ficha(campaña_id, ficha.id)
        self._snapshot_si_procede(campaña_id, destino, f"ficha_{ficha.id}")
        _escribir_json_atomico(destino, ficha)
        return destino

    def cargar_ficha(self, campaña_id: str, personaje_id: str) -> Ficha:
        ruta = self._ruta_ficha(campaña_id, personaje_id)
        modelo = _cargar_modelo(ruta, Ficha)
        assert isinstance(modelo, Ficha)
        return modelo

    def listar_fichas(self, campaña_id: str) -> list[str]:
        dir_fichas = self.ruta_campaña(campaña_id) / _SUBDIR_FICHAS
        if not dir_fichas.is_dir():
            return []
        return sorted(p.stem for p in dir_fichas.glob("*.json"))

    # -- EstadoPartida ---------------------------------------------------------

    def guardar_estado_partida(self, estado: EstadoPartida) -> Path:
        self.crear_campaña_si_no_existe(estado.campaña_id)
        destino = self._ruta_estado(estado.campaña_id)
        self._snapshot_si_procede(estado.campaña_id, destino, "estado_partida")
        _escribir_json_atomico(destino, estado)
        return destino

    def cargar_estado_partida(self, campaña_id: str) -> EstadoPartida:
        ruta = self._ruta_estado(campaña_id)
        modelo = _cargar_modelo(ruta, EstadoPartida)
        assert isinstance(modelo, EstadoPartida)
        return modelo
