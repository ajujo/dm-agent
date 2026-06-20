"""Contexto operativo activo (F6.5-B).

En pruebas reales, modelos locales inventan placeholders (`campaña_actual`,
`combate_actual`, `personaje_actual`, o "Tyr" en vez de "tyr") en lugar de
usar los IDs reales de la campaña/combate/personaje activos, aunque esos IDs
ya estén disponibles sin necesidad de preguntar. Este módulo construye un
bloque de texto con los IDs reales, derivados de los gestores existentes
(sin LLM, sin RAG, sin red): se inyecta como mensaje `system` adicional
*después* del bloque de memoria narrativa, para que sea lo último que el
modelo lea antes del historial de conversación y pese más en su decisión.

No es memoria narrativa (eso es `memoria/contexto.py`: continuidad de
historia). Esto es estado mecánico **actual**: qué combate/turno/ronda hay
en curso ahora mismo, recalculado en cada turno a partir de los gestores.
"""

from __future__ import annotations

from dm_agent.estado.combate import GestorCombateNarrativo

_AVISO_PLACEHOLDERS = (
    "Usa estos IDs reales en las herramientas.\n"
    "No uses placeholders como campaña_actual, combate_actual, personaje_actual "
    "o Tyr si el ID real es tyr."
)


def construir_bloque_contexto_operativo(
    gestor_combate: GestorCombateNarrativo,
    campaña_id: str,
    personaje_id: str | None = None,
) -> str:
    """Bloque "CONTEXTO OPERATIVO ACTUAL" con los IDs reales activos.

    `personaje_id`: si no se da, no hay (todavía) un mecanismo formal de
    "personaje activo" en `dm-agent` — se usa el `personaje_id` del combate
    activo de la campaña, si existe. Si no hay combate activo, el bloque de
    combate se omite explícitamente con un aviso ("sin combate activo
    detectado"), nunca falla.
    """
    combate = gestor_combate.cargar_activo(campaña_id)
    if not personaje_id and combate is not None:
        personaje_id = combate.personaje_id

    lineas = ["CONTEXTO OPERATIVO ACTUAL", "", f"- campaña_id activa: {campaña_id}"]
    if personaje_id:
        lineas.append(f"- personaje_id activo: {personaje_id}")

    if combate is None:
        lineas.append("- combate: sin combate activo detectado")
    else:
        lineas.append(f"- combate_id activo: {combate.id}")
        lineas.append(f"- estado combate: {combate.estado}")
        lineas.append(f"- ronda: {combate.ronda}")
        if combate.orden_iniciativa:
            turno_actual = combate.orden_iniciativa[combate.indice_turno_actual]
            lineas.append(f"- turno actual: {turno_actual.participante_id}")

    lineas += ["", _AVISO_PLACEHOLDERS]
    return "\n".join(lineas)
