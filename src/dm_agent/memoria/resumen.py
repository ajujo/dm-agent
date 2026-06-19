"""Resumidor narrativo con LLM (F4.2).

Consolida material narrativo (entradas recientes de la bitácora, o un texto de
escena/sesión) en un resumen útil para continuidad, y lo persiste como una
`EntradaNarrativa(tipo="resumen")`.

Coherente con D17 (narrativo en solitario / teatro de la mente): el resumen
favorece continuidad (estado, decisiones, PNJ, pistas, consecuencias, ganchos),
no es un registro táctico. El prompt prohíbe inventar, spoilers, resolver
decisiones pendientes o tocar mecánicas.

No hay inyección automática al contexto del agente todavía (eso es F4.3).
"""

from __future__ import annotations

from dm_agent.esquemas.narrativa import EntradaNarrativa, crear_entrada
from dm_agent.llm.cliente import ClienteLLM
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.prompts import RESUMEN_NARRATIVO, cargar_prompt


class ErrorResumen(Exception):
    """Base de errores del resumidor narrativo."""


class SinEntradasParaResumir(ErrorResumen):
    """No hay entradas narrativas que resumir."""


class MaterialVacio(ErrorResumen):
    """El texto a resumir está vacío."""


class ResumenVacio(ErrorResumen):
    """El LLM devolvió un resumen vacío."""


class ResumidorNarrativo:
    def __init__(
        self, cliente_llm: ClienteLLM, gestor_memoria: GestorMemoriaNarrativa
    ) -> None:
        self.cliente = cliente_llm
        self.memoria = gestor_memoria
        self.system_prompt = cargar_prompt(RESUMEN_NARRATIVO)

    def _resumir_material(
        self, campaña_id: str, material: str, *, titulo: str, sesion_id: str | None
    ) -> EntradaNarrativa:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": material},
        ]
        respuesta = self.cliente.chat(messages, stream=False)
        contenido = (respuesta.content or "").strip()
        if not contenido:
            raise ResumenVacio("el modelo devolvió un resumen vacío")
        entrada = crear_entrada(
            campaña_id,
            "resumen",
            contenido,
            titulo=titulo,
            tags=["resumen"],
            importancia=5,
            origen="resumen",
            sesion_id=sesion_id,
        )
        self.memoria.registrar_entrada(entrada)
        return entrada

    def resumir_texto(
        self, campaña_id: str, texto: str, sesion_id: str | None = None
    ) -> EntradaNarrativa:
        if not texto or not texto.strip():
            raise MaterialVacio("el texto a resumir está vacío")
        return self._resumir_material(
            campaña_id, texto.strip(), titulo="Resumen de escena", sesion_id=sesion_id
        )

    def resumir_entradas(
        self, campaña_id: str, limite: int = 20, sesion_id: str | None = None
    ) -> EntradaNarrativa:
        entradas = self.memoria.listar_entradas(campaña_id, limite=limite)
        if not entradas:
            raise SinEntradasParaResumir(f"sin entradas narrativas en {campaña_id!r}")
        # Material = las mismas entradas que vamos a resumir, en Markdown.
        material = self.memoria.ultimas_entradas_markdown(campaña_id, limite=limite)
        return self._resumir_material(
            campaña_id, material, titulo="Resumen de sesión", sesion_id=sesion_id
        )
