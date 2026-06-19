"""Tools de memoria narrativa (F4.1).

`narrativa.registrar`, `narrativa.reciente`.

Registran y consultan la bitácora narrativa de una campaña (ficción: decisiones,
pistas, PNJ, lugares, consecuencias). NO escriben en `eventos.jsonl` (eso es
mecánica). Coherente con D17 (narrativo en solitario / teatro de la mente).
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from dm_agent.esquemas.narrativa import crear_entrada
from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa

# Campos que el LLM puede aportar; `id`/`timestamp`/`version_schema` se generan.
_CAMPOS_ENTRADA = {"sesion_id", "tipo", "titulo", "contenido", "tags", "importancia", "origen"}


class _ToolNarrativaBase:
    requiere: list[str] = []
    modifica: list[str] = []

    def __init__(self, gestor: GestorMemoriaNarrativa) -> None:
        self.gestor = gestor

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""


class _ToolNarrativaRegistrar(_ToolNarrativaBase):
    nombre = "narrativa.registrar"
    descripcion = (
        "Registra una entrada en la bitácora narrativa de la campaña (decisión, pista, PNJ, "
        "lugar, consecuencia, escena, nota…). No altera estado mecánico ni eventos."
    )
    modifica = ["narrativa"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "sesion_id": {"type": "string"},
            "tipo": {
                "type": "string",
                "description": "escena|decision|pista|pnj|lugar|consecuencia|nota|resumen",
            },
            "titulo": {"type": "string"},
            "contenido": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "importancia": {"type": "integer", "minimum": 1, "maximum": 5},
            "origen": {"type": "string", "enum": ["usuario", "agente", "sistema", "resumen"]},
        },
        "required": ["campaña_id", "tipo", "contenido"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        tipo = args.get("tipo")
        contenido = args.get("contenido")
        if not campaña_id or not tipo or not contenido:
            return ResultadoHerramienta(
                ok=False, errores=["faltan 'campaña_id', 'tipo' y/o 'contenido'"]
            )
        extra = {k: args[k] for k in _CAMPOS_ENTRADA if k in args and k not in ("tipo", "contenido")}
        try:
            entrada = crear_entrada(campaña_id, tipo, contenido, **extra)
        except ValidationError as e:
            return ResultadoHerramienta(
                ok=False,
                errores=[f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()],
            )
        self.gestor.registrar_entrada(entrada)
        return ResultadoHerramienta(ok=True, datos={"entrada": entrada.model_dump(mode="json")})


class _ToolNarrativaReciente(_ToolNarrativaBase):
    nombre = "narrativa.reciente"
    descripcion = "Devuelve las últimas entradas de la bitácora narrativa (JSON + markdown). No modifica nada."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "limite": {"type": "integer", "minimum": 1, "default": 10},
        },
        "required": ["campaña_id"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        if not campaña_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'campaña_id'"])
        limite = args.get("limite", 10)
        if isinstance(limite, bool) or not isinstance(limite, int) or limite < 1:
            return ResultadoHerramienta(ok=False, errores=["'limite' debe ser un entero >= 1"])
        entradas = self.gestor.listar_entradas(campaña_id, limite=limite)
        return ResultadoHerramienta(
            ok=True,
            datos={
                "entradas": [e.model_dump(mode="json") for e in entradas],
                "markdown": self.gestor.ultimas_entradas_markdown(campaña_id, limite=limite),
            },
        )


def crear_tools_narrativa(gestor: GestorMemoriaNarrativa) -> list[Any]:
    """Crea las tools narrativas enlazadas a un `GestorMemoriaNarrativa`."""
    return [_ToolNarrativaRegistrar(gestor), _ToolNarrativaReciente(gestor)]
