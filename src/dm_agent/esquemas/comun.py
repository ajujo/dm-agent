"""Tipos y utilidades compartidas por los esquemas (F3.1)."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator


def _exigir_no_vacio(v: str) -> str:
    if not v.strip():
        raise ValueError("no puede estar vacío")
    return v


# Cadena que, una vez que es `str`, no puede ser vacía ni solo espacios.
# Combinable con `| None` para campos opcionales que, si existen, no van vacíos.
CadenaNoVacia = Annotated[str, AfterValidator(_exigir_no_vacio)]
