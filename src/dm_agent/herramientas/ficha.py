"""Tools deterministas de ficha (F3.3).

`ficha.leer`, `ficha.guardar`, `ficha.validar`, `ficha.actualizar`, `ficha.listar`.

El LLM nunca modifica la ficha directamente: toda lectura/escritura pasa por
estas tools, que validan con el esquema `Ficha` (pydantic) y persisten mediante
`GestorEstado`. Coherente con D17 (D&D 5.5 narrativo en solitario): esto es
persistencia de ficha, NO motor de HP/XP, combate ni reglas.

Las tools reciben un `GestorEstado` inyectado en construcción (igual que la tool
de dados se crea por factory). `ctx` del contrato de herramientas no se usa aquí.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from dm_agent.esquemas.ficha import Ficha
from dm_agent.estado.gestor import (
    ErrorEstado,
    ErrorEstadoNoEncontrado,
    GestorEstado,
)
from dm_agent.herramientas.base import ResultadoHerramienta

# Campos de primer nivel que `ficha.actualizar` puede tocar: todos menos los
# inmutables. `atributos` se permite reemplazar entero (no parcial) en F3.3.
_CAMPOS_INMUTABLES = {"id", "version_schema"}
_CAMPOS_ACTUALIZABLES = set(Ficha.model_fields) - _CAMPOS_INMUTABLES

_SCHEMA_OBJETO_FICHA = {
    "type": "object",
    "description": "Ficha completa en formato JSON conforme al esquema Ficha.",
}


def _ruta_relativa(gestor: GestorEstado, ruta) -> str:
    try:
        return ruta.relative_to(gestor.raiz).as_posix()
    except ValueError:
        return ruta.name


def _error_validacion(e: ValidationError) -> ResultadoHerramienta:
    # Mensaje compacto, sin traceback.
    errores = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()]
    return ResultadoHerramienta(ok=False, errores=errores or [str(e)])


class _ToolFichaBase:
    requiere: list[str] = []
    modifica: list[str] = []

    def __init__(self, gestor: GestorEstado) -> None:
        self.gestor = gestor

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""


class _ToolFichaLeer(_ToolFichaBase):
    nombre = "ficha.leer"
    descripcion = "Lee una ficha persistida de una campaña. No crea ni modifica nada."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "personaje_id": {"type": "string"},
        },
        "required": ["campaña_id", "personaje_id"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        personaje_id = args.get("personaje_id")
        if not campaña_id or not personaje_id:
            return ResultadoHerramienta(ok=False, errores=["faltan 'campaña_id' y/o 'personaje_id'"])
        if not self.gestor.existe_campaña(campaña_id):
            return ResultadoHerramienta(ok=False, errores=[f"campaña no existe: {campaña_id!r}"])
        try:
            ficha = self.gestor.cargar_ficha(campaña_id, personaje_id)
        except ErrorEstadoNoEncontrado:
            return ResultadoHerramienta(ok=False, errores=[f"ficha no existe: {personaje_id!r}"])
        except ErrorEstado as e:
            return ResultadoHerramienta(ok=False, errores=[f"ficha inválida: {e}"])
        return ResultadoHerramienta(ok=True, datos={"ficha": ficha.model_dump(mode="json")})


class _ToolFichaGuardar(_ToolFichaBase):
    nombre = "ficha.guardar"
    descripcion = "Valida una ficha completa y la persiste en la campaña (crea o sobrescribe)."
    modifica = ["ficha"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "ficha": _SCHEMA_OBJETO_FICHA,
        },
        "required": ["campaña_id", "ficha"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        datos_ficha = args.get("ficha")
        if not campaña_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'campaña_id'"])
        if not isinstance(datos_ficha, dict):
            return ResultadoHerramienta(ok=False, errores=["'ficha' debe ser un objeto"])
        try:
            ficha = Ficha.model_validate(datos_ficha)
        except ValidationError as e:
            return _error_validacion(e)
        ruta = self.gestor.guardar_ficha(campaña_id, ficha)
        return ResultadoHerramienta(
            ok=True,
            datos={"personaje_id": ficha.id, "ruta_relativa": _ruta_relativa(self.gestor, ruta)},
        )


class _ToolFichaValidar(_ToolFichaBase):
    nombre = "ficha.validar"
    descripcion = "Valida una ficha contra el esquema. No persiste nada."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"ficha": _SCHEMA_OBJETO_FICHA},
        "required": ["ficha"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        datos_ficha = args.get("ficha")
        if not isinstance(datos_ficha, dict):
            return ResultadoHerramienta(ok=False, errores=["'ficha' debe ser un objeto"])
        try:
            ficha = Ficha.model_validate(datos_ficha)
        except ValidationError as e:
            return _error_validacion(e)
        return ResultadoHerramienta(ok=True, datos={"ficha": ficha.model_dump(mode="json")})


class _ToolFichaActualizar(_ToolFichaBase):
    nombre = "ficha.actualizar"
    descripcion = (
        "Aplica cambios de primer nivel a una ficha existente, valida el resultado y lo guarda. "
        "No permite cambiar 'id' ni 'version_schema'. 'atributos' solo se reemplaza entero."
    )
    modifica = ["ficha"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "cambios": {
                "type": "object",
                "description": (
                    "Campos de primer nivel a modificar. Permitidos: nombre, clase, nivel, raza, "
                    "trasfondo, atributos (entero), hp_max, hp_actual, ca, bonificador_competencia, "
                    "xp, condiciones, inventario, notas."
                ),
            },
        },
        "required": ["campaña_id", "personaje_id", "cambios"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        personaje_id = args.get("personaje_id")
        cambios = args.get("cambios")
        if not campaña_id or not personaje_id:
            return ResultadoHerramienta(ok=False, errores=["faltan 'campaña_id' y/o 'personaje_id'"])
        if not isinstance(cambios, dict) or not cambios:
            return ResultadoHerramienta(ok=False, errores=["'cambios' debe ser un objeto no vacío"])

        inmutables = _CAMPOS_INMUTABLES & cambios.keys()
        if inmutables:
            return ResultadoHerramienta(
                ok=False, errores=[f"campos no modificables: {sorted(inmutables)}"]
            )
        desconocidos = cambios.keys() - _CAMPOS_ACTUALIZABLES
        if desconocidos:
            return ResultadoHerramienta(
                ok=False, errores=[f"campos desconocidos o no permitidos: {sorted(desconocidos)}"]
            )

        if not self.gestor.existe_campaña(campaña_id):
            return ResultadoHerramienta(ok=False, errores=[f"campaña no existe: {campaña_id!r}"])
        try:
            ficha = self.gestor.cargar_ficha(campaña_id, personaje_id)
        except ErrorEstadoNoEncontrado:
            return ResultadoHerramienta(ok=False, errores=[f"ficha no existe: {personaje_id!r}"])
        except ErrorEstado as e:
            return ResultadoHerramienta(ok=False, errores=[f"ficha inválida: {e}"])

        datos = ficha.model_dump()
        datos.update(cambios)
        try:
            actualizada = Ficha.model_validate(datos)
        except ValidationError as e:
            return _error_validacion(e)

        self.gestor.guardar_ficha(campaña_id, actualizada)
        return ResultadoHerramienta(ok=True, datos={"ficha": actualizada.model_dump(mode="json")})


class _ToolFichaListar(_ToolFichaBase):
    nombre = "ficha.listar"
    descripcion = "Lista los identificadores de personaje con ficha persistida en una campaña."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"campaña_id": {"type": "string"}},
        "required": ["campaña_id"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        if not campaña_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'campaña_id'"])
        if not self.gestor.existe_campaña(campaña_id):
            return ResultadoHerramienta(ok=False, errores=[f"campaña no existe: {campaña_id!r}"])
        return ResultadoHerramienta(
            ok=True, datos={"personajes": self.gestor.listar_fichas(campaña_id)}
        )


def crear_tools_ficha(gestor: GestorEstado) -> list[Any]:
    """Crea las cinco tools de ficha enlazadas a un `GestorEstado`."""
    return [
        _ToolFichaLeer(gestor),
        _ToolFichaGuardar(gestor),
        _ToolFichaValidar(gestor),
        _ToolFichaActualizar(gestor),
        _ToolFichaListar(gestor),
    ]
