"""Tools de resumen narrativo (F4.2).

`resumen.entradas`, `resumen.texto`.

Generan un resumen con LLM (`ResumidorNarrativo`) y lo guardan como
`EntradaNarrativa(tipo="resumen")` en la bitácora. No registran evento mecánico.
No hay inyección automática al contexto todavía (F4.3).
"""

from __future__ import annotations

from typing import Any

from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.llm.cliente import ErrorLLM
from dm_agent.memoria.resumen import ErrorResumen, ResumidorNarrativo


class _ToolResumenBase:
    requiere: list[str] = []
    modifica: list[str] = ["narrativa"]

    def __init__(self, resumidor: ResumidorNarrativo) -> None:
        self.resumidor = resumidor

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""


class _ToolResumenEntradas(_ToolResumenBase):
    nombre = "resumen.entradas"
    descripcion = (
        "Resume con el LLM las últimas entradas de la bitácora narrativa y guarda el "
        "resultado como una entrada de tipo 'resumen'. Útil para continuidad entre sesiones."
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "limite": {"type": "integer", "minimum": 1, "default": 20},
            "sesion_id": {"type": "string"},
        },
        "required": ["campaña_id"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        if not campaña_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'campaña_id'"])
        limite = args.get("limite", 20)
        if isinstance(limite, bool) or not isinstance(limite, int) or limite < 1:
            return ResultadoHerramienta(ok=False, errores=["'limite' debe ser un entero >= 1"])
        try:
            entrada = self.resumidor.resumir_entradas(
                campaña_id, limite=limite, sesion_id=args.get("sesion_id")
            )
        except ErrorResumen as e:
            return ResultadoHerramienta(ok=False, errores=[str(e)])
        except ErrorLLM as e:
            return ResultadoHerramienta(ok=False, errores=[f"error del modelo/endpoint: {e}"])
        return ResultadoHerramienta(ok=True, datos={"entrada": entrada.model_dump(mode="json")})


class _ToolResumenTexto(_ToolResumenBase):
    nombre = "resumen.texto"
    descripcion = (
        "Resume con el LLM un texto de escena/sesión proporcionado y guarda el resultado "
        "como una entrada de tipo 'resumen'."
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "texto": {"type": "string"},
            "sesion_id": {"type": "string"},
        },
        "required": ["campaña_id", "texto"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        texto = args.get("texto")
        if not campaña_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'campaña_id'"])
        try:
            entrada = self.resumidor.resumir_texto(
                campaña_id, texto or "", sesion_id=args.get("sesion_id")
            )
        except ErrorResumen as e:
            return ResultadoHerramienta(ok=False, errores=[str(e)])
        except ErrorLLM as e:
            return ResultadoHerramienta(ok=False, errores=[f"error del modelo/endpoint: {e}"])
        return ResultadoHerramienta(ok=True, datos={"entrada": entrada.model_dump(mode="json")})


def crear_tools_resumen(resumidor: ResumidorNarrativo) -> list[Any]:
    """Crea las tools de resumen enlazadas a un `ResumidorNarrativo`."""
    return [_ToolResumenEntradas(resumidor), _ToolResumenTexto(resumidor)]
