"""Sesión de juego persistida como JSONL append-only.

Cada línea es un registro JSON con al menos `tipo` y `timestamp`. Tipos usados
en F2.2:

    {"tipo": "user",        "content": "...",            "timestamp": "..."}
    {"tipo": "assistant",   "content": "...",            "timestamp": "..."}
    {"tipo": "tool_call",   "nombre_api": "dados_tirar", "argumentos": {...}, "timestamp": "..."}
    {"tipo": "tool_result", "nombre_api": "dados_tirar", "ok": true, "resultado": {...}, "timestamp": "..."}

No se guarda estado mecánico: solo el historial narrativo/operativo.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _ahora() -> str:
    return datetime.now(UTC).isoformat()


def _id_por_defecto() -> str:
    # Ordenable lexicográficamente => la "última" sesión es la de id mayor.
    return datetime.now(UTC).strftime("sesion-%Y%m%d-%H%M%S")


class Sesion:
    """Una sesión = un fichero `.jsonl`."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)

    # -- Construcción ----------------------------------------------------------

    @property
    def id(self) -> str:
        return self.ruta.stem

    @classmethod
    def crear(cls, dir_sesiones: Path, id: str | None = None) -> Sesion:
        dir_sesiones = Path(dir_sesiones)
        dir_sesiones.mkdir(parents=True, exist_ok=True)
        sid = id or _id_por_defecto()
        ruta = dir_sesiones / f"{sid}.jsonl"
        # Crea el fichero vacío si no existe (sesión nueva).
        ruta.touch(exist_ok=True)
        return cls(ruta)

    @classmethod
    def cargar(cls, ruta: Path) -> Sesion:
        ruta = Path(ruta)
        if not ruta.is_file():
            raise FileNotFoundError(f"sesión inexistente: {ruta}")
        return cls(ruta)

    @classmethod
    def ultima(cls, dir_sesiones: Path) -> Sesion | None:
        dir_sesiones = Path(dir_sesiones)
        if not dir_sesiones.is_dir():
            return None
        ficheros = sorted(dir_sesiones.glob("*.jsonl"))
        if not ficheros:
            return None
        # Más reciente por mtime (robusto aunque el id no sea temporal).
        ultimo = max(ficheros, key=lambda p: p.stat().st_mtime)
        return cls(ultimo)

    # -- Escritura -------------------------------------------------------------

    def _append(self, registro: dict[str, Any]) -> None:
        registro.setdefault("timestamp", _ahora())
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    def registrar_usuario(self, content: str) -> None:
        self._append({"tipo": "user", "content": content})

    def registrar_asistente(self, content: str) -> None:
        self._append({"tipo": "assistant", "content": content})

    def registrar_tool_call(self, nombre_api: str, argumentos: dict[str, Any]) -> None:
        self._append({"tipo": "tool_call", "nombre_api": nombre_api, "argumentos": argumentos})

    def registrar_tool_result(
        self, nombre_api: str, resultado: dict[str, Any], *, ok: bool = True
    ) -> None:
        self._append(
            {"tipo": "tool_result", "nombre_api": nombre_api, "ok": ok, "resultado": resultado}
        )

    # -- Lectura ---------------------------------------------------------------

    def historial(self) -> list[dict[str, Any]]:
        if not self.ruta.is_file():
            return []
        registros: list[dict[str, Any]] = []
        with self.ruta.open(encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                registros.append(json.loads(linea))
        return registros

    def __len__(self) -> int:
        return len(self.historial())
