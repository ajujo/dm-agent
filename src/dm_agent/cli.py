"""CLI de dm-agent (F2.2): REPL mínima jugable.

`dm-agent` arranca un chat por turnos contra un endpoint LLM OpenAI-compatible,
con la tool `dados_tirar` disponible. Todavía NO hay ficha, combate, inventario,
RAG ni memoria avanzada (ver docs/PLAN_FASES.md).
"""

from __future__ import annotations

import argparse

from dm_agent import __version__
from dm_agent.llm.cliente import ErrorLLM
from dm_agent.nucleo.bucle import SesionInteractiva, repl


def _crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dm-agent",
        description="Director de Juego local-first (REPL mínima, F2.2).",
    )
    parser.add_argument("--version", action="version", version=f"dm-agent {__version__}")
    parser.add_argument(
        "--perfil",
        default=None,
        help="Perfil de modelo (rapido | grande | pequeno | …). Por defecto el de proyecto.json.",
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--nueva", action="store_true", help="Empieza una sesión nueva (por defecto).")
    grupo.add_argument("--continuar", action="store_true", help="Continúa la última sesión guardada.")
    parser.add_argument("--debug", action="store_true", help="Activa la traza de depuración.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _crear_parser()
    args = parser.parse_args(argv)

    try:
        ctx = SesionInteractiva(perfil=args.perfil, debug=args.debug)
    except ErrorLLM as e:
        print(f"No se pudo iniciar dm-agent: {e}")
        print("Revisa config/ (perfiles.json, modelos.json, proyecto.json).")
        return 2

    if args.continuar:
        print(ctx.continuar_ultima())
    else:
        print(ctx.nueva_sesion())

    return repl(ctx)
