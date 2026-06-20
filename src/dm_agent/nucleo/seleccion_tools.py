"""Selección contextual de tools por turno (F6.2).

Algunos modelos locales, con muchas tools y schemas complejos a la vez,
fallan en emitir una tool call real incluso después de la disciplina de
F6.1/F6.1.1 (prompt + detector de pseudo-calls JSON/XML): en vez de eso
escriben texto que *parece* una llamada a herramienta. Reducir el número de
tools ofrecidas en cada turno, según la intención del mensaje del usuario,
mejora la probabilidad de que el modelo elija y llame una tool real.

Esta capa es una simple coincidencia de palabras clave, **determinista y sin
LLM**: no decide mecánica, no ejecuta nada, solo decide qué subconjunto de
esquemas de tools se expone a `ClienteLLM.chat(tools=...)`. Si no se
reconoce ninguna categoría con señal clara, `seleccionar_tools_para_turno`
devuelve `None`, que el llamador debe interpretar como "mantener el
comportamiento anterior" (ofrecer todas las tools disponibles) — es el
fallback seguro para mensajes ambiguos.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

# -- Tools por categoría (nombres API, ya transliterados a ASCII) -----------

TOOLS_FICHA = frozenset(
    {
        "ficha_leer",
        "ficha_guardar",
        "ficha_validar",
        "ficha_actualizar",
        "ficha_listar",
        "hp_xp_consultar_estado_vital",
    }
)

TOOLS_INVENTARIO = frozenset(
    {
        "inventario_listar",
        "inventario_anadir",
        "inventario_quitar",
        "inventario_equipar",
        "inventario_desequipar",
        "ficha_leer",
    }
)

TOOLS_COMBATE_GENERAL = frozenset(
    {
        "combate_iniciar",
        "combate_estado",
        "combate_anadir_enemigo",
        "combate_dano_enemigo",
        "combate_terminar",
        "combate_tirar_iniciativa",
        "combate_turno_actual",
        "combate_avanzar_turno",
        "combate_atacar_enemigo",
        "combate_atacar_personaje",
        "combate_registrar_accion_turno",
        "combate_proponer_reaccion",
        "combate_resolver_reaccion",
        "combate_listar_reacciones",
    }
)

TOOLS_ATAQUE = frozenset(
    {
        "combate_estado",
        "combate_turno_actual",
        "combate_atacar_enemigo",
        "combate_atacar_personaje",
        "combate_registrar_accion_turno",
    }
)

TOOLS_INICIATIVA = frozenset(
    {
        "combate_estado",
        "combate_tirar_iniciativa",
        "combate_turno_actual",
        "combate_avanzar_turno",
    }
)

TOOLS_REACCION = frozenset(
    {
        "combate_estado",
        "combate_proponer_reaccion",
        "combate_resolver_reaccion",
        "combate_listar_reacciones",
        "combate_atacar_enemigo",
        "combate_atacar_personaje",
    }
)

TOOLS_MEMORIA = frozenset(
    {
        "narrativa_registrar",
        "narrativa_reciente",
        "resumen_entradas",
        "resumen_texto",
        "sesion_cerrar",
        "sesion_cerrar_texto",
    }
)

# -- Palabras clave por categoría --------------------------------------------

_PALABRAS_FICHA = {
    "ficha",
    "personaje",
    "tyr",
    "hp",
    "ca",
    "atributos",
    "destreza",
    "fuerza",
    "constitución",
    "nivel",
    "clase",
    "raza",
}

_PALABRAS_INVENTARIO = {
    "inventario",
    "objeto",
    "arma",
    "espada",
    "escudo",
    "poción",
    "equipo",
    "equipar",
    "desequipar",
}

_PALABRAS_COMBATE_GENERAL = {
    "combate",
    "enemigo",
    "rata",
    "iniciativa",
    "turno",
    "ronda",
    "ataque",
    "ataca",
    "daño",
    "ca",
    "ventaja",
    "desventaja",
    "reacción",
    "oportunidad",
}

_PALABRAS_ATAQUE = {
    "ataca",
    "atacar",
    "ataque",
    "golpea",
    "dispara",
    "muerde",
    "daño",
    "espada",
    "arco",
    "mordisco",
}

_PALABRAS_INICIATIVA = {
    "iniciativa",
    "turno",
    "ronda",
    "orden",
    "avanza",
    "avanzar",
}

_PALABRAS_REACCION = {
    "reacción",
    "ataque de oportunidad",
    "oportunidad",
    "confirmar",
    "rechazar",
    "caducar",
}

_PALABRAS_MEMORIA = {
    "recuerda",
    "memoria",
    "bitácora",
    "resumen",
    "cerrar sesión",
    "cerrar",
    "continuar",
    "próxima sesión",
}


def _sin_acentos(texto: str) -> str:
    """Translitera a ASCII quitando diacríticos, para que la detección de
    palabras clave no dependa de que el usuario (o el modelo) escriba los
    acentos correctos."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _compilar_patron(palabras: set[str]) -> re.Pattern[str]:
    normalizadas = sorted({_sin_acentos(p.lower()) for p in palabras}, key=len, reverse=True)
    alternativas = "|".join(re.escape(p) for p in normalizadas)
    return re.compile(rf"\b(?:{alternativas})\b")


