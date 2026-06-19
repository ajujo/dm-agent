"""Tool de dados — versión Fase 1, determinista con semilla opcional.

Soporta:
- expresiones tipo "1d20+3", "2d6-1", "1d100"
- modo ventaja (toma el mayor de 2dN)
- modo desventaja (toma el menor de 2dN)
- semilla reproducible (para tests y debugging)

Nota: portado/simplificado del `motor/dados.py` del proyecto dnd5e-framework.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.nucleo.eventos import crear_evento

_REGEX_TIRADA = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


class TipoTirada(StrEnum):
    NORMAL = "normal"
    VENTAJA = "ventaja"
    DESVENTAJA = "desventaja"


@dataclass(slots=True)
class ResultadoTirada:
    expresion: str
    dados: list[int]
    modificador: int
    total: int
    tipo: TipoTirada = TipoTirada.NORMAL
    dados_descartados: list[int] = field(default_factory=list)
    critico: bool = False
    pifia: bool = False


def _parse_expresion(expr: str) -> tuple[int, int, int]:
    m = _REGEX_TIRADA.match(expr)
    if not m:
        raise ValueError(f"expresión inválida: {expr!r}")
    n = int(m.group(1))
    caras = int(m.group(2))
    mod_raw = m.group(3)
    mod = int(mod_raw.replace(" ", "")) if mod_raw else 0
    if n <= 0 or caras <= 0:
        raise ValueError(f"valores no positivos en {expr!r}")
    if n > 100 or caras > 1000:
        raise ValueError(f"valores fuera de rango razonable en {expr!r}")
    return n, caras, mod


def _construir_rng(semilla: int | None) -> random.Random:
    return random.Random(semilla)


def tirar(expr: str, semilla: int | None = None) -> ResultadoTirada:
    """Tirada normal."""
    n, caras, mod = _parse_expresion(expr)
    rng = _construir_rng(semilla)
    dados = [rng.randint(1, caras) for _ in range(n)]
    total = sum(dados) + mod
    critico = caras == 20 and n == 1 and dados[0] == 20
    pifia = caras == 20 and n == 1 and dados[0] == 1
    return ResultadoTirada(
        expresion=expr,
        dados=dados,
        modificador=mod,
        total=total,
        tipo=TipoTirada.NORMAL,
        critico=critico,
        pifia=pifia,
    )


def _tirar_con_ventaja_o_desventaja(
    expr: str, *, ventaja: bool, semilla: int | None
) -> ResultadoTirada:
    n, caras, mod = _parse_expresion(expr)
    if n != 1:
        raise ValueError("ventaja/desventaja requieren una sola tirada base (ej. 1d20)")
    rng = _construir_rng(semilla)
    t1 = rng.randint(1, caras)
    t2 = rng.randint(1, caras)
    elegido = max(t1, t2) if ventaja else min(t1, t2)
    descartado = min(t1, t2) if ventaja else max(t1, t2)
    total = elegido + mod
    critico = caras == 20 and elegido == 20
    pifia = caras == 20 and elegido == 1
    return ResultadoTirada(
        expresion=expr,
        dados=[elegido],
        modificador=mod,
        total=total,
        tipo=TipoTirada.VENTAJA if ventaja else TipoTirada.DESVENTAJA,
        dados_descartados=[descartado],
        critico=critico,
        pifia=pifia,
    )


def tirar_ventaja(expr: str, semilla: int | None = None) -> ResultadoTirada:
    return _tirar_con_ventaja_o_desventaja(expr, ventaja=True, semilla=semilla)


def tirar_desventaja(expr: str, semilla: int | None = None) -> ResultadoTirada:
    return _tirar_con_ventaja_o_desventaja(expr, ventaja=False, semilla=semilla)


# --- Herramienta (envoltorio del registro) -----------------------------------


class _ToolDados:
    nombre = "dados.tirar"
    descripcion = (
        "Tira dados con una expresión NdM[+/-mod]. Modo: normal | ventaja | desventaja. "
        "Acepta semilla opcional para reproducibilidad. Devuelve dados individuales, modificador y total."
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "expresion": {
                "type": "string",
                "description": "Expresión NdM[+/-mod] (ej. '1d20+3', '2d6-1').",
            },
            "modo": {
                "type": "string",
                "enum": ["normal", "ventaja", "desventaja"],
                "default": "normal",
            },
            "semilla": {
                "type": "integer",
                "description": "Semilla opcional. Útil para tests y depuración.",
            },
        },
        "required": ["expresion"],
        "additionalProperties": False,
    }
    requiere: list[str] = []
    modifica: list[str] = ["log_eventos"]

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        expr = args.get("expresion")
        modo = args.get("modo", "normal")
        semilla = args.get("semilla")
        if not isinstance(expr, str):
            return ResultadoHerramienta(ok=False, errores=["'expresion' debe ser string"])
        try:
            if modo == "normal":
                r = tirar(expr, semilla=semilla)
            elif modo == "ventaja":
                r = tirar_ventaja(expr, semilla=semilla)
            elif modo == "desventaja":
                r = tirar_desventaja(expr, semilla=semilla)
            else:
                return ResultadoHerramienta(ok=False, errores=[f"modo desconocido: {modo!r}"])
        except ValueError as e:
            return ResultadoHerramienta(ok=False, errores=[str(e)])

        evt = crear_evento(
            "dados_tirados",
            tool="dados.tirar",
            datos={
                "expresion": r.expresion,
                "dados": r.dados,
                "modificador": r.modificador,
                "total": r.total,
                "tipo": r.tipo.value,
                "critico": r.critico,
                "pifia": r.pifia,
                "semilla": semilla,
            },
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "expresion": r.expresion,
                "dados": r.dados,
                "dados_descartados": r.dados_descartados,
                "modificador": r.modificador,
                "total": r.total,
                "tipo": r.tipo.value,
                "critico": r.critico,
                "pifia": r.pifia,
            },
            eventos=[evt],
        )


def crear_tool_dados() -> _ToolDados:
    return _ToolDados()
