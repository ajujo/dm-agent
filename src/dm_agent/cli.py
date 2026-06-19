"""CLI mínima — placeholder hasta Fase 2."""

from __future__ import annotations

import argparse

from dm_agent import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dm-agent")
    parser.add_argument("--version", action="version", version=f"dm-agent {__version__}")
    parser.add_argument(
        "--perfil",
        default=None,
        help="Perfil de modelo a usar (rapido | grande | pequeno). Disponible a partir de Fase 2.",
    )
    parser.parse_args(argv)
    print("dm-agent: esqueleto (Fase 1). La REPL llega en la Fase 2 — ver docs/PLAN_FASES.md.")
    return 0
