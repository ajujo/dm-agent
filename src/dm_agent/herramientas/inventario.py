"""Tools deterministas de inventario simple (F3.6).

`inventario.listar`, `inventario.añadir`, `inventario.quitar`,
`inventario.equipar`, `inventario.desequipar`.

Operan solo sobre `Ficha.inventario` (lista de `ObjetoInventario`). Toda mutación
pasa por validación con `Ficha`, se guarda de forma atómica con `GestorEstado` y
registra un `Evento` canónico en `eventos.jsonl`. Desde F3.6, los cambios
semánticos de inventario deben hacerse con estas tools, no con `ficha.actualizar`
(que es genérica/administrativa).

Coherente con D17 (D&D 5.5 narrativo en solitario): inventario simple y narrativo
(objetos de aventura, llaves, pociones, armas…). NO hay peso/carga, oro/economía,
rareza, attunement, slots ni propiedades complejas.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from dm_agent.esquemas.evento import crear_evento
from dm_agent.esquemas.ficha import Ficha, ObjetoInventario
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import ErrorEstado, ErrorEstadoNoEncontrado, GestorEstado
from dm_agent.herramientas.base import ResultadoHerramienta

_ACTOR_DM = "dm"

_SCHEMA_OBJETO = {
    "type": "object",
    "description": "Objeto de inventario conforme al esquema ObjetoInventario.",
}


def _cantidad_positiva(valor: Any) -> tuple[int | None, ResultadoHerramienta | None]:
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, ResultadoHerramienta(ok=False, errores=["'cantidad' debe ser un entero"])
    if valor <= 0:
        return None, ResultadoHerramienta(ok=False, errores=["'cantidad' debe ser > 0"])
    return valor, None


class _ToolInventarioBase:
    requiere: list[str] = []
    modifica: list[str] = []

    def __init__(self, gestor: GestorEstado, registro_eventos: RegistroEventosEstado) -> None:
        self.gestor = gestor
        self.eventos = registro_eventos

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""

    def _cargar(
        self, campaña_id: str | None, personaje_id: str | None
    ) -> tuple[Ficha | None, ResultadoHerramienta | None]:
        if not campaña_id or not personaje_id:
            return None, ResultadoHerramienta(
                ok=False, errores=["faltan 'campaña_id' y/o 'personaje_id'"]
            )
        if not self.gestor.existe_campaña(campaña_id):
            return None, ResultadoHerramienta(
                ok=False, errores=[f"campaña no existe: {campaña_id!r}"]
            )
        try:
            return self.gestor.cargar_ficha(campaña_id, personaje_id), None
        except ErrorEstadoNoEncontrado:
            return None, ResultadoHerramienta(
                ok=False, errores=[f"ficha no existe: {personaje_id!r}"]
            )
        except ErrorEstado as e:
            return None, ResultadoHerramienta(ok=False, errores=[f"ficha inválida: {e}"])

    def _guardar_con_inventario(
        self, campaña_id: str, ficha: Ficha, inventario: list[dict[str, Any]]
    ) -> Ficha:
        actualizada = Ficha.model_validate({**ficha.model_dump(), "inventario": inventario})
        self.gestor.guardar_ficha(campaña_id, actualizada)
        return actualizada

    def _registrar(self, campaña_id: str, tipo: str, tool: str, datos: dict[str, Any]) -> None:
        self.eventos.registrar(
            campaña_id,
            crear_evento(
                tipo,
                actor=_ACTOR_DM,
                objetivo=datos.get("personaje_id"),
                tool=tool,
                motivo=datos.get("motivo"),
                datos=datos,
            ),
        )

    @staticmethod
    def _salida(ficha: Ficha) -> dict[str, Any]:
        return {
            "personaje_id": ficha.id,
            "inventario": [o.model_dump(mode="json") for o in ficha.inventario],
        }


class _ToolInventarioListar(_ToolInventarioBase):
    nombre = "inventario.listar"
    descripcion = "Lista el inventario de un personaje. No modifica ni registra evento."
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
        ficha, err = self._cargar(args.get("campaña_id"), args.get("personaje_id"))
        if err:
            return err
        assert ficha is not None
        return ResultadoHerramienta(ok=True, datos=self._salida(ficha))


class _ToolInventarioAñadir(_ToolInventarioBase):
    nombre = "inventario.añadir"
    descripcion = (
        "Añade un objeto al inventario. Si ya existe uno con el mismo id, suma cantidades. "
        "Valida el objeto, guarda y registra evento."
    )
    modifica = ["ficha", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "objeto": _SCHEMA_OBJETO,
            "motivo": {"type": "string"},
        },
        "required": ["campaña_id", "personaje_id", "objeto"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        objeto = args.get("objeto")
        if not isinstance(objeto, dict):
            return ResultadoHerramienta(ok=False, errores=["'objeto' debe ser un objeto"])
        try:
            nuevo = ObjetoInventario.model_validate(objeto)
        except ValidationError as e:
            return ResultadoHerramienta(
                ok=False,
                errores=[f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()],
            )

        ficha, err = self._cargar(args.get("campaña_id"), args.get("personaje_id"))
        if err:
            return err
        assert ficha is not None
        campaña_id = args["campaña_id"]
        motivo = args.get("motivo")

        inventario = [o.model_dump() for o in ficha.inventario]
        existente = next((o for o in inventario if o["id"] == nuevo.id), None)
        if existente is not None:
            cantidad_antes = existente["cantidad"]
            existente["cantidad"] += nuevo.cantidad
            if nuevo.descripcion:  # actualiza descripción solo si viene no vacía
                existente["descripcion"] = nuevo.descripcion
            cantidad_despues = existente["cantidad"]
        else:
            inventario.append(nuevo.model_dump())
            cantidad_antes = 0
            cantidad_despues = nuevo.cantidad

        actualizada = self._guardar_con_inventario(campaña_id, ficha, inventario)
        self._registrar(
            campaña_id, "objeto_añadido", self.nombre,
            {
                "personaje_id": ficha.id,
                "objeto_id": nuevo.id,
                "nombre": nuevo.nombre,
                "cantidad": nuevo.cantidad,
                "cantidad_antes": cantidad_antes,
                "cantidad_despues": cantidad_despues,
                "motivo": motivo,
            },
        )
        return ResultadoHerramienta(ok=True, datos=self._salida(actualizada))


class _ToolInventarioQuitar(_ToolInventarioBase):
    nombre = "inventario.quitar"
    descripcion = (
        "Quita unidades de un objeto por id. Si la cantidad llega a 0, elimina el objeto. "
        "Rechaza quitar más de lo disponible. Guarda y registra evento."
    )
    modifica = ["ficha", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "objeto_id": {"type": "string"},
            "cantidad": {"type": "integer", "description": "Unidades a quitar (> 0)."},
            "motivo": {"type": "string"},
        },
        "required": ["campaña_id", "personaje_id", "objeto_id", "cantidad"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        cantidad, err = _cantidad_positiva(args.get("cantidad"))
        if err:
            return err
        objeto_id = args.get("objeto_id")
        if not objeto_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'objeto_id'"])

        ficha, err = self._cargar(args.get("campaña_id"), args.get("personaje_id"))
        if err:
            return err
        assert ficha is not None and cantidad is not None
        campaña_id = args["campaña_id"]
        motivo = args.get("motivo")

        inventario = [o.model_dump() for o in ficha.inventario]
        obj = next((o for o in inventario if o["id"] == objeto_id), None)
        if obj is None:
            return ResultadoHerramienta(ok=False, errores=[f"objeto no existe: {objeto_id!r}"])
        if cantidad > obj["cantidad"]:
            return ResultadoHerramienta(
                ok=False,
                errores=[
                    f"no se puede quitar {cantidad}: solo hay {obj['cantidad']} de {objeto_id!r}"
                ],
            )

        cantidad_antes = obj["cantidad"]
        if cantidad == obj["cantidad"]:
            inventario = [o for o in inventario if o["id"] != objeto_id]
        else:
            obj["cantidad"] -= cantidad
        cantidad_despues = cantidad_antes - cantidad

        actualizada = self._guardar_con_inventario(campaña_id, ficha, inventario)
        self._registrar(
            campaña_id, "objeto_quitado", self.nombre,
            {
                "personaje_id": ficha.id,
                "objeto_id": objeto_id,
                "nombre": obj["nombre"],
                "cantidad": cantidad,
                "cantidad_antes": cantidad_antes,
                "cantidad_despues": cantidad_despues,
                "motivo": motivo,
            },
        )
        return ResultadoHerramienta(ok=True, datos=self._salida(actualizada))


class _ToolInventarioEquipar(_ToolInventarioBase):
    _equipar = True
    nombre = "inventario.equipar"
    descripcion = "Marca un objeto como equipado. Guarda y registra evento. Sin slots ni exclusividad."
    modifica = ["ficha", "eventos"]
    _tipo_evento = "objeto_equipado"
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "objeto_id": {"type": "string"},
            "motivo": {"type": "string"},
        },
        "required": ["campaña_id", "personaje_id", "objeto_id"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        objeto_id = args.get("objeto_id")
        if not objeto_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'objeto_id'"])
        ficha, err = self._cargar(args.get("campaña_id"), args.get("personaje_id"))
        if err:
            return err
        assert ficha is not None
        campaña_id = args["campaña_id"]
        motivo = args.get("motivo")

        inventario = [o.model_dump() for o in ficha.inventario]
        obj = next((o for o in inventario if o["id"] == objeto_id), None)
        if obj is None:
            return ResultadoHerramienta(ok=False, errores=[f"objeto no existe: {objeto_id!r}"])
        obj["equipado"] = self._equipar

        actualizada = self._guardar_con_inventario(campaña_id, ficha, inventario)
        self._registrar(
            campaña_id, self._tipo_evento, self.nombre,
            {
                "personaje_id": ficha.id,
                "objeto_id": objeto_id,
                "nombre": obj["nombre"],
                "motivo": motivo,
            },
        )
        return ResultadoHerramienta(ok=True, datos=self._salida(actualizada))


class _ToolInventarioDesequipar(_ToolInventarioEquipar):
    _equipar = False
    nombre = "inventario.desequipar"
    descripcion = "Marca un objeto como no equipado. Guarda y registra evento."
    _tipo_evento = "objeto_desequipado"


def crear_tools_inventario(
    gestor: GestorEstado, registro_eventos: RegistroEventosEstado
) -> list[Any]:
    """Crea las cinco tools de inventario enlazadas a `GestorEstado` y al registro de eventos."""
    return [
        _ToolInventarioListar(gestor, registro_eventos),
        _ToolInventarioAñadir(gestor, registro_eventos),
        _ToolInventarioQuitar(gestor, registro_eventos),
        _ToolInventarioEquipar(gestor, registro_eventos),
        _ToolInventarioDesequipar(gestor, registro_eventos),
    ]
