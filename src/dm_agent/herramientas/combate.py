"""Tools de combate narrativo mínimo (F5.1, distancias revisadas en F5.1.1,
iniciativa/turnos añadidos en F5.2, ataques básicos contra CA en F5.3,
ventaja/desventaja y modificadores situacionales en F5.4).

`combate.iniciar`, `combate.estado`, `combate.añadir_enemigo`,
`combate.daño_enemigo`, `combate.terminar`, `combate.tirar_iniciativa`,
`combate.turno_actual`, `combate.avanzar_turno`, `combate.atacar_enemigo`,
`combate.atacar_personaje`.

Combate narrativo en el sentido de D17: teatro de la mente, sin grid, sin
casillas, sin economía de acciones completa. Se conserva el vocabulario de
combate de D&D (enemigo, ataque, daño, estado, distancia, iniciativa, turno)
pero se resuelve de forma conversacional, sin geometría exacta. El daño al
personaje jugador por fuera de un ataque resuelto sigue pasando por
`hp_xp.aplicar_daño`; estas tools gestionan el estado de los enemigos
simples, el orden de turnos y la resolución de ataques dentro de la escena.
Cada mutación registra un `Evento` auditable, igual que `hp_xp.*` (F3.4).

La iniciativa es clásica: 1d20 + modificador de Destreza (D-COMBATE-01). El
DM Agent tira automáticamente por los enemigos (D-COMBATE-02); el jugador
sigue resolviendo la suya. Las tiradas usan `dm_agent.herramientas.dados.tirar`
(mismo motor que `dados.tirar`); con `semilla` son deterministas para tests,
sin ella son aleatorias de verdad en runtime.

Ataques (F5.3): 1d20 + modificador de ataque contra la CA del objetivo;
natural 1 falla siempre (pifia), natural 20 impacta siempre (crítico). El
daño al personaje en `combate.atacar_personaje` se aplica directamente sobre
`Ficha` (vía `GestorEstado`) y registra solo `ataque_personaje_resuelto`
— deliberadamente **no** se llama a `hp_xp.aplicar_daño` para evitar
duplicar el evento de daño (ver ADR-0018). `combate.atacar_enemigo` no
avanza turno automáticamente: el avance sigue siendo explícito vía
`combate.avanzar_turno`.

Ventaja/desventaja (F5.4, `modo_tirada`): normal tira 1d20; ventaja/
desventaja tiran 2d20 y se quedan con el mayor/menor. Si la ficción tiene
ventaja y desventaja a la vez, se cancelan — quien llama a la tool decide el
`modo_tirada` final, no hay acumulación de múltiples ventajas/desventajas
aquí. Natural 1/20 se evalúa sobre la tirada elegida tras ventaja/
desventaja. `modificador_situacional` (-10..10) es un bonificador/
penalizador narrativo simple que se suma al total de ataque junto con
`modificador_ataque`; `motivo_modificador` es texto libre para registrar por
qué se aplicó. Sin estos campos nuevos, el comportamiento es idéntico a
F5.3.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from dm_agent.esquemas.combate import CombateNarrativo, EnemigoCombate, EntradaIniciativa
from dm_agent.esquemas.evento import crear_evento
from dm_agent.esquemas.ficha import Ficha
from dm_agent.estado.combate import ErrorCombateNoEncontrado, GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import ErrorEstado, ErrorEstadoNoEncontrado, GestorEstado
from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.herramientas.dados import tirar as tirar_dados
from dm_agent.herramientas.hp_xp import estado_vital

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
        "enum": ["cuerpo_a_cuerpo", "corta", "media", "larga", "fuera_de_alcance"],
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


def _validar_mod_destreza(valor: Any) -> tuple[int | None, str | None]:
    """Valida un `mod_destreza` recibido por args (no el del esquema). None -> 0."""
    if valor is None:
        return 0, None
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, "'mod_destreza' debe ser un entero"
    if valor < -10 or valor > 10:
        return None, "'mod_destreza' debe estar entre -10 y 10"
    return valor, None


def _tirar_d20(mod: int, semilla: int | None) -> int:
    """1d20 + mod, vía el motor de dados existente (D-COMBATE-01)."""
    expr = f"1d20{mod:+d}"
    return tirar_dados(expr, semilla=semilla).total


def _semilla_participante(semilla_base: int | None, indice: int) -> int | None:
    """Deriva una semilla distinta por participante a partir de una base (tests).

    Sin `semilla_base`, devuelve None: cada tirada usa entropía real e
    independiente (runtime).
    """
    if semilla_base is None:
        return None
    return semilla_base + indice


def _orden_iniciativa_orden(entrada: EntradaIniciativa) -> tuple[int, int, str, str]:
    """Clave de orden: iniciativa descendente; empate -> personaje gana; luego nombre/id estable."""
    return (-entrada.iniciativa, 0 if entrada.es_personaje else 1, entrada.nombre, entrada.participante_id)


@dataclass(slots=True)
class ResultadoAtaque:
    """Resultado de resolver un ataque contra CA (F5.3; ventaja/desventaja en F5.4).

    No se persiste tal cual; se vuelca a evento auditable y a la respuesta de la tool.
    """

    atacante_id: str
    objetivo_id: str
    modo_tirada: str
    tiradas_d20: list[int]
    tirada_d20: int
    modificador_ataque: int
    modificador_situacional: int
    total_ataque: int
    ca_objetivo: int
    impacta: bool
    critico: bool
    pifia: bool
    dano: int
    tipo_dano: str | None
    motivo: str | None
    motivo_modificador: str | None


_MODOS_TIRADA = ("normal", "ventaja", "desventaja")


def _validar_modo_tirada(valor: Any) -> tuple[str | None, str | None]:
    """None -> "normal". Valida contra D&D: ventaja/desventaja se cancelan fuera de esta tool."""
    if valor is None:
        return "normal", None
    if not isinstance(valor, str) or valor not in _MODOS_TIRADA:
        return None, f"'modo_tirada' debe ser uno de {_MODOS_TIRADA}"
    return valor, None


def _validar_modificador_ataque(valor: Any) -> tuple[int | None, str | None]:
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, "'modificador_ataque' debe ser un entero"
    return valor, None


def _validar_modificador_situacional(valor: Any) -> tuple[int | None, str | None]:
    """None -> 0. Bonificador/penalizador narrativo simple, rango -10..10."""
    if valor is None:
        return 0, None
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None, "'modificador_situacional' debe ser un entero"
    if valor < -10 or valor > 10:
        return None, "'modificador_situacional' debe estar entre -10 y 10"
    return valor, None


def _tirar_d20_bruto(semilla: int | None) -> int:
    """1d20 puro, sin modificador (para ventaja/desventaja)."""
    return tirar_dados("1d20", semilla=semilla).dados[0]


def _tirar_tiradas_ataque(modo_tirada: str, semilla: int | None) -> list[int]:
    """Tira 1d20 (normal) o 2d20 (ventaja/desventaja); no decide cuál se usa (D-COMBATE F5.4)."""
    if modo_tirada == "normal":
        return [_tirar_d20_bruto(semilla)]
    primera = _tirar_d20_bruto(semilla)
    segunda = _tirar_d20_bruto(None if semilla is None else semilla + 1)
    return [primera, segunda]


def _elegir_tirada(modo_tirada: str, tiradas: list[int]) -> int:
    if modo_tirada == "ventaja":
        return max(tiradas)
    if modo_tirada == "desventaja":
        return min(tiradas)
    return tiradas[0]


def _tirar_dano(expresion: str, semilla: int | None) -> int:
    """Tira una expresión de daño (ej. '1d8+3'); nunca negativo."""
    return max(0, tirar_dados(expresion, semilla=semilla).total)


_REGEX_EXPR_DANO = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def _duplicar_dados_critico(expresion: str) -> str:
    """Duplica el número de dados (no el modificador) para un crítico limpio.

    Si la expresión no encaja con el patrón NdM[+/-mod], se devuelve sin
    tocar (no debería ocurrir: ya se validó como expresión de dados antes).
    """
    m = _REGEX_EXPR_DANO.match(expresion)
    if not m:
        return expresion
    n = int(m.group(1))
    caras = m.group(2)
    mod = m.group(3) or ""
    return f"{n * 2}d{caras}{mod}"


def _resolver_ataque(
    *,
    atacante_id: str,
    objetivo_id: str,
    modo_tirada: str,
    modificador_ataque: int,
    modificador_situacional: int,
    ca_objetivo: int,
    dano_expr: str,
    tipo_dano: str | None,
    motivo: str | None,
    motivo_modificador: str | None,
    semilla: int | None,
) -> tuple[ResultadoAtaque | None, ResultadoHerramienta | None]:
    """1d20 (o 2d20 con ventaja/desventaja) + modificadores contra CA.

    Natural 1 (sobre la tirada elegida) falla siempre; natural 20 impacta siempre y duplica
    dados de daño. Comparte esta lógica `combate.atacar_enemigo` y `combate.atacar_personaje`.
    """
    tiradas_d20 = _tirar_tiradas_ataque(modo_tirada, semilla)
    tirada_elegida = _elegir_tirada(modo_tirada, tiradas_d20)
    pifia = tirada_elegida == 1
    critico = tirada_elegida == 20
    total_ataque = tirada_elegida + modificador_ataque + modificador_situacional
    impacta = critico or (not pifia and total_ataque >= ca_objetivo)

    dano_total = 0
    if impacta:
        expr_dano = _duplicar_dados_critico(dano_expr) if critico else dano_expr
        semilla_dano = None if semilla is None else semilla + 2
        try:
            dano_total = _tirar_dano(expr_dano, semilla_dano)
        except ValueError as e:
            return None, ResultadoHerramienta(ok=False, errores=[f"'dano' inválido: {e}"])

    resultado = ResultadoAtaque(
        atacante_id=atacante_id,
        objetivo_id=objetivo_id,
        modo_tirada=modo_tirada,
        tiradas_d20=tiradas_d20,
        tirada_d20=tirada_elegida,
        modificador_ataque=modificador_ataque,
        modificador_situacional=modificador_situacional,
        total_ataque=total_ataque,
        ca_objetivo=ca_objetivo,
        impacta=impacta,
        critico=critico,
        pifia=pifia,
        dano=dano_total,
        tipo_dano=tipo_dano,
        motivo=motivo,
        motivo_modificador=motivo_modificador,
    )
    return resultado, None


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


class _ToolTirarIniciativa(_ToolCombateBase):
    nombre = "combate.tirar_iniciativa"
    descripcion = (
        "Tira iniciativa clásica (1d20 + mod. Destreza) para el personaje y, automáticamente, "
        "para cada enemigo del combate (D-COMBATE-01/02). Guarda el orden, pone ronda=1 e "
        "indice_turno_actual=0. No implementa sorpresa."
    )
    modifica = ["combate", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
            "personaje": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "nombre": {"type": "string"},
                    "mod_destreza": {"type": "integer", "minimum": -10, "maximum": 10},
                },
                "required": ["id"],
                "additionalProperties": False,
            },
            "enemigos": {
                "type": "array",
                "description": "Modificadores de Destreza por enemigo_id; si falta, se usa 0.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "mod_destreza": {"type": "integer", "minimum": -10, "maximum": 10},
                    },
                    "required": ["id"],
                    "additionalProperties": False,
                },
            },
            "semilla": {
                "type": "integer",
                "description": "Semilla opcional para tiradas reproducibles (tests/depuración).",
            },
        },
        "required": ["campaña_id", "combate_id", "personaje"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        combate, err = self._cargar(campaña_id, args.get("combate_id"))
        if err:
            return err
        assert combate is not None

        personaje = args.get("personaje")
        if not isinstance(personaje, dict) or not personaje.get("id"):
            return ResultadoHerramienta(ok=False, errores=["falta 'personaje.id'"])
        personaje_id = personaje["id"]
        if personaje_id != combate.personaje_id:
            return ResultadoHerramienta(
                ok=False,
                errores=[
                    f"'personaje.id' ({personaje_id!r}) no coincide con el personaje del "
                    f"combate ({combate.personaje_id!r})"
                ],
            )
        mod_pj, error_mod = _validar_mod_destreza(personaje.get("mod_destreza"))
        if error_mod:
            return ResultadoHerramienta(ok=False, errores=[error_mod])
        assert mod_pj is not None

        overrides_raw = args.get("enemigos", [])
        overrides: dict[str, Any] = {}
        for o in overrides_raw:
            if not isinstance(o, dict) or not o.get("id"):
                return ResultadoHerramienta(ok=False, errores=["cada entrada de 'enemigos' requiere 'id'"])
            overrides[o["id"]] = o

        semilla = args.get("semilla")
        idx_semilla = 0

        iniciativa_pj = _tirar_d20(mod_pj, _semilla_participante(semilla, idx_semilla))
        idx_semilla += 1
        entradas = [
            EntradaIniciativa(
                participante_id=personaje_id,
                nombre=personaje.get("nombre", personaje_id),
                tipo="personaje",
                iniciativa=iniciativa_pj,
                es_personaje=True,
            )
        ]

        nuevos_enemigos = []
        for enemigo in combate.enemigos:
            override = overrides.get(enemigo.id)
            if override is not None and "mod_destreza" in override:
                mod_en, error_mod_en = _validar_mod_destreza(override["mod_destreza"])
                if error_mod_en:
                    return ResultadoHerramienta(ok=False, errores=[error_mod_en])
            else:
                mod_en = enemigo.mod_destreza if enemigo.mod_destreza is not None else 0
            assert mod_en is not None

            iniciativa_en = _tirar_d20(mod_en, _semilla_participante(semilla, idx_semilla))
            idx_semilla += 1

            nuevos_enemigos.append(
                enemigo.model_copy(update={"mod_destreza": mod_en, "iniciativa": iniciativa_en})
            )
            entradas.append(
                EntradaIniciativa(
                    participante_id=enemigo.id,
                    nombre=enemigo.nombre,
                    tipo="enemigo",
                    iniciativa=iniciativa_en,
                    es_personaje=False,
                )
            )

        entradas.sort(key=_orden_iniciativa_orden)

        combate_actualizado = combate.model_copy(
            update={
                "enemigos": nuevos_enemigos,
                "orden_iniciativa": entradas,
                "indice_turno_actual": 0,
                "ronda": 1,
            }
        )
        self.gestor.guardar(combate_actualizado)

        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "iniciativa_tirada",
                actor=_ACTOR_DM,
                objetivo=combate.id,
                tool=self.nombre,
                datos={
                    "campaña_id": campaña_id,
                    "combate_id": combate.id,
                    "orden_iniciativa": [e.model_dump(mode="json") for e in entradas],
                    "ronda": 1,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "combate_id": combate.id,
                "orden_iniciativa": [e.model_dump(mode="json") for e in entradas],
                "indice_turno_actual": 0,
                "ronda": 1,
                "combate": combate_actualizado.model_dump(mode="json"),
            },
        )


class _ToolTurnoActual(_ToolCombateBase):
    nombre = "combate.turno_actual"
    descripcion = (
        "Consulta la entrada actual del orden de iniciativa y la ronda. "
        "No modifica nada ni registra evento."
    )
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
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

        if not combate.orden_iniciativa:
            return ResultadoHerramienta(
                ok=False, errores=[f"no se ha tirado iniciativa en {combate.id!r}"]
            )
        entrada = combate.orden_iniciativa[combate.indice_turno_actual]
        return ResultadoHerramienta(
            ok=True,
            datos={
                "combate_id": combate.id,
                "turno_actual": entrada.model_dump(mode="json"),
                "indice_turno_actual": combate.indice_turno_actual,
                "ronda": combate.ronda,
            },
        )


class _ToolAvanzarTurno(_ToolCombateBase):
    nombre = "combate.avanzar_turno"
    descripcion = (
        "Avanza al siguiente turno del orden de iniciativa. Si llega al final, vuelve al "
        "primero y aumenta la ronda. Registra evento turno_avanzado."
    )
    modifica = ["combate", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
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

        if not combate.orden_iniciativa:
            return ResultadoHerramienta(
                ok=False, errores=[f"no se ha tirado iniciativa en {combate.id!r}"]
            )

        entrada_anterior = combate.orden_iniciativa[combate.indice_turno_actual]
        nuevo_indice = combate.indice_turno_actual + 1
        nueva_ronda = combate.ronda
        if nuevo_indice >= len(combate.orden_iniciativa):
            nuevo_indice = 0
            nueva_ronda += 1
        entrada_actual = combate.orden_iniciativa[nuevo_indice]

        combate_actualizado = combate.model_copy(
            update={"indice_turno_actual": nuevo_indice, "ronda": nueva_ronda}
        )
        self.gestor.guardar(combate_actualizado)

        motivo = args.get("motivo")
        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "turno_avanzado",
                actor=_ACTOR_DM,
                objetivo=entrada_actual.participante_id,
                tool=self.nombre,
                motivo=motivo,
                datos={
                    "campaña_id": campaña_id,
                    "combate_id": combate.id,
                    "turno_anterior": entrada_anterior.participante_id,
                    "turno_actual": entrada_actual.participante_id,
                    "ronda": nueva_ronda,
                    "motivo": motivo,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "combate_id": combate.id,
                "turno_actual": entrada_actual.model_dump(mode="json"),
                "indice_turno_actual": nuevo_indice,
                "ronda": nueva_ronda,
                "combate": combate_actualizado.model_dump(mode="json"),
            },
        )


class _ToolAtacarEnemigo(_ToolCombateBase):
    nombre = "combate.atacar_enemigo"
    descripcion = (
        "Resuelve un ataque contra un enemigo: 1d20 (o 2d20 con ventaja/desventaja) + "
        "modificador_ataque + modificador_situacional contra su CA. Natural 1 (sobre la tirada "
        "elegida) falla siempre (pifia); natural 20 impacta siempre (crítico, daño duplicado). "
        "Si impacta, aplica daño al enemigo. No avanza turno: usa combate.avanzar_turno aparte."
    )
    modifica = ["combate", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
            "atacante_id": {"type": "string"},
            "enemigo_id": {"type": "string"},
            "modificador_ataque": {"type": "integer"},
            "dano": {"type": "string", "description": "Expresión de dados, ej. '1d8+3'."},
            "tipo_dano": {"type": "string"},
            "motivo": {"type": "string"},
            "modo_tirada": {
                "type": "string",
                "enum": list(_MODOS_TIRADA),
                "default": "normal",
                "description": "normal (1d20), ventaja o desventaja (2d20, mayor/menor).",
            },
            "modificador_situacional": {
                "type": "integer",
                "minimum": -10,
                "maximum": 10,
                "default": 0,
                "description": "Bonificador/penalizador narrativo simple.",
            },
            "motivo_modificador": {
                "type": "string",
                "description": "Motivo narrativo del modo_tirada/modificador_situacional.",
            },
            "semilla": {
                "type": "integer",
                "description": "Semilla opcional para tiradas reproducibles (tests/depuración).",
            },
        },
        "required": ["campaña_id", "combate_id", "atacante_id", "enemigo_id", "modificador_ataque", "dano"],
        "additionalProperties": False,
    }

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        combate, err = self._cargar(campaña_id, args.get("combate_id"))
        if err:
            return err
        assert combate is not None

        atacante_id = args.get("atacante_id")
        enemigo_id = args.get("enemigo_id")
        if not atacante_id or not enemigo_id:
            return ResultadoHerramienta(ok=False, errores=["faltan 'atacante_id' y/o 'enemigo_id'"])

        enemigo = next((e for e in combate.enemigos if e.id == enemigo_id), None)
        if enemigo is None:
            return ResultadoHerramienta(
                ok=False, errores=[f"enemigo no existe en este combate: {enemigo_id!r}"]
            )

        modificador, error_mod = _validar_modificador_ataque(args.get("modificador_ataque"))
        if error_mod:
            return ResultadoHerramienta(ok=False, errores=[error_mod])
        assert modificador is not None

        modo_tirada, error_modo = _validar_modo_tirada(args.get("modo_tirada"))
        if error_modo:
            return ResultadoHerramienta(ok=False, errores=[error_modo])
        assert modo_tirada is not None

        mod_situacional, error_sit = _validar_modificador_situacional(
            args.get("modificador_situacional")
        )
        if error_sit:
            return ResultadoHerramienta(ok=False, errores=[error_sit])
        assert mod_situacional is not None

        dano_expr = args.get("dano")
        if not isinstance(dano_expr, str) or not dano_expr.strip():
            return ResultadoHerramienta(
                ok=False, errores=["'dano' debe ser una expresión de dados no vacía (ej. '1d8+3')"]
            )

        tipo_dano = args.get("tipo_dano")
        motivo = args.get("motivo")
        motivo_modificador = args.get("motivo_modificador")
        resultado, error_dado = _resolver_ataque(
            atacante_id=atacante_id,
            objetivo_id=enemigo_id,
            modo_tirada=modo_tirada,
            modificador_ataque=modificador,
            modificador_situacional=mod_situacional,
            ca_objetivo=enemigo.ca,
            dano_expr=dano_expr,
            tipo_dano=tipo_dano,
            motivo=motivo,
            motivo_modificador=motivo_modificador,
            semilla=args.get("semilla"),
        )
        if error_dado:
            return error_dado
        assert resultado is not None

        hp_antes = enemigo.hp_actual
        hp_despues = hp_antes
        nuevo_estado = enemigo.estado
        combate_actualizado = combate
        if resultado.impacta:
            hp_despues = max(0, hp_antes - resultado.dano)
            nuevo_estado = _estado_tras_daño(hp_despues, enemigo.hp_max)
            enemigo_actualizado = enemigo.model_copy(
                update={"hp_actual": hp_despues, "estado": nuevo_estado}
            )
            nuevos_enemigos = [
                enemigo_actualizado if e.id == enemigo_id else e for e in combate.enemigos
            ]
            combate_actualizado = combate.model_copy(update={"enemigos": nuevos_enemigos})
            self.gestor.guardar(combate_actualizado)

        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "ataque_enemigo_resuelto",
                actor=_ACTOR_DM,
                objetivo=enemigo_id,
                tool=self.nombre,
                motivo=motivo,
                datos={
                    "campaña_id": campaña_id,
                    "combate_id": combate.id,
                    "atacante_id": atacante_id,
                    "objetivo_id": enemigo_id,
                    "modo_tirada": resultado.modo_tirada,
                    "tiradas_d20": resultado.tiradas_d20,
                    "tirada_d20": resultado.tirada_d20,
                    "modificador_ataque": modificador,
                    "modificador_situacional": mod_situacional,
                    "total_ataque": resultado.total_ataque,
                    "ca_objetivo": enemigo.ca,
                    "impacta": resultado.impacta,
                    "critico": resultado.critico,
                    "pifia": resultado.pifia,
                    "dano": resultado.dano,
                    "tipo_dano": tipo_dano,
                    "hp_antes": hp_antes,
                    "hp_despues": hp_despues,
                    "motivo": motivo,
                    "motivo_modificador": motivo_modificador,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "combate_id": combate.id,
                "atacante_id": atacante_id,
                "enemigo_id": enemigo_id,
                "modo_tirada": resultado.modo_tirada,
                "tiradas_d20": resultado.tiradas_d20,
                "tirada_d20": resultado.tirada_d20,
                "modificador_ataque": modificador,
                "modificador_situacional": mod_situacional,
                "total_ataque": resultado.total_ataque,
                "ca_objetivo": enemigo.ca,
                "impacta": resultado.impacta,
                "critico": resultado.critico,
                "pifia": resultado.pifia,
                "dano": resultado.dano,
                "tipo_dano": tipo_dano,
                "hp_antes": hp_antes,
                "hp_despues": hp_despues,
                "estado": nuevo_estado,
                "motivo_modificador": motivo_modificador,
                "combate": combate_actualizado.model_dump(mode="json"),
            },
        )


class _ToolAtacarPersonaje(_ToolCombateBase):
    nombre = "combate.atacar_personaje"
    descripcion = (
        "Resuelve un ataque de un enemigo contra el personaje jugador: 1d20 (o 2d20 con "
        "ventaja/desventaja) + modificador_ataque + modificador_situacional contra ficha.ca. "
        "Natural 1 (sobre la tirada elegida) falla siempre (pifia); natural 20 impacta siempre "
        "(crítico, daño duplicado). Si impacta, aplica daño directamente a la Ficha (no llama a "
        "hp_xp.aplicar_daño, para no duplicar evento). No avanza turno."
    )
    modifica = ["combate", "ficha", "eventos"]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "campaña_id": {"type": "string"},
            "combate_id": {"type": "string"},
            "enemigo_id": {"type": "string"},
            "personaje_id": {"type": "string"},
            "modificador_ataque": {"type": "integer"},
            "dano": {"type": "string", "description": "Expresión de dados, ej. '1d6+2'."},
            "tipo_dano": {"type": "string"},
            "motivo": {"type": "string"},
            "modo_tirada": {
                "type": "string",
                "enum": list(_MODOS_TIRADA),
                "default": "normal",
                "description": "normal (1d20), ventaja o desventaja (2d20, mayor/menor).",
            },
            "modificador_situacional": {
                "type": "integer",
                "minimum": -10,
                "maximum": 10,
                "default": 0,
                "description": "Bonificador/penalizador narrativo simple.",
            },
            "motivo_modificador": {
                "type": "string",
                "description": "Motivo narrativo del modo_tirada/modificador_situacional.",
            },
            "semilla": {
                "type": "integer",
                "description": "Semilla opcional para tiradas reproducibles (tests/depuración).",
            },
        },
        "required": [
            "campaña_id", "combate_id", "enemigo_id", "personaje_id", "modificador_ataque", "dano",
        ],
        "additionalProperties": False,
    }

    def __init__(
        self,
        gestor: GestorCombateNarrativo,
        registro_eventos: RegistroEventosEstado,
        gestor_estado: GestorEstado,
    ) -> None:
        super().__init__(gestor, registro_eventos)
        self.gestor_estado = gestor_estado

    def ejecutar(self, ctx: Any, **args: Any) -> ResultadoHerramienta:
        campaña_id = args.get("campaña_id")
        combate, err = self._cargar(campaña_id, args.get("combate_id"))
        if err:
            return err
        assert combate is not None

        enemigo_id = args.get("enemigo_id")
        personaje_id = args.get("personaje_id")
        if not enemigo_id or not personaje_id:
            return ResultadoHerramienta(ok=False, errores=["faltan 'enemigo_id' y/o 'personaje_id'"])

        enemigo = next((e for e in combate.enemigos if e.id == enemigo_id), None)
        if enemigo is None:
            return ResultadoHerramienta(
                ok=False, errores=[f"enemigo no existe en este combate: {enemigo_id!r}"]
            )
        if personaje_id != combate.personaje_id:
            return ResultadoHerramienta(
                ok=False,
                errores=[
                    f"'personaje_id' ({personaje_id!r}) no coincide con el personaje del "
                    f"combate ({combate.personaje_id!r})"
                ],
            )

        if not self.gestor_estado.existe_campaña(campaña_id):
            return ResultadoHerramienta(ok=False, errores=[f"campaña no existe: {campaña_id!r}"])
        try:
            ficha = self.gestor_estado.cargar_ficha(campaña_id, personaje_id)
        except ErrorEstadoNoEncontrado:
            return ResultadoHerramienta(ok=False, errores=[f"ficha no existe: {personaje_id!r}"])
        except ErrorEstado as e:
            return ResultadoHerramienta(ok=False, errores=[f"ficha inválida: {e}"])

        modificador, error_mod = _validar_modificador_ataque(args.get("modificador_ataque"))
        if error_mod:
            return ResultadoHerramienta(ok=False, errores=[error_mod])
        assert modificador is not None

        modo_tirada, error_modo = _validar_modo_tirada(args.get("modo_tirada"))
        if error_modo:
            return ResultadoHerramienta(ok=False, errores=[error_modo])
        assert modo_tirada is not None

        mod_situacional, error_sit = _validar_modificador_situacional(
            args.get("modificador_situacional")
        )
        if error_sit:
            return ResultadoHerramienta(ok=False, errores=[error_sit])
        assert mod_situacional is not None

        dano_expr = args.get("dano")
        if not isinstance(dano_expr, str) or not dano_expr.strip():
            return ResultadoHerramienta(
                ok=False, errores=["'dano' debe ser una expresión de dados no vacía (ej. '1d6+2')"]
            )

        tipo_dano = args.get("tipo_dano")
        motivo = args.get("motivo")
        motivo_modificador = args.get("motivo_modificador")
        resultado, error_dado = _resolver_ataque(
            atacante_id=enemigo_id,
            objetivo_id=personaje_id,
            modo_tirada=modo_tirada,
            modificador_ataque=modificador,
            modificador_situacional=mod_situacional,
            ca_objetivo=ficha.ca,
            dano_expr=dano_expr,
            tipo_dano=tipo_dano,
            motivo=motivo,
            motivo_modificador=motivo_modificador,
            semilla=args.get("semilla"),
        )
        if error_dado:
            return error_dado
        assert resultado is not None

        hp_antes = ficha.hp_actual
        hp_despues = hp_antes
        if resultado.impacta:
            hp_despues = max(0, hp_antes - resultado.dano)
            ficha_actualizada = Ficha.model_validate({**ficha.model_dump(), "hp_actual": hp_despues})
            self.gestor_estado.guardar_ficha(campaña_id, ficha_actualizada)

        self.eventos.registrar(
            campaña_id,
            crear_evento(
                "ataque_personaje_resuelto",
                actor=_ACTOR_DM,
                objetivo=personaje_id,
                tool=self.nombre,
                motivo=motivo,
                datos={
                    "campaña_id": campaña_id,
                    "combate_id": combate.id,
                    "atacante_id": enemigo_id,
                    "objetivo_id": personaje_id,
                    "modo_tirada": resultado.modo_tirada,
                    "tiradas_d20": resultado.tiradas_d20,
                    "tirada_d20": resultado.tirada_d20,
                    "modificador_ataque": modificador,
                    "modificador_situacional": mod_situacional,
                    "total_ataque": resultado.total_ataque,
                    "ca_objetivo": ficha.ca,
                    "impacta": resultado.impacta,
                    "critico": resultado.critico,
                    "pifia": resultado.pifia,
                    "dano": resultado.dano,
                    "tipo_dano": tipo_dano,
                    "hp_antes": hp_antes,
                    "hp_despues": hp_despues,
                    "motivo": motivo,
                    "motivo_modificador": motivo_modificador,
                },
            ),
        )
        return ResultadoHerramienta(
            ok=True,
            datos={
                "combate_id": combate.id,
                "enemigo_id": enemigo_id,
                "personaje_id": personaje_id,
                "modo_tirada": resultado.modo_tirada,
                "tiradas_d20": resultado.tiradas_d20,
                "tirada_d20": resultado.tirada_d20,
                "modificador_ataque": modificador,
                "modificador_situacional": mod_situacional,
                "total_ataque": resultado.total_ataque,
                "ca_objetivo": ficha.ca,
                "impacta": resultado.impacta,
                "critico": resultado.critico,
                "pifia": resultado.pifia,
                "dano": resultado.dano,
                "tipo_dano": tipo_dano,
                "hp_antes": hp_antes,
                "hp_despues": hp_despues,
                "estado_vital": estado_vital(hp_despues, ficha.hp_max),
                "motivo_modificador": motivo_modificador,
            },
        )


def crear_tools_combate(
    gestor: GestorCombateNarrativo,
    registro_eventos: RegistroEventosEstado,
    gestor_estado: GestorEstado,
) -> list[Any]:
    """Crea las diez tools de combate enlazadas a los gestores y al registro de eventos."""
    return [
        _ToolIniciar(gestor, registro_eventos),
        _ToolEstado(gestor, registro_eventos),
        _ToolAñadirEnemigo(gestor, registro_eventos),
        _ToolDañoEnemigo(gestor, registro_eventos),
        _ToolTerminar(gestor, registro_eventos),
        _ToolTirarIniciativa(gestor, registro_eventos),
        _ToolTurnoActual(gestor, registro_eventos),
        _ToolAvanzarTurno(gestor, registro_eventos),
        _ToolAtacarEnemigo(gestor, registro_eventos),
        _ToolAtacarPersonaje(gestor, registro_eventos, gestor_estado),
    ]
