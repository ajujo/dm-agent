"""Construcción del bloque de memoria narrativa para el contexto del agente (F4.3).

Lee la bitácora narrativa de una campaña y produce un bloque Markdown **compacto**
que se inyecta como segundo mensaje `system` (continuidad), sin tocar ficheros ni
llamar al LLM.

No es RAG ni búsqueda semántica: es una ventana reciente (último resumen + N
entradas recientes no-resumen). Coherente con D17: continuidad narrativa, no log
táctico.
"""

from __future__ import annotations

from dm_agent.esquemas.narrativa import EntradaNarrativa
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa

_AVISO = (
    "Usa esta memoria solo para mantener continuidad. No inventes hechos nuevos a "
    "partir de ella. Si algo no está claro, pregunta o mantén la ambigüedad."
)

# Ventana de lectura acotada (no inyectamos toda la bitácora, pero leemos un poco
# más para poder localizar el último resumen aunque no esté entre las últimas N).
_VENTANA_LECTURA = 200
# Longitud máxima de cada línea de entrada reciente.
_MAX_LINEA = 240


def _linea_entrada(e: EntradaNarrativa) -> str:
    titulo = e.titulo.strip() if e.titulo else ""
    contenido = " ".join(e.contenido.split())
    # Incluimos título Y contenido: el contenido es lo que de verdad da
    # continuidad (p. ej. el punto de arranque de una entrada `siguiente_sesion`).
    texto = f"{titulo}: {contenido}" if titulo else contenido
    if len(texto) > _MAX_LINEA:
        texto = texto[: _MAX_LINEA - 1].rstrip() + "…"
    return f"- [{e.tipo}] {texto}"


class ConstructorContextoMemoria:
    def __init__(
        self,
        gestor_memoria: GestorMemoriaNarrativa,
        limite_entradas: int = 8,
        incluir_resumenes: bool = True,
    ) -> None:
        self.memoria = gestor_memoria
        self.limite_entradas = max(0, limite_entradas)
        self.incluir_resumenes = incluir_resumenes

    def construir_bloque_memoria(self, campaña_id: str) -> str:
        """Devuelve un bloque Markdown de memoria, o cadena vacía si no hay nada."""
        entradas = self.memoria.listar_entradas(campaña_id, limite=_VENTANA_LECTURA)
        if not entradas:
            return ""

        resumen = None
        if self.incluir_resumenes:
            resumenes = [e for e in entradas if e.tipo == "resumen"]
            if resumenes:
                resumen = resumenes[-1]  # el más reciente

        no_resumen = [e for e in entradas if e.tipo != "resumen"]
        recientes = no_resumen[-self.limite_entradas :] if self.limite_entradas else []

        if resumen is None and not recientes:
            return ""

        partes = ["# Memoria narrativa de campaña", "", _AVISO]
        if resumen is not None:
            partes += ["", "## Resumen reciente", "", resumen.contenido.strip()]
        if recientes:
            partes += ["", "## Entradas recientes", ""]
            partes += [_linea_entrada(e) for e in recientes]
        return "\n".join(partes)
