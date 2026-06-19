"""Agent loop mínimo del Director de Juego (F2.2).

Flujo de un turno:

    usuario → registra en sesión → construye messages (system + historial)
    → ClienteLLM.chat(tools=[dados_tirar])
      - si hay content normal: lo devuelve y lo persiste
      - si hay tool_calls: ejecuta cada una con RegistroHerramientas.dispatch_api,
        persiste call+result, reinyecta resultados y vuelve a llamar al LLM
    → protegido por max_iter_turno para no bucle-infinito

Alcance F2.2: NO hay estado mecánico (ficha, combate, inventario, mundo). La
única tool ejecutable es `dados.tirar` (nombre API `dados_tirar`). Una tool
desconocida produce un resultado de error controlado que se reinyecta al modelo.
"""

from __future__ import annotations

import json
from typing import Any

from dm_agent.herramientas.registro import HerramientaNoRegistrada, RegistroHerramientas
from dm_agent.llm.cliente import ClienteLLM, ToolCall
from dm_agent.memoria.contexto import ConstructorContextoMemoria
from dm_agent.persistencia.sesion import Sesion


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

    # -- Turno completo --------------------------------------------------------

    def responder(self, entrada_usuario: str) -> str:
        self.sesion.registrar_usuario(entrada_usuario)
        messages = self._messages_base()
        tools = self.registro.esquemas_disponibles(ctx=None) or None

        for _ in range(self.max_iter_turno):
            resp = self.cliente.chat(messages, tools=tools)

            if not resp.tiene_tool_calls:
                content = resp.content or ""
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
                self.sesion.registrar_tool_call(tc.nombre_api, tc.argumentos)
                resultado, ok = self._ejecutar_tool_call(tc)
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
