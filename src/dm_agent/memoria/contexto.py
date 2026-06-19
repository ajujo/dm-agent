"""Construcción del bloque de memoria narrativa para el contexto del agente (F4.3).

Lee la bitácora narrativa de una campaña y produce un bloque Markdown **compacto**
que se inyecta como segundo mensaje `system` (continuidad), sin tocar ficheros ni
llamar al LLM.

No es RAG ni búsqueda semántica: es una ventana reciente (último resumen + N
entradas recientes no-resumen). Coherente con D17: continuidad narrativa, no log
táctico.
"""

from __future__ import annotations

from dm_agent.esquemas.entidades import EntidadBase, FrenteAbierto
from dm_agent.esquemas.narrativa import EntradaNarrativa
from dm_agent.memoria.entidades import GestorEntidadesNarrativas
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa

_AVISO = (
    "Usa esta memoria solo para mantener continuidad. No inventes hechos nuevos a "
    "partir de ella. Si algo no está claro, pregunta o mantén la ambigüedad."
)

# Ventana de lectura acotada (no inyectamos toda la bitácora, pero leemos un poco
# más para poder localizar el último resumen aunque no esté entre las últimas N).
_VENTANA_LECTURA = 200
# Longitud máxima de cada línea de entrada reciente / entidad.
_MAX_LINEA = 240


def _truncar(texto: str, maximo: int = _MAX_LINEA) -> str:
    if len(texto) > maximo:
        return texto[: maximo - 1].rstrip() + "…"
    return texto


def _linea_entrada(e: EntradaNarrativa) -> str:
    titulo = e.titulo.strip() if e.titulo else ""
    contenido = " ".join(e.contenido.split())
    # Incluimos título Y contenido: el contenido es lo que de verdad da
    # continuidad (p. ej. el punto de arranque de una entrada `siguiente_sesion`).
    texto = f"{titulo}: {contenido}" if titulo else contenido
    return f"- [{e.tipo}] {_truncar(texto)}"


def _linea_entidad(e: EntidadBase, *, sufijo_nombre: str = "") -> str:
    nombre = e.nombre.strip()
    if sufijo_nombre:
        nombre = f"{nombre}, {sufijo_nombre}"
    texto = f"- {nombre}"
    descripcion = " ".join(e.descripcion.split()) if e.descripcion else ""
    if descripcion:
        texto += f": {descripcion}"
    if e.estado:
        texto += f". Estado: {e.estado}."
    return _truncar(texto)


def _linea_frente(f: FrenteAbierto) -> str:
    texto = f"- {f.nombre.strip()}"
    descripcion = " ".join(f.descripcion.split()) if f.descripcion else ""
    if descripcion:
        texto += f": {descripcion}"
    if f.reloj is not None:
        texto += f". Reloj: {f.reloj}/6."
    elif f.estado:
        texto += f". Estado: {f.estado}."
    return _truncar(texto)


class ConstructorContextoMemoria:
    def __init__(
        self,
        gestor_memoria: GestorMemoriaNarrativa,
        limite_entradas: int = 8,
        incluir_resumenes: bool = True,
        gestor_entidades: GestorEntidadesNarrativas | None = None,
        limite_entidades: int = 8,
    ) -> None:
        self.memoria = gestor_memoria
        self.limite_entradas = max(0, limite_entradas)
        self.incluir_resumenes = incluir_resumenes
        # Entidades narrativas estructuradas (F4.6): opcional, ninguna inyección
        # de entidades si no hay gestor (compatibilidad con llamadas previas).
        self.gestor_entidades = gestor_entidades
        self.limite_entidades = max(0, limite_entidades)

    def _seccion_entidades(self, campaña_id: str) -> str:
        if self.gestor_entidades is None or self.limite_entidades <= 0:
            return ""
        n = self.limite_entidades
        pnjs = self.gestor_entidades.listar_pnj(campaña_id)[:n]
        lugares = self.gestor_entidades.listar_lugares(campaña_id)[:n]
        pistas = self.gestor_entidades.listar_pistas(campaña_id)[:n]
        objetivos = self.gestor_entidades.listar_objetivos(campaña_id)[:n]
        frentes = self.gestor_entidades.listar_frentes(campaña_id)[:n]

        bloques: list[str] = []
        if pnjs:
            bloques += ["### PNJ", ""] + [_linea_entidad(p, sufijo_nombre=p.rol or "") for p in pnjs]
        if lugares:
            if bloques:
                bloques.append("")
            bloques += ["### Lugares", ""] + [
                _linea_entidad(lugar, sufijo_nombre=lugar.tipo or "") for lugar in lugares
            ]
        if pistas:
            if bloques:
                bloques.append("")
            bloques += ["### Pistas", ""] + [_linea_entidad(p) for p in pistas]
        if objetivos:
            if bloques:
                bloques.append("")
            bloques += ["### Objetivos", ""] + [_linea_entidad(o) for o in objetivos]
        if frentes:
            if bloques:
                bloques.append("")
            bloques += ["### Frentes abiertos", ""] + [_linea_frente(f) for f in frentes]

        if not bloques:
            return ""
        return "\n".join(["## Entidades importantes", ""] + bloques)

    def construir_bloque_memoria(self, campaña_id: str) -> str:
        """Devuelve un bloque Markdown de memoria, o cadena vacía si no hay nada."""
        entradas = self.memoria.listar_entradas(campaña_id, limite=_VENTANA_LECTURA)

        resumen = None
        if self.incluir_resumenes:
            resumenes = [e for e in entradas if e.tipo == "resumen"]
            if resumenes:
                resumen = resumenes[-1]  # el más reciente

        no_resumen = [e for e in entradas if e.tipo != "resumen"]
        recientes = no_resumen[-self.limite_entradas :] if self.limite_entradas else []

        seccion_entidades = self._seccion_entidades(campaña_id)

        if resumen is None and not recientes and not seccion_entidades:
            return ""

        partes = ["# Memoria narrativa de campaña", "", _AVISO]
        if resumen is not None:
            partes += ["", "## Resumen reciente", "", resumen.contenido.strip()]
        if recientes:
            partes += ["", "## Entradas recientes", ""]
            partes += [_linea_entrada(e) for e in recientes]
        if seccion_entidades:
            partes += ["", seccion_entidades]
        return "\n".join(partes)
