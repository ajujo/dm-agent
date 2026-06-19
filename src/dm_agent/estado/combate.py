"""GestorCombateNarrativo: persistencia de combates narrativos mínimos (F5.1).

    storage/
    └── campañas/
        └── <campaña_id>/
            └── combates/
                ├── <combate_id>.json
                └── activo.json

Decisión: `activo.json` guarda solo una **referencia** (`{"combate_id": ...}`),
no el combate completo. Así solo hay un sitio que escribir por mutación (el
fichero `<combate_id>.json`); `activo.json` nunca puede quedar desincronizado
con el contenido real del combate. Solo puede haber una referencia activa por
campaña: escribirla reemplaza la anterior.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from dm_agent.esquemas.combate import CombateNarrativo

_SUBDIR_CAMPAÑAS = "campañas"
_SUBDIR_COMBATES = "combates"
_FICHERO_ACTIVO = "activo.json"


class ErrorCombate(Exception):
    """Base de los errores de persistencia de combate."""


class ErrorCombateNoEncontrado(ErrorCombate):
    """No existe el combate solicitado."""


def _escribir_json_atomico(ruta: Path, contenido: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(contenido, ensure_ascii=False, indent=2)
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


class GestorCombateNarrativo:
    def __init__(self, raiz_storage: Path | str) -> None:
        self.raiz = Path(raiz_storage)

    # -- Rutas -------------------------------------------------------------

    def _dir_combates(self, campaña_id: str) -> Path:
        return self.raiz / _SUBDIR_CAMPAÑAS / campaña_id / _SUBDIR_COMBATES

    def _ruta_combate(self, campaña_id: str, combate_id: str) -> Path:
        return self._dir_combates(campaña_id) / f"{combate_id}.json"

    def _ruta_activo(self, campaña_id: str) -> Path:
        return self._dir_combates(campaña_id) / _FICHERO_ACTIVO

    # -- Combates ------------------------------------------------------------

    def guardar(self, combate: CombateNarrativo) -> CombateNarrativo:
        ruta = self._ruta_combate(combate.campaña_id, combate.id)
        _escribir_json_atomico(ruta, combate.model_dump(mode="json"))
        return combate

    def cargar(self, campaña_id: str, combate_id: str) -> CombateNarrativo:
        ruta = self._ruta_combate(campaña_id, combate_id)
        if not ruta.is_file():
            raise ErrorCombateNoEncontrado(f"no existe combate {combate_id!r} en {campaña_id!r}")
        return CombateNarrativo.model_validate(json.loads(ruta.read_text(encoding="utf-8")))

    def listar(self, campaña_id: str) -> list[CombateNarrativo]:
        dir_combates = self._dir_combates(campaña_id)
        if not dir_combates.is_dir():
            return []
        combates = []
        for ruta in sorted(dir_combates.glob("*.json")):
            if ruta.name == _FICHERO_ACTIVO:
                continue
            combates.append(CombateNarrativo.model_validate(json.loads(ruta.read_text(encoding="utf-8"))))
        return combates

    # -- Combate activo (referencia, F5.1: uno por campaña) -------------------

    def marcar_activo(self, combate: CombateNarrativo) -> None:
        _escribir_json_atomico(self._ruta_activo(combate.campaña_id), {"combate_id": combate.id})

    def limpiar_activo(self, campaña_id: str) -> None:
        self._ruta_activo(campaña_id).unlink(missing_ok=True)

    def cargar_activo(self, campaña_id: str) -> CombateNarrativo | None:
        ruta = self._ruta_activo(campaña_id)
        if not ruta.is_file():
            return None
        combate_id = json.loads(ruta.read_text(encoding="utf-8")).get("combate_id")
        if not combate_id:
            return None
        try:
            return self.cargar(campaña_id, combate_id)
        except ErrorCombateNoEncontrado:
            return None
