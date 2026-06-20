"""Agent loop mínimo del Director de Juego (F2.2; disciplina de tools en F6.1).

Flujo de un turno:

    usuario → registra en sesión → construye messages (system + historial)
    → ClienteLLM.chat(tools=[...])
      - si hay tool_calls: ejecuta cada una con RegistroHerramientas.dispatch_api,
        persiste call+result, reinyecta resultados y vuelve a llamar al LLM
      - si hay content normal sin tool_calls: si "parece" una tool call simulada
        en texto (F6.1), se reintenta una vez con un mensaje correctivo; si no,
        se devuelve y se persiste
    → protegido por max_iter_turno para no bucle-infinito

F6.1: algunos modelos, en vez de llamar a una tool real, escriben en el texto
un bloque tipo `[{"name": "ficha_leer", "arguments": {...}}]` que parece una
tool call pero no ejecuta nada. `_contiene_tool_call_simulada` detecta ese
patrón (sin intentar parsearlo ni ejecutarlo: sería peligroso) y dispara como
máximo un reintento corrector por turno.

F6.1.1: el mismo problema reaparece en formato XML/pseudo-call (por ejemplo
`<call:name="ficha_leer"><call:param="...">...</call:>`) o con etiquetas tipo
`<tool_call>`/`<tool>`. `_contiene_tool_call_simulada` se amplía para
reconocer también esos formatos, con la misma política: solo detectar y
avisar/reintentar, nunca parsear ni ejecutar.

F6.2: incluso con esa disciplina, modelos locales con muchas tools y schemas
complejos a la vez siguen fallando en emitir una tool call real. Antes de
cada turno, `_tools_para_turno` filtra las tools que se exponen al LLM según
la intención del mensaje (`seleccion_tools.seleccionar_tools_para_turno`):
menos tools por turno, más probabilidad de que el modelo elija una real. En
`--debug` siempre se imprime qué tools quedaron expuestas.

F6.3: tres fallos de robustez observados ya con tool calls reales (F6.2):
(a) el modelo repite la misma tool call (mismo nombre + mismos argumentos)
dos veces en el mismo turno → se ignora la repetición exacta sin volver a
ejecutar la tool; (b) el modelo termina el turno sin texto útil y sin
ninguna tool call → se devuelve un mensaje seguro en vez de un turno vacío;
(c) el usuario pide explícitamente una tool por su nombre API y el modelo no
la llama de verdad → un reintento corrector una vez, y si sigue sin
llamarla, un mensaje seguro que no afirma que se ejecutó.
"""

from __future__ import annotations

import json
import re
from typing import Any

from dm_agent.herramientas.registro import HerramientaNoRegistrada, RegistroHerramientas
from dm_agent.llm.cliente import ClienteLLM, ToolCall
from dm_agent.memoria.contexto import ConstructorContextoMemoria
from dm_agent.nucleo.seleccion_tools import seleccionar_tools_para_turno
from dm_agent.persistencia.sesion import Sesion

_PATRON_TOOL_CALL_SIMULADA = re.compile(
    r'"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:'
    r'|"arguments"\s*:\s*\{.*?\}\s*,\s*"name"\s*:\s*"[^"]+"'
    r"|<call:name\s*="
    r"|<call:param\s*="
    r"|</call:>"
    r"|<tool_call\b"
    r"|<tool>",
    re.DOTALL,
)

_MENSAJE_CORRECTIVO_TOOL_SIMULADA = (
    "Has escrito una llamada a herramienta como texto. Eso está prohibido.\n\n"
    "No escribas JSON de tool calls.\n"
    'No escribas XML/pseudo-calls como <call:name="...">.\n'
    "No escribas <tool_call> ni formatos similares.\n\n"
    "Si necesitas usar una herramienta, debes llamar a la tool real mediante el sistema "
    "de tools.\n"
    "Reintenta ahora usando una tool call real o responde que no puedes."
)


def _contiene_tool_call_simulada(texto: str) -> bool:
    """Detecta una tool call simulada como texto: JSON tipo {"name": ..., "arguments": ...}
    o XML/pseudo-call tipo <call:name="...">, <call:param="...">, </call:>, <tool_call>,
    <tool>.

    Deliberadamente no intenta parsear ni ejecutar ese contenido: solo lo
    detecta para poder avisar/reintentar. Un JSON narrativo normal (sin las
    claves "name"+"arguments" juntas, ni esas etiquetas) no debe disparar
    esto.
    """
    return bool(_PATRON_TOOL_CALL_SIMULADA.search(texto))


_MENSAJE_TOOL_EXPLICITA_NO_EJECUTADA = (
    "El usuario ha pedido explícitamente usar la herramienta {nombre}, pero no la has "
    "llamado realmente. Debes llamar esa herramienta real mediante el sistema de tools. "
    "No escribas JSON, XML ni texto explicando la llamada. Si no puedes llamarla, responde "
    "claramente que no puedes."
)

