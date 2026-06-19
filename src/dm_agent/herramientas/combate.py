"""Tools de combate narrativo mínimo (F5.1).

`combate.iniciar`, `combate.estado`, `combate.añadir_enemigo`,
`combate.daño_enemigo`, `combate.terminar`.

Combate narrativo en el sentido de D17: teatro de la mente, sin grid, sin
casillas, sin iniciativa compleja, sin economía de acciones. El daño al
personaje jugador sigue pasando por `hp_xp.aplicar_daño`; estas tools solo
gestionan el estado de los enemigos simples dentro de la escena. Cada
mutación registra un `Evento` auditable, igual que `hp_xp.*` (F3.4).
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import ValidationError

from dm_agent.esquemas.combate import CombateNarrativo, EnemigoCombate
from dm_agent.esquemas.evento import crear_evento
from dm_agent.estado.combate import ErrorCombateNoEncontrado, GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.herramientas.base import ResultadoHerramienta

_ACTOR_DM = "dm"

_PROPS_ENEMIGO: dict[str, Any] = {
    "id": {"type": "string"},
    "nombre": {"type": "string"},
    "hp_max": {"type": "integer", "minimum": 1},
    "hp_actual": {"type": "integer", "minimum": 0},
    "ca": {"type": "integer", "minimum": 1},
    "estado": {"type": "string"},
    "descripcion": {"type": "string"},
    "distancia": {
        "type": "string",
        "enum": ["cerca", "media", "lejos", "fuera_de_alcance"],
    },
    "tags": {"type": "array", "items": {"type": "string"}},
}
_REQUERIDOS_ENEMIGO = ["id", "nombre", "hp_max", "hp_actual", "ca"]
_SCHEMA_ENEMIGO: dict[str, Any] = {
    "type": "object",
    "properties": _PROPS_ENEMIGO,
    "required": _REQUERIDOS_ENEMIGO,
    "additionalProperties": False,
}


def _errores_validacion(e: ValidationError) -> list[str]:
    return [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()]


def _cantidad_positiva(args: dict[str, Any]) -> tuple[int | None, ResultadoHerramienta | None]:
    cantidad = args.get("cantidad")
    # bool es subclase de int: lo rechazamos explícitamente.
    if isinstance(cantidad, bool) or not isinstance(cantidad, int):
        return None, ResultadoHerramienta(ok=False, errores=["'cantidad' debe ser un entero"])
    if cantidad <= 0:
        return None, ResultadoHerramienta(ok=False, errores=["'cantidad' debe ser > 0"])
    return cantidad, None


def _estado_tras_daño(hp_actual: int, hp_max: int) -> str:
    if hp_actual <= 0:
        return "derrotado"
    if hp_actual <= hp_max * 0.25:
        return "critico"
    if hp_actual < hp_max:
        return "herido"
    return "activo"


def _generar_id_combate() -> str:
    return f"combate_{uuid.uuid4().hex[:8]}"


class _ToolCombateBase:
    requiere: list[str] = []
    modifica: list[str] = []

    def __init__(self, gestor: GestorCombateNarrativo, registro_eventos: RegistroEventosEstado) -> None:
        self.gestor = gestor
        self.eventos = registro_eventos

    def disponible(self, ctx: Any) -> tuple[bool, str]:
        return True, ""

    def _cargar(
        self, campaña_id: str | None, combate_id: str | None
    ) -> tuple[CombateNarrativo | None, ResultadoHerramienta | None]:
        if not campaña_id or not combate_id:
            return None, ResultadoHerramienta(
                ok=False, errores=["faltan 'campaña_id' y/o 'combate_id'"]
            )
        try:
            return self.gestor.cargar(campaña_id, combate_id), None
        except ErrorCombateNoEncontrado:
            return None, ResultadoHerramienta(
                ok=False, errores=[f"combate no existe: {combate_id!r}"]
            )


class _ToolIniciar(_ToolCombateBase):
    nombre = "combate.iniciar"
    descripcion = (
        "Inicia una escena de combate narrativo: registra enemigos simples y la marca como "
        "combate activo de la campaña. Falla si ya hay un combate activo sin terminar/cancelar."
    )
    modifica = ["combate", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "sesion_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "descripcion_escena": {"type": "string"},
            "enemigos": {"type": "array", "items": _SCHEMA_ENEMIGO},
        },
        "required": ["campaña_id", "personaje_id"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        personaje_id = args.get("personaje_id")
        if not campaña_id or not personaje_id:
            return ResultadoHerramienta(
                ok=False, errores=["faltan 'campaña_id' y/o 'personaje_id'"]
            )

        activo = self.gestor.cargar_activo(campaña_id)
        if activo is not None and activo.estado not in ("terminado", "cancelado"):
            return ResultadoHerramienta(
                ok=False,
                errores=[
                    f"ya hay un combate activo en {campaña_id!r}: {activo.id!r} "
                    f"(estado={activo.estado!r}); termínalo antes de iniciar otro"
                ],
            )

        try:
            enemigos = [EnemigoCombate.model_validate(e) for e in args.get("enemigos", [])]
            combate = CombateNarrativo(
                id=_generar_id_combate(),
                campaña_id=campaña_id,
                sesion_id=args.get("sesion_id"),
                personaje_id=personaje_id,
                estado="activo",
                descripcion_escena=args.get("descripcion_escena", ""),
                enemigos=enemigos,
            )
        except ValidationError as e:
            return ResultadoHerramienta(ok=False, errores=_errores_validacion(e))

        self.gestor.guardar(combate)
        self.gestor.marcar_activo(combate)

        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "combate_iniciado",
                actor=_ACTOR_DM,
                objetivo=combate.id,
                tool=self.nombre,
                datos={
                    "campaña_id": campaña_id,
                    "combate_id": combate.id,
                    "personaje_id": personaje_id,
                    "num_enemigos": len(combate.enemigos),
                },
            ),
        )
        return ResultadoHerramienta(ok=True, datos={"combate": combate.model_dump(mode="json")})


class _ToolEstado(_ToolCombateBase):
    nombre = "combate.estado"
    descripcion = (
        "Consulta el estado de un combate (por combate_id, o el combate activo de la campaña "
        "si se omite). No modifica nada ni registra evento."
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
        },
        "required": ["campaña_id"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        if not campaña_id:
            return ResultadoHerramienta(ok=False, errores=["falta 'campaña_id'"])
        combate_id = args.get("combate_id")
        if combate_id:
            combate, err = self._cargar(campaña_id, combate_id)
            if err:
                return err
        else:
            combate = self.gestor.cargar_activo(campaña_id)
            if combate is None:
                return ResultadoHerramienta(
                    ok=False, errores=[f"no hay combate activo en {campaña_id!r}"]
                )
        assert combate is not None
        return ResultadoHerramienta(ok=True, datos={"combate": combate.model_dump(mode="json")})


class _ToolAñadirEnemigo(_ToolCombateBase):
    nombre = "combate.añadir_enemigo"
    descripcion = "Añade un enemigo simple a un combate existente. Rechaza id de enemigo duplicado."
    modifica = ["combate", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
            "enemigo": _SCHEMA_ENEMIGO,
        },
        "required": ["campaña_id", "combate_id", "enemigo"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        combate, err = self._cargar(campaña_id, args.get("combate_id"))
        if err:
            return err
        assert combate is not None

        try:
            enemigo = EnemigoCombate.model_validate(args.get("enemigo") or {})
        except ValidationError as e:
            return ResultadoHerramienta(ok=False, errores=_errores_validacion(e))

        if any(e.id == enemigo.id for e in combate.enemigos):
            return ResultadoHerramienta(
                ok=False, errores=[f"ya existe un enemigo con id {enemigo.id!r} en este combate"]
            )

        combate_actualizado = combate.model_copy(update={"enemigos": [*combate.enemigos, enemigo]})
        self.gestor.guardar(combate_actualizado)

        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "enemigo_añadido",
                actor=_ACTOR_DM,
                objetivo=enemigo.id,
                tool=self.nombre,
                datos={
                    "campaña_id": campaña_id,
                    "combate_id": combate.id,
                    "enemigo_id": enemigo.id,
                    "nombre": enemigo.nombre,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True, datos={"combate": combate_actualizado.model_dump(mode="json")}
        )


class _ToolDañoEnemigo(_ToolCombateBase):
    nombre = "combate.daño_enemigo"
    descripcion = (
        "Aplica daño a un enemigo del combate: baja hp_actual (mínimo 0), actualiza su estado "
        "narrativo y registra evento. No aplica resistencia/vulnerabilidad."
    )
    modifica = ["combate", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
            "enemigo_id": {"type": "string"},
            "cantidad": {"type": "integer", "description": "Puntos de daño (> 0)."},
            "motivo": {"type": "string"},
        },
        "required": ["campaña_id", "combate_id", "enemigo_id", "cantidad"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        cantidad, err = _cantidad_positiva(args)
        if err:
            return err
        campaña_id = args.get("campaña_id")
        combate, err = self._cargar(campaña_id, args.get("combate_id"))
        if err:
            return err
        assert combate is not None and cantidad is not None

        enemigo_id = args.get("enemigo_id")
        enemigo = next((e for e in combate.enemigos if e.id == enemigo_id), None)
        if enemigo is None:
            return ResultadoHerramienta(
                ok=False, errores=[f"enemigo no existe en este combate: {enemigo_id!r}"]
            )

        hp_antes = enemigo.hp_actual
        hp_despues = max(0, hp_antes - cantidad)
        nuevo_estado = _estado_tras_daño(hp_despues, enemigo.hp_max)
        enemigo_actualizado = enemigo.model_copy(update={"hp_actual": hp_despues, "estado": nuevo_estado})
        nuevos_enemigos = [
            enemigo_actualizado if e.id == enemigo_id else e for e in combate.enemigos
        ]
        combate_actualizado = combate.model_copy(update={"enemigos": nuevos_enemigos})
        self.gestor.guardar(combate_actualizado)

        motivo = args.get("motivo")
        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "daño_enemigo",
                actor=_ACTOR_DM,
                objetivo=enemigo_id,
                tool=self.nombre,
                motivo=motivo,
                datos={
                    "campaña_id": campaña_id,
                    "combate_id": combate.id,
                    "enemigo_id": enemigo_id,
                    "cantidad": cantidad,
                    "hp_antes": hp_antes,
                    "hp_despues": hp_despues,
                    "estado": nuevo_estado,
                    "motivo": motivo,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "combate_id": combate.id,
                "enemigo_id": enemigo_id,
                "hp_antes": hp_antes,
                "hp_despues": hp_despues,
                "estado": nuevo_estado,
                "combate": combate_actualizado.model_dump(mode="json"),
            },
        )


class _ToolTerminar(_ToolCombateBase):
    nombre = "combate.terminar"
    descripcion = (
        "Marca un combate como terminado y libera el combate activo de la campaña. "
        "No otorga XP automáticamente (usa hp_xp.otorgar_xp aparte)."
    )
    modifica = ["combate", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
            "resultado": {"type": "string"},
            "motivo": {"type": "string"},
        },
        "required": ["campaña_id", "combate_id"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        combate, err = self._cargar(campaña_id, args.get("combate_id"))
        if err:
            return err
        assert combate is not None

        combate_actualizado = combate.model_copy(update={"estado": "terminado"})
        self.gestor.guardar(combate_actualizado)

        activo = self.gestor.cargar_activo(campaña_id)
        if activo is not None and activo.id == combate.id:
            self.gestor.limpiar_activo(campaña_id)

        resultado = args.get("resultado")
        motivo = args.get("motivo")
        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "combate_terminado",
                actor=_ACTOR_DM,
                objetivo=combate.id,
                tool=self.nombre,
                motivo=motivo,
                datos={
                    "campaña_id": campaña_id,
                    "combate_id": combate.id,
                    "resultado": resultado,
                    "motivo": motivo,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True, datos={"combate": combate_actualizado.model_dump(mode="json")}
        )


def crear_tools_combate(
    gestor: GestorCombateNarrativo, registro_eventos: RegistroEventosEstado
) -> list[Any]:
    """Crea las cinco tools de combate enlazadas al gestor y al registro de eventos."""
    return [
        _ToolIniciar(gestor, registro_eventos),
        _ToolEstado(gestor, registro_eventos),
        _ToolAñadirEnemigo(gestor, registro_eventos),
        _ToolDañoEnemigo(gestor, registro_eventos),
        _ToolTerminar(gestor, registro_eventos),
    ]
