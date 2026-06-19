"""Tools de entidades narrativas estructuradas (F4.6).

`entidad.guardar_*` / `entidad.listar_*` para PNJ, lugares, pistas, objetivos y
frentes abiertos. Complementan `narrativa.*` (F4.1): la bitácora dice qué pasó,
estas tools dicen quién/qué existe y en qué estado está *ahora*. No registran
eventos mecánicos ni entradas narrativas.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from dm_agent.esquemas.entidades import PNJ, FrenteAbierto, Lugar, Objetivo, Pista
from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.memoria.entidades import GestorEntidadesNarrativas

_PROPS_BASE: dict[str, Any] = {
    "campaña_id": {"type": "string"},
    "id": {"type": "string"},
    "nombre": {"type": "string"},
    "descripcion": {"type": "string"},
    "estado": {"type": "string"},
    "tags": {"type": "array", "items": {"type": "string"}},
    "importancia": {"type": "integer", "minimum": 1, "maximum": 5},
    "notas": {"type": "string"},
}
_REQUERIDOS_BASE = ["campaña_id", "id", "nombre"]

_PROPS_PNJ = {
    **_PROPS_BASE,
    "rol": {"type": "string"},
    "actitud": {"type": "string"},
    "ubicacion_id": {"type": "string"},
    "relacion_con_personaje": {"type": "string"},
}
_PROPS_LUGAR = {
    **_PROPS_BASE,
    "tipo": {"type": "string"},
    "conectado_con": {"type": "array", "items": {"type": "string"}},
}
_PROPS_PISTA = {
    **_PROPS_BASE,
    "origen": {"type": "string"},
    "relacionada_con": {"type": "string"},
    "resuelta": {"type": "boolean"},
}
_PROPS_OBJETIVO = {
    **_PROPS_BASE,
    "prioridad": {"type": "integer"},
    "relacionado_con": {"type": "string"},
}
_PROPS_FRENTE = {
    **_PROPS_BASE,
    "amenaza": {"type": "string"},
    "reloj": {"type": "integer", "minimum": 0, "maximum": 6},
    "consecuencias": {"type": "string"},
    "relacionado_con": {"type": "string"},
}


def _errores_validacion(e: ValidationError) -> list[str]:
    return [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()]


class _ToolEntidadGuardarBase:
    requiere: list[str] = []
    modifica: list[str] = ["entidades"]

    def __init__(
        self,
        gestor: GestorEntidadesNarrativas,
        *,
        nombre: str,
        descripcion: str,
        props: dict[str, Any],
        modelo: type[BaseModel],
        metodo_guardar: str,
        clave: str,
    ) -> None:
        self.gestor = gestor
        self.nombre = nombre
        self.descripcion = descripcion
        self.schema: dict[str, Any] = {
            "type": "object",
            "properties": props,
            "required": list(_REQUERIDOS_BASE),
            "additionalProperties": False,
        }
        self._modelo = modelo
        self._metodo_guardar = metodo_guardar
        self._clave = clave

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        if not campaña_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'campaña_id'"])
        resto = {k: v for k, v in args.items() if k != "campaña_id"}
        try:
            entidad = self._modelo.model_validate(resto)
        except ValidationError as e:
            return ResultadoHerramienta(ok=False, errores=_errores_validacion(e))
        guardada = getattr(self.gestor, self._metodo_guardar)(campaña_id, entidad)
        return ResultadoHerramienta(ok=True, datos={self._clave: guardada.model_dump(mode="json")})


class _ToolEntidadListarBase:
    requiere: list[str] = []
    modifica: list[str] = []

    def __init__(
        self,
        gestor: GestorEntidadesNarrativas,
        *,
        nombre: str,
        descripcion: str,
        metodo_listar: str,
        clave: str,
    ) -> None:
        self.gestor = gestor
        self.nombre = nombre
        self.descripcion = descripcion
        self.schema: dict[str, Any] = {
            "type": "object",
            "properties": {"campaña_id": {"type": "string"}},
            "required": ["campaña_id"],
            "additionalProperties": False,
        }
        self._metodo_listar = metodo_listar
        self._clave = clave

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        if not campaña_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'campaña_id'"])
        entidades = getattr(self.gestor, self._metodo_listar)(campaña_id)
        return ResultadoHerramienta(
            ok=True, datos={self._clave: [e.model_dump(mode="json") for e in entidades]}
        )


_TIPOS: list[dict[str, Any]] = [
    {
        "etiqueta": "PNJ",
        "modelo": PNJ,
        "props": _PROPS_PNJ,
        "nombre_guardar": "entidad.guardar_pnj",
        "nombre_listar": "entidad.listar_pnj",
        "metodo_guardar": "guardar_pnj",
        "metodo_listar": "listar_pnj",
        "clave": "pnj",
    },
    {
        "etiqueta": "lugar",
        "modelo": Lugar,
        "props": _PROPS_LUGAR,
        "nombre_guardar": "entidad.guardar_lugar",
        "nombre_listar": "entidad.listar_lugares",
        "metodo_guardar": "guardar_lugar",
        "metodo_listar": "listar_lugares",
        "clave": "lugar",
        "clave_listar": "lugares",
    },
    {
        "etiqueta": "pista",
        "modelo": Pista,
        "props": _PROPS_PISTA,
        "nombre_guardar": "entidad.guardar_pista",
        "nombre_listar": "entidad.listar_pistas",
        "metodo_guardar": "guardar_pista",
        "metodo_listar": "listar_pistas",
        "clave": "pista",
        "clave_listar": "pistas",
    },
    {
        "etiqueta": "objetivo",
        "modelo": Objetivo,
        "props": _PROPS_OBJETIVO,
        "nombre_guardar": "entidad.guardar_objetivo",
        "nombre_listar": "entidad.listar_objetivos",
        "metodo_guardar": "guardar_objetivo",
        "metodo_listar": "listar_objetivos",
        "clave": "objetivo",
        "clave_listar": "objetivos",
    },
    {
        "etiqueta": "frente abierto",
        "modelo": FrenteAbierto,
        "props": _PROPS_FRENTE,
        "nombre_guardar": "entidad.guardar_frente",
        "nombre_listar": "entidad.listar_frentes",
        "metodo_guardar": "guardar_frente",
        "metodo_listar": "listar_frentes",
        "clave": "frente",
        "clave_listar": "frentes",
    },
]


def crear_tools_entidades(gestor: GestorEntidadesNarrativas) -> list[Any]:
    """Crea las 10 tools de entidades (guardar/listar × 5 tipos) enlazadas al gestor."""
    tools: list[Any] = []
    for t in _TIPOS:
        tools.append(
            _ToolEntidadGuardarBase(
                gestor,
                nombre=t["nombre_guardar"],
                descripcion=(
                    f"Guarda (crea o reemplaza por id) un/a {t['etiqueta']} de la campaña. "
                    "No registra eventos mecánicos ni entradas narrativas."
                ),
                props=t["props"],
                modelo=t["modelo"],
                metodo_guardar=t["metodo_guardar"],
                clave=t["clave"],
            )
        )
        tools.append(
            _ToolEntidadListarBase(
                gestor,
                nombre=t["nombre_listar"],
                descripcion=(
                    f"Lista los/las {t['etiqueta']} conocidos de la campaña, "
                    "ordenados por importancia descendente y luego nombre. No modifica nada."
                ),
                metodo_listar=t["metodo_listar"],
                clave=t.get("clave_listar", t["clave"]),
            )
        )
    return tools