_MENSAJE_RESPUESTA_VACIA = (
    "No he recibido una respuesta útil del modelo ni se ha ejecutado ninguna herramienta. "
    "Repite la instrucción de forma más directa o usa una sola herramienta."
)


def _tool_mencionada_no_ejecutada(
    entrada_usuario: str, nombres_expuestos: list[str], nombres_ejecutados: set[str]
) -> str | None:
    """Si el usuario nombró explícitamente (por su nombre API) alguna de las
    tools expuestas en este turno y esa tool todavía no se ha ejecutado de
    verdad, devuelve su nombre. `None` si no hay ninguna tool mencionada
    pendiente."""
    texto = entrada_usuario.lower()
    for nombre in nombres_expuestos:
        if nombre in nombres_ejecutados:
            continue
        if nombre.lower() in texto:
            return nombre
    return None


class AgenteDM:
    def __init__(
        self,
        cliente: ClienteLLM,
        registro: RegistroHerramientas,
        sesion: Sesion,
        *,
        system_prompt: str,
        max_iter_turno: int = 8,
        debug: bool = False,
        constructor_memoria: ConstructorContextoMemoria | None = None,
        campaña_id: str | None = None,
    ) -> None:
        self.cliente = cliente
        self.registro = registro
        self.sesion = sesion
        self.system_prompt = system_prompt
        self.max_iter_turno = max(1, max_iter_turno)
        self.debug = debug
        # Inyección de memoria narrativa (F4.3): solo si hay constructor y campaña.
        self.constructor_memoria = constructor_memoria
        self.campaña_id = campaña_id

    # -- Construcción de messages ---------------------------------------------

    def _messages_base(self) -> list[dict[str, Any]]:
        """System prompt + historial narrativo (solo turnos user/assistant).

        Los eventos `tool_call`/`tool_result` persistidos NO se reinyectan entre
        turnos en esta versión mínima; el round-trip de tools vive solo dentro
        del turno en curso."""
        messages: list[dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        bloque_memoria = self._bloque_memoria()
        if bloque_memoria:
            # Segundo mensaje system: continuidad narrativa, sin sustituir el base.
            messages.append({"role": "system", "content": bloque_memoria})
        for ev in self.sesion.historial():
            tipo = ev.get("tipo")
            if tipo == "user":
                messages.append({"role": "user", "content": ev.get("content", "")})
            elif tipo == "assistant":
                contenido = ev.get("content")
                if contenido:
                    messages.append({"role": "assistant", "content": contenido})
        return messages

    def _bloque_memoria(self) -> str:
        """Bloque de memoria narrativa a inyectar, o "" si no procede."""
        if self.constructor_memoria is None or not self.campaña_id:
            return ""
        return self.constructor_memoria.construir_bloque_memoria(self.campaña_id)

    # -- Ejecución de una tool call -------------------------------------------

    def _ejecutar_tool_call(self, tc: ToolCall) -> tuple[dict[str, Any], bool]:
        """Devuelve (resultado, ok). Nunca lanza: una tool desconocida o un
        fallo se convierten en un resultado de error controlado."""
        try:
            self.registro.nombre_api_a_interno(tc.nombre_api)
        except HerramientaNoRegistrada:
            return ({"error": f"herramienta desconocida: {tc.nombre_api}"}, False)

        try:
            res = self.registro.dispatch_api(tc.nombre_api, ctx=None, **tc.argumentos)
        except TypeError as e:
            return ({"error": f"argumentos inválidos para {tc.nombre_api}: {e}"}, False)

        if res.ok:
            return (res.datos, True)
        return ({"error": "; ".join(res.errores) or "tool falló"}, False)

    # -- Selección contextual de tools (F6.2) -----------------------------------

    def _tools_para_turno(self, entrada_usuario: str) -> list[dict[str, Any]] | None:
        """Filtra las tools que se exponen al LLM en este turno según la
        intención del mensaje (F6.2). Si no hay intención clara, conserva el
        comportamiento anterior (todas las tools disponibles)."""
        todas = self.registro.esquemas_disponibles(ctx=None)
        nombres_relevantes = seleccionar_tools_para_turno(entrada_usuario)
        if nombres_relevantes is None:
            seleccionadas = todas
        else:
            seleccionadas = [t for t in todas if t["function"]["name"] in nombres_relevantes]
        if self.debug:
            nombres = [t["function"]["name"] for t in seleccionadas]
            print(f"[debug] tools expuestas: {', '.join(nombres) if nombres else '(ninguna)'}")
        return seleccionadas or None

    # -- Turno completo --------------------------------------------------------

    def responder(self, entrada_usuario: str) -> str:
        self.sesion.registrar_usuario(entrada_usuario)
        messages = self._messages_base()
        tools = self._tools_para_turno(entrada_usuario)
        nombres_expuestos = [t["function"]["name"] for t in (tools or [])]
        reintento_simulada_usado = False
        reintento_tool_explicita_usado = False
        # (nombre_api, argumentos_json_normalizados) ya ejecutados en este turno (F6.3-A).
        tool_calls_ejecutadas: set[tuple[str, str]] = set()
        nombres_tools_ejecutadas: set[str] = set()

        for _ in range(self.max_iter_turno):
            resp = self.cliente.chat(messages, tools=tools)

            if not resp.tiene_tool_calls:
                content = resp.content or ""
                if _contiene_tool_call_simulada(content):
                    if self.debug:
                        print(
                            "[debug] posible tool call simulada en texto; "
                            "no se ha ejecutado ninguna herramienta"
                        )
                    if not reintento_simulada_usado:
                        reintento_simulada_usado = True
                        messages.append({"role": "assistant", "content": content})
                        messages.append(
                            {"role": "user", "content": _MENSAJE_CORRECTIVO_TOOL_SIMULADA}
                        )
                        continue
                    self.sesion.registrar_asistente(content)
                    return content

                # F6.3-C: el usuario pidió explícitamente una tool expuesta y no se
                # ha ejecutado de verdad todavía → reintento corrector una vez.
                tool_pendiente = _tool_mencionada_no_ejecutada(
                    entrada_usuario, nombres_expuestos, nombres_tools_ejecutadas
                )
                if tool_pendiente is not None:
                    if not reintento_tool_explicita_usado:
                        reintento_tool_explicita_usado = True
                        if self.debug:
                            print(
                                "[debug] tool explícita mencionada pero no ejecutada: "
                                f"{tool_pendiente}"
                            )
                        messages.append({"role": "assistant", "content": content})
                        messages.append(
                            {
                                "role": "user",
                                "content": _MENSAJE_TOOL_EXPLICITA_NO_EJECUTADA.format(
                                    nombre=tool_pendiente
                                ),
                            }
                        )
                        continue
                    mensaje_final = (
                        f"No se ha podido ejecutar la herramienta solicitada: {tool_pendiente}."
                    )
                    self.sesion.registrar_asistente(mensaje_final)
                    return mensaje_final

                # F6.3-B: ni texto útil ni tool calls → mensaje seguro, no un turno vacío.
                if not content.strip():
                    if self.debug:
                        print("[debug] respuesta vacía del modelo sin tool calls")
                    self.sesion.registrar_asistente(_MENSAJE_RESPUESTA_VACIA)
                    return _MENSAJE_RESPUESTA_VACIA

                self.sesion.registrar_asistente(content)
                return content

            # Reinyecta el mensaje del asistente con sus tool_calls.
            messages.append(
                {
                    "role": "assistant",
                    "content": resp.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.nombre_api, "arguments": tc.argumentos_json},
                        }
                        for tc in resp.tool_calls
                    ],
                }
            )

            for tc in resp.tool_calls:
                clave = (tc.nombre_api, json.dumps(tc.argumentos, sort_keys=True))
                if clave in tool_calls_ejecutadas:
                    # F6.3-A: misma tool + mismos argumentos ya ejecutada en este turno.
                    if self.debug:
                        print(f"[debug] tool duplicada ignorada: {tc.nombre_api}({tc.argumentos})")
                    resultado_dup = {
                        "aviso": (
                            f"tool duplicada ignorada: {tc.nombre_api} ya se ejecutó con estos "
                            "mismos argumentos en este turno"
                        )
                    }
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.nombre_api,
                            "content": json.dumps(resultado_dup, ensure_ascii=False),
                        }
                    )
                    continue

                tool_calls_ejecutadas.add(clave)
                self.sesion.registrar_tool_call(tc.nombre_api, tc.argumentos)
                resultado, ok = self._ejecutar_tool_call(tc)
                nombres_tools_ejecutadas.add(tc.nombre_api)
                self.sesion.registrar_tool_result(tc.nombre_api, resultado, ok=ok)
                if self.debug:
                    print(f"[debug] tool {tc.nombre_api}({tc.argumentos}) -> ok={ok} {resultado}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.nombre_api,
                        "content": json.dumps(resultado, ensure_ascii=False),
                    }
                )
            # vuelve a iterar: el modelo verá los resultados de tool

        # Se alcanzó el límite de iteraciones sin respuesta final.
        aviso = (
            "[El Director se ha enredado resolviendo herramientas y ha alcanzado el "
            f"límite de {self.max_iter_turno} iteraciones en este turno. Reformula tu acción.]"
        )
        self.sesion.registrar_asistente(aviso)
        return aviso
