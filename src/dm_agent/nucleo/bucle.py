"""REPL mínima y cableado del agente (F2.2).

Mantiene `cli.py` fino: aquí viven el factory del agente, el controlador de la
sesión interactiva y el bucle de lectura/escritura. El bucle recibe `leer`/
`escribir` inyectables para poder testearse sin terminal ni red.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.dados import crear_tool_dados
from dm_agent.herramientas.ficha import crear_tools_ficha
from dm_agent.herramientas.hp_xp import crear_tools_hp_xp
from dm_agent.herramientas.inventario import crear_tools_inventario
from dm_agent.herramientas.narrativa import crear_tools_narrativa
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.herramientas.resumen import crear_tools_resumen
from dm_agent.llm.cliente import ClienteLLM, ErrorLLM
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.memoria.resumen import ResumidorNarrativo
from dm_agent.nucleo.agente import AgenteDM
from dm_agent.persistencia.sesion import Sesion
from dm_agent.prompts import SYSTEM_DM_MINIMO, cargar_prompt

_RAIZ = Path(__file__).resolve().parents[3]
_CONFIG_POR_DEFECTO = _RAIZ / "config"

COMANDOS = {
    "/ayuda": "muestra esta ayuda",
    "/salir": "termina la sesión",
    "/guardar": "fuerza el guardado de la sesión",
    "/continuar": "muestra la sesión activa (id y nº de registros)",
    "/nueva": "crea una sesión nueva",
    "/debug": "activa/desactiva la traza de depuración",
}


def _texto_ayuda() -> str:
    lineas = ["Comandos disponibles:"]
    lineas += [f"  {cmd:<11} {desc}" for cmd, desc in COMANDOS.items()]
    lineas.append("Cualquier otra cosa que escribas se envía al Director de Juego.")
    return "\n".join(lineas)


def _crear_registro(
    gestor: GestorEstado,
    registro_eventos: RegistroEventosEstado,
    memoria_narrativa: GestorMemoriaNarrativa,
    resumidor: ResumidorNarrativo,
) -> RegistroHerramientas:
    registro = RegistroHerramientas()
    registro.registrar(crear_tool_dados())
    for tool in crear_tools_ficha(gestor):
        registro.registrar(tool)
    for tool in crear_tools_hp_xp(gestor, registro_eventos):
        registro.registrar(tool)
    for tool in crear_tools_inventario(gestor, registro_eventos):
        registro.registrar(tool)
    for tool in crear_tools_narrativa(memoria_narrativa):
        registro.registrar(tool)
    for tool in crear_tools_resumen(resumidor):
        registro.registrar(tool)
    return registro


def _raiz_storage(proyecto: dict[str, Any], config_dir: Path) -> Path:
    storage = proyecto.get("rutas", {}).get("storage", "./storage")
    raiz = config_dir.resolve().parent
    return (raiz / storage).resolve()


def _dir_sesiones(proyecto: dict[str, Any], config_dir: Path) -> Path:
    return _raiz_storage(proyecto, config_dir) / "sesiones"


class SesionInteractiva:
    """Tiene todo lo necesario para procesar turnos y gestionar la sesión."""

    def __init__(
        self,
        *,
        perfil: str | None = None,
        config_dir: Path | None = None,
        debug: bool = False,
        http_client: Any | None = None,
    ) -> None:
        self.config_dir = (config_dir or _CONFIG_POR_DEFECTO).resolve()
        proyecto_path = self.config_dir / "proyecto.json"
        try:
            self.proyecto = json.loads(proyecto_path.read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            raise ErrorLLM(f"no se encuentra {proyecto_path}") from e

        self.perfil = perfil or self.proyecto.get("perfil_por_defecto", "rapido")
        self.max_iter = int(self.proyecto.get("max_iter_turno", 8))
        self.debug = debug
        self.dir_sesiones = _dir_sesiones(self.proyecto, self.config_dir)
        self._http_client = http_client

        # Cliente y registro (desde_config NO hace red; solo valida config).
        self.cliente = ClienteLLM.desde_config(
            self.perfil, config_dir=self.config_dir, http_client=http_client
        )
        raiz_storage = _raiz_storage(self.proyecto, self.config_dir)
        self.gestor = GestorEstado(raiz_storage)
        self.registro_eventos = RegistroEventosEstado(raiz_storage)
        self.memoria_narrativa = GestorMemoriaNarrativa(raiz_storage)
        self.resumidor = ResumidorNarrativo(self.cliente, self.memoria_narrativa)
        self.registro = _crear_registro(
            self.gestor, self.registro_eventos, self.memoria_narrativa, self.resumidor
        )
        self.system_prompt = cargar_prompt(SYSTEM_DM_MINIMO)

        self.sesion: Sesion | None = None
        self.agente: AgenteDM | None = None

    # -- Gestión de sesión -----------------------------------------------------

    def _construir_agente(self) -> None:
        assert self.sesion is not None
        self.agente = AgenteDM(
            self.cliente,
            self.registro,
            self.sesion,
            system_prompt=self.system_prompt,
            max_iter_turno=self.max_iter,
            debug=self.debug,
        )

    def nueva_sesion(self) -> str:
        self.sesion = Sesion.crear(self.dir_sesiones)
        self._construir_agente()
        return f"Sesión nueva: {self.sesion.id}"

    def continuar_ultima(self) -> str:
        ultima = Sesion.ultima(self.dir_sesiones)
        if ultima is None:
            return self.nueva_sesion() + " (no había sesión previa)"
        self.sesion = ultima
        self._construir_agente()
        return f"Continuando sesión: {self.sesion.id} ({len(self.sesion)} registros)"

    def info_sesion(self) -> str:
        if self.sesion is None:
            return "No hay sesión activa."
        return f"Sesión activa: {self.sesion.id} ({len(self.sesion)} registros) en {self.sesion.ruta}"

    def guardar(self) -> str:
        # JSONL es append-only: cada turno ya está en disco. Es informativo.
        if self.sesion is None:
            return "No hay sesión activa que guardar."
        return f"Sesión {self.sesion.id} al día (JSONL append-only, ya persistido)."

    def alternar_debug(self) -> str:
        self.debug = not self.debug
        if self.agente is not None:
            self.agente.debug = self.debug
        return f"debug = {'on' if self.debug else 'off'}"

    def procesar(self, texto: str) -> str:
        if self.agente is None:
            self.nueva_sesion()
        assert self.agente is not None
        return self.agente.responder(texto)


def repl(
    ctx: Any,
    *,
    leer: Callable[[str], str] | None = None,
    escribir: Callable[[str], None] | None = None,
) -> int:
    """Bucle REPL. `ctx` debe exponer procesar/info_sesion/guardar/
    nueva_sesion/alternar_debug (ver `SesionInteractiva`).

    `leer`/`escribir` se resuelven en tiempo de llamada (no como defaults
    capturados) para que sean inyectables y monkeypatcheables en tests."""
    leer = leer or input
    escribir = escribir or print
    escribir("dm-agent — escribe /ayuda para ver los comandos. /salir para terminar.")
    while True:
        try:
            entrada = leer("> ")
        except (EOFError, KeyboardInterrupt):
            escribir("\nHasta la próxima.")
            return 0

        texto = entrada.strip()
        if not texto:
            continue

        if texto in ("/salir", "/exit", "/quit"):
            escribir("Hasta la próxima.")
            return 0
        if texto == "/ayuda":
            escribir(_texto_ayuda())
            continue
        if texto == "/guardar":
            escribir(ctx.guardar())
            continue
        if texto == "/continuar":
            escribir(ctx.info_sesion())
            continue
        if texto == "/nueva":
            escribir(ctx.nueva_sesion())
            continue
        if texto == "/debug":
            escribir(ctx.alternar_debug())
            continue
        if texto.startswith("/"):
            escribir(f"Comando desconocido: {texto}. Usa /ayuda.")
            continue

        try:
            escribir(ctx.procesar(texto))
        except ErrorLLM as e:
            escribir(f"[error del modelo/endpoint] {e}")
