"""Tools deterministas de HP y XP (F3.4).

`hp_xp.aplicar_daño`, `hp_xp.aplicar_curacion`, `hp_xp.otorgar_xp`,
`hp_xp.consultar_estado_vital`.

Toda mecánica de daño/curación/XP debe pasar por estas tools (no por
`ficha.actualizar`, que es genérica/administrativa). Cada cambio exitoso:
carga la ficha con `GestorEstado`, modifica solo el campo permitido, revalida
con `Ficha`, guarda de forma atómica y registra un `Evento` auditable en el
`eventos.jsonl` de la campaña.

Coherente con D17 (D&D 5.5 narrativo en solitario): lógica simple, compatible con
teatro de la mente. NO hay combate, iniciativa, muerte/salvaciones, condiciones
complejas, resistencia/vulnerabilidad ni subida de nivel automática.
"""

from __future__ import annotations

from typing import Any

from dm_agent.esquemas.evento import crear_evento
from dm_agent.esquemas.ficha import Ficha
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import ErrorEstado, ErrorEstadoNoEncontrado, GestorEstado
from dm_agent.herramientas.base import ResultadoHerramienta

_ACTOR_DM = "dm"


def estado_vital(hp_actual: int, hp_max: int) -> str:
    """Clasificación narrativa simple del estado vital."""
    if hp_actual <= 0:
        return "caido"
    if hp_actual >= hp_max:
        return "sano"
    if hp_actual <= hp_max * 0.25:
        return "critico"
    return "herido"


def _porcentaje_hp(hp_actual: int, hp_max: int) -> float:
    if hp_max <= 0:
        return 0.0
    return round(hp_actual / hp_max * 100, 1)


def _cantidad_positiva(args: dict[str, Any]) -> tuple[int | None, ResultadoHerramienta | None]:
    cantidad = args.get("cantidad")
    # bool es subclase de int: lo rechazamos explícitamente.
    if isinstance(cantidad, bool) or not isinstance(cantidad, int):
        return None, ResultadoHerramienta(ok=False, errores=["'cantidad' debe ser un entero"])
    if cantidad <= 0:
        return None, ResultadoHerramienta(ok=False, errores=["'cantidad' debe ser > 0"])
    return cantidad, None


class _ToolHpXpBase:
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

    def _guardar_con_hp(self, campaña_id: str, ficha: Ficha, nuevo_hp: int) -> Ficha:
        actualizada = Ficha.model_validate({**ficha.model_dump(), "hp_actual": nuevo_hp})
        self.gestor.guardar_ficha(campaña_id, actualizada)
        return actualizada

    def _guardar_con_xp(self, campaña_id: str, ficha: Ficha, nuevo_xp: int) -> Ficha:
        actualizada = Ficha.model_validate({**ficha.model_dump(), "xp": nuevo_xp})
        self.gestor.guardar_ficha(campaña_id, actualizada)
        return actualizada


class _ToolAplicarDaño(_ToolHpXpBase):
    nombre = "hp_xp.aplicar_daño"
    descripcion = (
        "Aplica daño a un personaje: baja hp_actual (mínimo 0), guarda y registra evento. "
        "No aplica resistencia/vulnerabilidad ni salvaciones."
    )
    modifica = ["ficha", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "cantidad": {"type": "integer", "description": "Puntos de daño (> 0)."},
            "tipo_daño": {"type": "string", "description": "Tipo de daño (opcional, narrativo)."},
            "motivo": {"type": "string"},
        },
        "required": ["campaña_id", "personaje_id", "cantidad"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        cantidad, err = _cantidad_positiva(args)
        if err:
            return err
        ficha, err = self._cargar(args.get("campaña_id"), args.get("personaje_id"))
        if err:
            return err
        assert ficha is not None and cantidad is not None

        hp_antes = ficha.hp_actual
        hp_despues = max(0, hp_antes - cantidad)
        campaña_id = args["campaña_id"]
        motivo = args.get("motivo")
        actualizada = self._guardar_con_hp(campaña_id, ficha, hp_despues)

        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "daño_aplicado",
                actor=_ACTOR_DM,
                objetivo=ficha.id,
                tool=self.nombre,
                motivo=motivo,
                datos={
                    "cantidad": cantidad,
                    "hp_antes": hp_antes,
                    "hp_despues": hp_despues,
                    "tipo_daño": args.get("tipo_daño"),
                    "motivo": motivo,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "personaje_id": ficha.id,
                "hp_antes": hp_antes,
                "hp_despues": hp_despues,
                "hp_max": actualizada.hp_max,
                "estado_vital": estado_vital(hp_despues, actualizada.hp_max),
            },
        )