_PATRON_FICHA = _compilar_patron(_PALABRAS_FICHA)
_PATRON_INVENTARIO = _compilar_patron(_PALABRAS_INVENTARIO)
_PATRON_COMBATE_GENERAL = _compilar_patron(_PALABRAS_COMBATE_GENERAL)
_PATRON_ATAQUE = _compilar_patron(_PALABRAS_ATAQUE)
_PATRON_INICIATIVA = _compilar_patron(_PALABRAS_INICIATIVA)
_PATRON_REACCION = _compilar_patron(_PALABRAS_REACCION)
_PATRON_MEMORIA = _compilar_patron(_PALABRAS_MEMORIA)


def seleccionar_tools_para_turno(
    mensaje_usuario: str,
    historial: Sequence[str] | None = None,
    estado_opcional: object | None = None,
) -> frozenset[str] | None:
    """Devuelve el conjunto de nombres API de tools relevantes para el turno,
    o `None` si no se reconoce ninguna categoría con señal clara (el
    llamador debe interpretarlo como "ofrecer todas las tools disponibles",
    el comportamiento anterior a F6.2).

    `historial` y `estado_opcional` existen para dejar la firma abierta a
    señal adicional de la conversación, pero la versión actual decide solo a
    partir de `mensaje_usuario`: añadir más señal sin evidencia de que haga
    falta sería sobre-ingeniería.
    """
    del estado_opcional  # reservado para señal futura; no usado todavía.
    texto = mensaje_usuario or ""
    if historial:
        texto = " ".join([*historial, texto])
    texto_norm = _sin_acentos(texto.lower())

    coincide_ficha = bool(_PATRON_FICHA.search(texto_norm))
    coincide_inventario = bool(_PATRON_INVENTARIO.search(texto_norm))
    coincide_combate_general = bool(_PATRON_COMBATE_GENERAL.search(texto_norm))
    coincide_ataque = bool(_PATRON_ATAQUE.search(texto_norm))
    coincide_iniciativa = bool(_PATRON_INICIATIVA.search(texto_norm))
    coincide_reaccion = bool(_PATRON_REACCION.search(texto_norm))
    coincide_memoria = bool(_PATRON_MEMORIA.search(texto_norm))

    if not any(
        (
            coincide_ficha,
            coincide_inventario,
            coincide_combate_general,
            coincide_ataque,
            coincide_iniciativa,
            coincide_reaccion,
            coincide_memoria,
        )
    ):
        return None

    seleccion: set[str] = set()
    if coincide_ficha:
        seleccion |= TOOLS_FICHA
    if coincide_inventario:
        seleccion |= TOOLS_INVENTARIO
    if coincide_memoria:
        seleccion |= TOOLS_MEMORIA

    # Las categorías de combate específicas (ataque/iniciativa/reacción) son
    # subconjuntos deliberadamente pequeños: si alguna coincide, no se cae al
    # conjunto completo de las 14 tools de combate ("salvo que sea
    # necesario", según F6.2) aunque también coincidan palabras genéricas de
    # combate (p. ej. "ataca a la rata" coincide con "combate"/"enemigo").
    especifica_combate = coincide_ataque or coincide_iniciativa or coincide_reaccion
    if coincide_ataque:
        seleccion |= TOOLS_ATAQUE
    if coincide_iniciativa:
        seleccion |= TOOLS_INICIATIVA
    if coincide_reaccion:
        seleccion |= TOOLS_REACCION
    if coincide_combate_general and not especifica_combate:
        seleccion |= TOOLS_COMBATE_GENERAL

    return frozenset(seleccion)
