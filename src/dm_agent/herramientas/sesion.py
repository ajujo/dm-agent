"""Tools de cierre de sesión (F4.4).

`sesion.cerrar`, `sesion.cerrar_texto`.

Generan con el LLM un resumen de cierre + una preparación de la próxima sesión y
los guardan como `EntradaNarrativa` (`resumen` y `siguiente_sesion`) en la
bitácora. No registran evento mecánico. No fuerzan que el LLM las use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.llm.cliente import ErrorLLM
from dm_agent.memoria.cierre_sesion import CierreSesionNarrativa, ErrorCierre
from dm_agent.persistencia.sesion import Sesion


def _salida(entradas: dict[str, Any]) -> dict[str, Any]:
    return {
        "resumen": entradas["resumen"].model_dump(mode="json"),
        "preparacion": entradas["preparacion"].model_dump(mode="json"),
    }


class _ToolSesionBase:
    requiere: list[str] = []
    modifica = ["narrativa"]

    def __init__(self, cierre: CierreSesionNarrativa) -> None:
        self.cierre = cierre

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""


class _ToolSesionCerrar(_ToolSesionBase):
    nombre = "sesion.cerrar"
    descripcion = (
        "Cierra una sesión por su id: lee su transcripción, genera con el LLM un resumen de "
        "cierre y la preparación de la próxima sesión, y los guarda en la memoria narrativa."
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "sesion_id": {"type": "string"},
        },
        "required": ["campaña_id", "sesion_id"],
        "additionalProperties": False,
    }

    def __init__(self, cierre: CierreSesionNarrativa, dir_sesiones: Path | str) -> None:
        super().__init__(cierre)
        self.dir_sesiones = Path(dir_sesiones)

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        sesion_id = args.get("sesion_id")
        if not campaña_id or not sesion_id:
            return ResultadoHerramienta(ok=False, errores=["faltan 'campaña_id' y/o 'sesion_id'"])
        ruta = self.dir_sesiones / f"{sesion_id}.jsonl"
        try:
            sesion = Sesion.cargar(ruta)
        except FileNotFoundError:
            return ResultadoHerramienta(ok=False, errores=[f"sesión no existe: {sesion_id!r}"])
        texto = sesion.texto_para_resumen()
        try:
            entradas = self.cierre.cerrar_sesion(campaña_id, sesion_id, texto)
        except ErrorCierre as e:
            return ResultadoHerramienta(ok=False, errores=[str(e)])
        except ErrorLLM as e:
            return ResultadoHerramienta(ok=False, errores=[f"error del modelo/endpoint: {e}"])
        return ResultadoHerramienta(ok=True, datos=_salida(entradas))


class _ToolSesionCerrarTexto(_ToolSesionBase):
    nombre = "sesion.cerrar_texto"
    descripcion = (
        "Cierra una sesión a partir de un texto proporcionado: genera resumen de cierre y "
        "preparación de la próxima sesión y los guarda en la memoria narrativa."
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "sesion_id": {"type": "string"},
            "texto": {"type": "string"},
        },
        "required": ["campaña_id", "sesion_id", "texto"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        sesion_id = args.get("sesion_id")
        texto = args.get("texto")
        if not campaña_id or not sesion_id:
            return ResultadoHerramienta(ok=False, errores=["faltan 'campaña_id' y/o 'sesion_id'"])
        try:
            entradas = self.cierre.cerrar_sesion(campaña_id, sesion_id, texto or "")
        except ErrorCierre as e:
            return ResultadoHerramienta(ok=False, errores=[str(e)])
        except ErrorLLM as e:
            return ResultadoHerramienta(ok=False, errores=[f"error del modelo/endpoint: {e}"])
        return ResultadoHerramienta(ok=True, datos=_salida(entradas))


def crear_tools_sesion(
    cierre: CierreSesionNarrativa, dir_sesiones: Path | str
) -> list[Any]:
    """Crea las tools de cierre de sesión."""
    return [_ToolSesionCerrar(cierre, dir_sesiones), _ToolSesionCerrarTexto(cierre)]