class _ToolAplicarCuracion(_ToolHpXpBase):
    nombre = "hp_xp.aplicar_curacion"
    descripcion = (
        "Cura a un personaje: sube hp_actual (máximo hp_max), guarda y registra evento. "
        "No aplica curación con dados, estabilización ni condiciones."
    )
    modifica = ["ficha", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "cantidad": {"type": "integer", "description": "Puntos de curación (> 0)."},
            "motivo": {"type": "string"},
        },
        "required": ["campaña_id", "personaje_id", "cantidad"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        cantidad, err = _cantidad_positiva(args)
        if err:
            return err
        ficha, err = self._cargar(args.get("campaña_id"), args.get("personaje_id"))
        if err:
            return err
        assert ficha is not None and cantidad is not None

        hp_antes = ficha.hp_actual
        hp_despues = min(ficha.hp_max, hp_antes + cantidad)
        campaña_id = args["campaña_id"]
        motivo = args.get("motivo")
        actualizada = self._guardar_con_hp(campaña_id, ficha, hp_despues)

        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "curacion_aplicada",
                actor=_ACTOR_DM,
                objetivo=ficha.id,
                tool=self.nombre,
                motivo=motivo,
                datos={
                    "cantidad": cantidad,
                    "hp_antes": hp_antes,
                    "hp_despues": hp_despues,
                    "motivo": motivo,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "personaje_id": ficha.id,
                "hp_antes": hp_antes,
                "hp_despues": hp_despues,
                "hp_max": actualizada.hp_max,
                "estado_vital": estado_vital(hp_despues, actualizada.hp_max),
            },
        )


class _ToolOtorgarXp(_ToolHpXpBase):
    nombre = "hp_xp.otorgar_xp"
    descripcion = (
        "Otorga XP a un personaje: suma a ficha.xp, guarda y registra evento. "
        "No calcula subida de nivel."
    )
    modifica = ["ficha", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "cantidad": {"type": "integer", "description": "XP a otorgar (> 0)."},
            "motivo": {"type": "string"},
        },
        "required": ["campaña_id", "personaje_id", "cantidad"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        cantidad, err = _cantidad_positiva(args)
        if err:
            return err
        ficha, err = self._cargar(args.get("campaña_id"), args.get("personaje_id"))
        if err:
            return err
        assert ficha is not None and cantidad is not None

        xp_antes = ficha.xp
        xp_despues = xp_antes + cantidad
        campaña_id = args["campaña_id"]
        motivo = args.get("motivo")
        self._guardar_con_xp(campaña_id, ficha, xp_despues)

        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "xp_otorgada",
                actor=_ACTOR_DM,
                objetivo=ficha.id,
                tool=self.nombre,
                motivo=motivo,
                datos={
                    "cantidad": cantidad,
                    "xp_antes": xp_antes,
                    "xp_despues": xp_despues,
                    "motivo": motivo,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "personaje_id": ficha.id,
                "xp_antes": xp_antes,
                "xp_despues": xp_despues,
                # Informativo: la subida de nivel automática no existe todavía (F-futura).
                "subida_nivel_pendiente": None,
            },
        )


class _ToolConsultarEstadoVital(_ToolHpXpBase):
    nombre = "hp_xp.consultar_estado_vital"
    descripcion = "Consulta hp_actual/hp_max/porcentaje/estado_vital. No modifica ni registra evento."
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
        return ResultadoHerramienta(
            ok=True,
            datos={
                "personaje_id": ficha.id,
                "hp_actual": ficha.hp_actual,
                "hp_max": ficha.hp_max,
                "porcentaje_hp": _porcentaje_hp(ficha.hp_actual, ficha.hp_max),
                "estado_vital": estado_vital(ficha.hp_actual, ficha.hp_max),
            },
        )


def crear_tools_hp_xp(
    gestor: GestorEstado, registro_eventos: RegistroEventosEstado
) -> list[Any]:
    """Crea las cuatro tools de HP/XP enlazadas a `GestorEstado` y al registro de eventos."""
    return [
        _ToolAplicarDaño(gestor, registro_eventos),
        _ToolAplicarCuracion(gestor, registro_eventos),
        _ToolOtorgarXp(gestor, registro_eventos),
        _ToolConsultarEstadoVital(gestor, registro_eventos),
    ]
