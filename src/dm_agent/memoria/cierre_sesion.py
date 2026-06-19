"""Cierre y preparación de sesión narrativa (F4.4).

Toma el texto de una sesión, pide al LLM un **resumen de cierre** + una
**preparación de la próxima sesión**, y guarda **dos** `EntradaNarrativa` en la
bitácora de la campaña:

- `tipo="resumen"`        → qué pasó / estado / consecuencias abiertas.
- `tipo="siguiente_sesion"` → punto exacto de arranque de la próxima sesión.

Ambas comparten `campaña_id` y `sesion_id` (enlace claro campaña↔sesión, deuda de
F4.3 resuelta de forma mínima). Coherente con D17 (continuidad narrativa).
"""

from __future__ import annotations

from dm_agent.esquemas.narrativa import EntradaNarrativa, crear_entrada
from dm_agent.llm.cliente import ClienteLLM
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.prompts import CIERRE_SESION, cargar_prompt

_H_RESUMEN = "# Resumen de cierre"
_H_PREP = "# Preparación de próxima sesión"
_PREP_POR_DEFECTO = "Pendiente de preparar a partir del resumen anterior."


class ErrorCierre(Exception):
    """Base de errores del cierre de sesión."""


class TextoSesionVacio(ErrorCierre):
    """No hay texto de sesión que cerrar."""


class CierreVacio(ErrorCierre):
    """El LLM devolvió un cierre vacío."""


def _parsear_cierre(texto: str) -> tuple[str, str]:
    """Devuelve (resumen, preparacion). Degradación documentada: si no hay
    encabezados, todo va a resumen y la preparación queda como pendiente."""
    if _H_RESUMEN in texto and _H_PREP in texto:
        _, resto = texto.split(_H_RESUMEN, 1)
        resumen, preparacion = resto.split(_H_PREP, 1)
    elif _H_PREP in texto:
        resumen, preparacion = texto.split(_H_PREP, 1)
        resumen = resumen.replace(_H_RESUMEN, "")
    else:
        # Sin encabezados esperados: todo como resumen, preparación mínima.
        resumen, preparacion = texto, _PREP_POR_DEFECTO

    resumen = resumen.strip() or texto.strip()
    preparacion = preparacion.strip() or _PREP_POR_DEFECTO
    return resumen, preparacion


class CierreSesionNarrativa:
    def __init__(
        self, cliente_llm: ClienteLLM, gestor_memoria: GestorMemoriaNarrativa
    ) -> None:
        self.cliente = cliente_llm
        self.memoria = gestor_memoria
        self.system_prompt = cargar_prompt(CIERRE_SESION)

    def cerrar_sesion(
        self, campaña_id: str, sesion_id: str, texto_sesion: str
    ) -> dict[str, EntradaNarrativa]:
        if not texto_sesion or not texto_sesion.strip():
            raise TextoSesionVacio("no hay texto de sesión que cerrar")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": texto_sesion.strip()},
        ]
        respuesta = self.cliente.chat(messages, stream=False)
        contenido = (respuesta.content or "").strip()
        if not contenido:
            raise CierreVacio("el modelo devolvió un cierre vacío")

        texto_resumen, texto_prep = _parsear_cierre(contenido)

        entrada_resumen = crear_entrada(
            campaña_id, "resumen", texto_resumen,
            titulo="Resumen de cierre", tags=["resumen", "cierre"],
            importancia=5, origen="resumen", sesion_id=sesion_id,
        )
        self.memoria.registrar_entrada(entrada_resumen)

        entrada_prep = crear_entrada(
            campaña_id, "siguiente_sesion", texto_prep,
            titulo="Preparación de próxima sesión", tags=["preparacion", "siguiente_sesion"],
            importancia=5, origen="resumen", sesion_id=sesion_id,
        )
        self.memoria.registrar_entrada(entrada_prep)

        return {"resumen": entrada_resumen, "preparacion": entrada_prep}
