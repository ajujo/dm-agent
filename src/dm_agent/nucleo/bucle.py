"""REPL mínima y cableado del agente (F2.2).

Mantiene `cli.py` fino: aquí viven el factory del agente, el controlador de la
sesión interactiva y el bucle de lectura/escritura. El bucle recibe `leer`/
`escribir` inyectables para poder testearse sin terminal ni red.

F6.4: además del flujo normal (usuario → LLM → tool calls), el comando
`/tool <nombre_tool_api> <json_argumentos>` ejecuta una tool real
directamente desde el REPL, sin pasar por el LLM. Es una vía de depuración/
recuperación manual para cuando un modelo local no emite una tool call real
aunque la tool esté disponible (ver F6.1-F6.3): el usuario puede forzar la
ejecución él mismo. No se añade al historial conversacional del LLM (no
pasa por `Sesion.registrar_usuario`/`registrar_asistente`).

F6.5-C: `/tool` es potente pero incómodo para operaciones frecuentes (hay
que escribir el JSON entero a mano). `/combate`, `/turno`, `/reacciones`,
`/ficha` y `/estado` son atajos sobre el mismo mecanismo (`dispatch_api`
directo, sin LLM): resuelven `campaña_id`/`combate_id`/`personaje_id` solos
a partir del combate activo de la campaña (mismo origen que el contexto
operativo de F6.5-B), así que no hace falta escribir esos IDs cada vez.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dm_agent.esquemas.combate import CombateNarrativo
from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.combate import crear_tools_combate
from dm_agent.herramientas.dados import crear_tool_dados
from dm_agent.herramientas.entidades import crear_tools_entidades
from dm_agent.herramientas.ficha import crear_tools_ficha
from dm_agent.herramientas.hp_xp import crear_tools_hp_xp
from dm_agent.herramientas.inventario import crear_tools_inventario
from dm_agent.herramientas.narrativa import crear_tools_narrativa
from dm_agent.herramientas.registro import HerramientaNoRegistrada, RegistroHerramientas
from dm_agent.herramientas.resumen import crear_tools_resumen
from dm_agent.herramientas.sesion import crear_tools_sesion
from dm_agent.llm.cliente import ClienteLLM, ErrorLLM
from dm_agent.memoria.cierre_sesion import CierreSesionNarrativa, ErrorCierre
from dm_agent.memoria.contexto import ConstructorContextoMemoria
from dm_agent.memoria.entidades import GestorEntidadesNarrativas
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
    "/cerrar": "cierra la sesión: resumen + preparación de la próxima",
    "/debug": "activa/desactiva la traza de depuración",
    "/tool": "ejecuta una tool real sin pasar por el LLM: /tool <nombre_tool_api> <json>",
    "/combate": "estado del combate activo (sin LLM)",
    "/turno": "turno actual del combate activo (sin LLM)",
    "/reacciones": "reacciones del combate activo (sin LLM)",
    "/ficha": "ficha del personaje activo (sin LLM)",
    "/estado": "resumen compacto: ficha, combate, turno, enemigos, reacciones (sin LLM)",
}


class ErrorComandoTool(ValueError):
    """Línea de `/tool` mal formada (nombre o JSON de argumentos)."""


def parsear_comando_tool(linea: str) -> tuple[str, dict[str, Any]]:
    """Parsea el cuerpo de `/tool <nombre_tool_api> <json_argumentos>` (F6.4).

    `linea` es el texto **después** de `/tool` (puede incluir o no el espacio
    inicial). Lanza `ErrorComandoTool` con un mensaje legible si falta el
    nombre, falta el JSON, o el JSON no decodifica a un objeto."""
    texto = linea.strip()
    if not texto:
        raise ErrorComandoTool("uso: /tool <nombre_tool_api> <json_argumentos>")

    partes = texto.split(maxsplit=1)
    nombre_api = partes[0]
    json_texto = partes[1].strip() if len(partes) > 1 else ""
    if not json_texto:
        raise ErrorComandoTool(
            "faltan los argumentos JSON: /tool <nombre_tool_api> <json_argumentos>"
        )

    try:
        argumentos = json.loads(json_texto)
    except json.JSONDecodeError as e:
        raise ErrorComandoTool(f"JSON de argumentos inválido: {e}") from e
    if not isinstance(argumentos, dict):
        raise ErrorComandoTool('los argumentos deben ser un objeto JSON, p. ej. {"clave": ...}')
    return nombre_api, argumentos


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
    cierre: CierreSesionNarrativa,
    dir_sesiones: Path,
    entidades_narrativas: GestorEntidadesNarrativas,
    combate: GestorCombateNarrativo,
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
    for tool in crear_tools_sesion(cierre, dir_sesiones):
        registro.registrar(tool)
    for tool in crear_tools_entidades(entidades_narrativas):
        registro.registrar(tool)
    for tool in crear_tools_combate(combate, registro_eventos, gestor):
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
        self.entidades_narrativas = GestorEntidadesNarrativas(raiz_storage)
        self.combate = GestorCombateNarrativo(raiz_storage)
        self.resumidor = ResumidorNarrativo(self.cliente, self.memoria_narrativa)
        self.cierre = CierreSesionNarrativa(self.cliente, self.memoria_narrativa)
        self.registro = _crear_registro(
            self.gestor,
            self.registro_eventos,
            self.memoria_narrativa,
            self.resumidor,
            self.cierre,
            self.dir_sesiones,
            self.entidades_narrativas,
            self.combate,
        )
        self.system_prompt = cargar_prompt(SYSTEM_DM_MINIMO)

        # Memoria narrativa inyectable (F4.3). Campaña activa: config o "campana_demo".
        mem_cfg = self.proyecto.get("memoria", {})
        self.campaña_id = self.proyecto.get("campaña_activa", "campana_demo")
        if mem_cfg.get("inyectar_narrativa", True):
            gestor_entidades = (
                self.entidades_narrativas if mem_cfg.get("inyectar_entidades", True) else None
            )
            self.constructor_memoria: ConstructorContextoMemoria | None = (
                ConstructorContextoMemoria(
                    self.memoria_narrativa,
                    limite_entradas=int(mem_cfg.get("limite_entradas_contexto", 8)),
                    incluir_resumenes=bool(mem_cfg.get("incluir_resumenes", True)),
                    gestor_entidades=gestor_entidades,
                    limite_entidades=int(mem_cfg.get("limite_entidades_contexto", 8)),
                )
            )
        else:
            self.constructor_memoria = None

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
            constructor_memoria=self.constructor_memoria,
            campaña_id=self.campaña_id,
            gestor_combate=self.combate,
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

    def cerrar_sesion(self) -> str:
        """Cierra la sesión activa: genera resumen + preparación con el LLM."""
        if self.sesion is None:
            return "No hay sesión activa que cerrar."
        texto = self.sesion.texto_para_resumen()
        if not texto.strip():
            return "La sesión activa no tiene contenido que cerrar todavía."
        try:
            entradas = self.cierre.cerrar_sesion(self.campaña_id, self.sesion.id, texto)
        except ErrorCierre as e:
            return f"No se pudo cerrar la sesión: {e}"
        except ErrorLLM as e:
            return f"[error del modelo/endpoint] {e}"
        return (
            f"Sesión {self.sesion.id} cerrada.\n\n"
            f"== Resumen de cierre ==\n{entradas['resumen'].contenido}\n\n"
            f"== Punto de arranque de la próxima ==\n{entradas['preparacion'].contenido}"
        )

    def _dispatch_y_formatear(
        self, nombre_api: str, argumentos: dict[str, Any], *, prefijo: str = "tool"
    ) -> str:
        """Despacha una tool real (`dispatch_api`) y formatea el resultado de
        forma legible. Compartido por `/tool` (F6.4) y los comandos cómodos
        `/combate`/`/turno`/`/reacciones`/`/ficha` (F6.5-C). Registra
        `tool_call`/`tool_result` en `Sesion` para auditoría, pero **no**
        como turno `user`/`assistant`: no entra en el historial conversacional
        que `AgenteDM` reinyecta al LLM."""
        try:
            self.registro.nombre_api_a_interno(nombre_api)
        except HerramientaNoRegistrada:
            return f"[{prefijo}] {nombre_api} -> error: herramienta desconocida"

        try:
            resultado = self.registro.dispatch_api(nombre_api, ctx=None, **argumentos)
        except TypeError as e:
            return f"[{prefijo}] {nombre_api} -> error: argumentos inválidos: {e}"

        datos = resultado.datos if resultado.ok else {"error": "; ".join(resultado.errores)}
        if self.sesion is not None:
            self.sesion.registrar_tool_call(nombre_api, argumentos)
            self.sesion.registrar_tool_result(nombre_api, datos, ok=resultado.ok)
        cuerpo = json.dumps(datos, ensure_ascii=False, indent=2)
        return f"[{prefijo}] {nombre_api} -> ok={resultado.ok}\n{cuerpo}"

    def ejecutar_tool_manual(self, linea: str) -> str:
        """Comando `/tool` (F6.4): ejecuta una tool real directamente, sin
        pasar por el LLM. Depuración/recuperación manual cuando el modelo no
        emite una tool call real aunque la tool exista."""
        try:
            nombre_api, argumentos = parsear_comando_tool(linea)
        except ErrorComandoTool as e:
            return f"[tool] error: {e}"
        return self._dispatch_y_formatear(nombre_api, argumentos, prefijo="tool")

    def _combate_activo(self) -> CombateNarrativo | None:
        """Combate activo de la campaña activa, o `None` si no hay ninguno
        (F6.5-B/C): mismo origen que el contexto operativo inyectado al LLM."""
        return self.combate.cargar_activo(self.campaña_id)

    def comando_combate(self) -> str:
        """Comando `/combate` (F6.5-C): estado del combate activo, sin
        necesidad de escribir `campaña_id`/`combate_id` a mano."""
        combate = self._combate_activo()
        if combate is None:
            return "[comando] No hay combate activo detectado."
        return self._dispatch_y_formatear(
            "combate_estado",
            {"campaña_id": self.campaña_id, "combate_id": combate.id},
            prefijo="comando",
        )

    def comando_turno(self) -> str:
        """Comando `/turno` (F6.5-C): turno actual del combate activo."""
        combate = self._combate_activo()
        if combate is None:
            return "[comando] No hay combate activo detectado."
        return self._dispatch_y_formatear(
            "combate_turno_actual",
            {"campaña_id": self.campaña_id, "combate_id": combate.id},
            prefijo="comando",
        )

    def comando_reacciones(self) -> str:
        """Comando `/reacciones` (F6.5-C): reacciones del combate activo."""
        combate = self._combate_activo()
        if combate is None:
            return "[comando] No hay combate activo detectado."
        return self._dispatch_y_formatear(
            "combate_listar_reacciones",
            {"campaña_id": self.campaña_id, "combate_id": combate.id},
            prefijo="comando",
        )

    def comando_ficha(self) -> str:
        """Comando `/ficha` (F6.5-C): ficha del personaje activo. Sin un
        mecanismo formal de "personaje activo", se usa el `personaje_id` del
        combate activo (igual que el contexto operativo de F6.5-B)."""
        combate = self._combate_activo()
        personaje_id = combate.personaje_id if combate is not None else None
        if not personaje_id:
            return "[comando] No se conoce personaje activo. Usa /tool ficha_leer {...}"
        return self._dispatch_y_formatear(
            "ficha_leer",
            {"campaña_id": self.campaña_id, "personaje_id": personaje_id},
            prefijo="comando",
        )

    def comando_estado(self) -> str:
        """Comando `/estado` (F6.5-C): resumen compacto y legible (no JSON
        bruto) combinando ficha, combate, turno, enemigos y reacciones
        pendientes. No llama al LLM."""
        combate = self._combate_activo()
        lineas = [f"Campaña: {self.campaña_id}"]

        personaje_id = combate.personaje_id if combate is not None else None
        if personaje_id:
            try:
                resultado = self.registro.dispatch_api(
                    "ficha_leer", ctx=None, campaña_id=self.campaña_id, personaje_id=personaje_id
                )
            except HerramientaNoRegistrada:
                lineas.append(f"Personaje: {personaje_id} (tool ficha_leer no disponible)")
            else:
                if resultado.ok:
                    ficha = resultado.datos.get("ficha", {})
                    nombre = ficha.get("nombre", personaje_id)
                    lineas.append(
                        f"Personaje: {nombre} ({personaje_id}) — "
                        f"HP {ficha.get('hp_actual', '?')}/{ficha.get('hp_max', '?')}, "
                        f"CA {ficha.get('ca', '?')}"
                    )
                else:
                    lineas.append(f"Personaje: {personaje_id} (no se pudo leer la ficha)")
        else:
            lineas.append("Personaje: desconocido")

        if combate is None:
            lineas.append("Combate: sin combate activo detectado")
            return "[estado]\n" + "\n".join(lineas)

        lineas.append(f"Combate: {combate.id} — {combate.estado}")
        lineas.append(f"Ronda: {combate.ronda}")
        if combate.enemigos:
            lineas.append("Enemigos:")
            for enemigo in combate.enemigos:
                lineas.append(
                    f"- {enemigo.id}: {enemigo.estado}, {enemigo.hp_actual}/{enemigo.hp_max} HP"
                )
        pendientes = sum(1 for p in combate.propuestas_reaccion if p.estado == "pendiente")
        lineas.append(f"Reacciones pendientes: {pendientes}")
        return "[estado]\n" + "\n".join(lineas)


def repl(
    ctx: Any,
    *,
    leer: Callable[[str], str] | None = None,
    escribir: Callable[[str], None] | None = None,
) -> int:
    """Bucle REPL. `ctx` debe exponer procesar/info_sesion/guardar/
    nueva_sesion/alternar_debug/ejecutar_tool_manual/comando_combate/
    comando_turno/comando_reacciones/comando_ficha/comando_estado (ver
    `SesionInteractiva`).

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

        # F6.4.1: strip() (no solo lstrip()) antes de comparar contra comandos,
        # para que espacios iniciales/finales accidentales (p. ej. " /tool ...")
        # no hagan que la línea se trate como texto narrativo para el LLM.
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
        if texto == "/cerrar":
            escribir(ctx.cerrar_sesion())
            continue
        if texto == "/debug":
            escribir(ctx.alternar_debug())
            continue
        if texto == "/tool" or texto.startswith("/tool "):
            escribir(ctx.ejecutar_tool_manual(texto[len("/tool") :]))
            continue
        if texto == "/combate":
            escribir(ctx.comando_combate())
            continue
        if texto == "/turno":
            escribir(ctx.comando_turno())
            continue
        if texto == "/reacciones":
            escribir(ctx.comando_reacciones())
            continue
        if texto == "/ficha":
            escribir(ctx.comando_ficha())
            continue
        if texto == "/estado":
            escribir(ctx.comando_estado())
            continue
        if texto.startswith("/"):
            escribir(f"Comando desconocido: {texto}. Usa /ayuda.")
            continue

        try:
            escribir(ctx.procesar(texto))
        except ErrorLLM as e:
            escribir(f"[error del modelo/endpoint] {e}")
