#!/usr/bin/env python3
"""Validación offline de la configuración de perfiles/modelos/proyecto.

Uso:
    python scripts/check_perfil.py [--config DIR]

Por defecto valida `config/` relativo a la raíz del repo. No realiza llamadas
de red: comprueba únicamente coherencia estructural. La validación en vivo de
endpoints es Fase 2.

Códigos de salida:
    0  -> configuración correcta
    1  -> se han encontrado errores de configuración
    2  -> error de uso / ruta inexistente
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite ejecutar el script sin instalar el paquete (añade src/ al path).
_RAIZ = Path(__file__).resolve().parent.parent
_SRC = _RAIZ / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dm_agent.config.validacion import validar_directorio_config  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida la configuración de dm-agent (offline).")
    parser.add_argument(
        "--config",
        type=Path,
        default=_RAIZ / "config",
        help="Directorio de configuración (por defecto: ./config)",
    )
    args = parser.parse_args(argv)

    config_dir: Path = args.config
    if not config_dir.is_dir():
        print(f"✗ directorio de configuración inexistente: {config_dir}", file=sys.stderr)
        return 2

    errores = validar_directorio_config(config_dir)
    if errores:
        print(f"✗ configuración inválida ({len(errores)} error(es)):")
        for e in errores:
            print(f"  - {e}")
        return 1

    print(f"✓ configuración válida en {config_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
