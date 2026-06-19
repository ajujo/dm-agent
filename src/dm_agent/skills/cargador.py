"""Cargador de skills — escanea SKILL.md, parsea frontmatter YAML.

Versión Fase 1: solo descubrimiento + metadata. El router viene en Fase 8.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class SkillInvalida(ValueError):
    pass


@dataclass(slots=True)
class SkillMeta:
    slug: str
    ruta: Path
    nombre: str
    descripcion: str
    version: str
    modo: str
    requiere_tools: list[str]
    lee: list[str]
    modifica: list[str]
    tono_aplicable: list[str]
    nivel_juego: list[str]
    cuerpo: str

    @property
    def encabezado(self) -> dict[str, Any]:
        return {
            "name": self.nombre,
            "version": self.version,
            "modo": self.modo,
            "requiere_tools": self.requiere_tools,
            "lee": self.lee,
            "modifica": self.modifica,
        }


_CAMPOS_REQUERIDOS = ("name", "description", "version", "modo")


def _parse_skill_md(ruta: Path) -> SkillMeta:
    texto = ruta.read_text(encoding="utf-8")
    if not texto.startswith("---"):
        raise SkillInvalida(f"{ruta}: falta frontmatter YAML al inicio")
    partes = texto.split("---", 2)
    if len(partes) < 3:
        raise SkillInvalida(f"{ruta}: frontmatter mal cerrado (faltan dos '---')")
    front_yaml, cuerpo = partes[1], partes[2].strip()
    try:
        front: dict[str, Any] = yaml.safe_load(front_yaml) or {}
    except yaml.YAMLError as e:
        raise SkillInvalida(f"{ruta}: YAML inválido: {e}") from e

    for campo in _CAMPOS_REQUERIDOS:
        if campo not in front:
            raise SkillInvalida(f"{ruta}: falta campo requerido '{campo}'")

    slug = ruta.parent.name
    return SkillMeta(
        slug=slug,
        ruta=ruta,
        nombre=str(front["name"]),
        descripcion=str(front["description"]),
        version=str(front["version"]),
        modo=str(front["modo"]),
        requiere_tools=list(front.get("requiere_tools") or []),
        lee=list(front.get("lee") or []),
        modifica=list(front.get("modifica") or []),
        tono_aplicable=list(front.get("tono_aplicable") or []),
        nivel_juego=list(front.get("nivel_juego") or []),
        cuerpo=cuerpo,
    )


class CargadorSkills:
    """Descubre skills en `raiz/**/SKILL.md` y cachea su metadata."""

    def __init__(self, raiz: Path | str) -> None:
        self.raiz = Path(raiz)
        self._cache: dict[str, SkillMeta] | None = None

    def descubrir(self) -> dict[str, SkillMeta]:
        if not self.raiz.is_dir():
            self._cache = {}
            return self._cache
        encontradas: dict[str, SkillMeta] = {}
        for ruta in sorted(self.raiz.glob("**/SKILL.md")):
            meta = _parse_skill_md(ruta)
            if meta.slug in encontradas:
                raise SkillInvalida(
                    f"slug duplicado: {meta.slug} en {ruta} y {encontradas[meta.slug].ruta}"
                )
            encontradas[meta.slug] = meta
        self._cache = encontradas
        return encontradas

    def listar(self) -> list[SkillMeta]:
        if self._cache is None:
            self.descubrir()
        assert self._cache is not None
        return list(self._cache.values())

    def obtener(self, slug: str) -> SkillMeta:
        if self._cache is None:
            self.descubrir()
        assert self._cache is not None
        if slug not in self._cache:
            raise KeyError(slug)
        return self._cache[slug]
