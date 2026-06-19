"""Tests del agent loop mínimo (`dm_agent.nucleo.agente.AgenteDM`).

El cliente LLM se sustituye por un doble que devuelve respuestas guionizadas;
no hay red ni servidor real.
"""

import json

from dm_agent.herramientas.dados import crear_tool_dados
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.llm.cliente import RespuestaLLM, ToolCall
from dm_agent.nucleo.agente import AgenteDM
from dm_agent.persistencia.sesion import Sesion

SYSTEM = "Eres un DM de prueba."


class FakeCliente:
    """Devuelve respuestas en orden; repite la última si se agotan."""

    def __init__(self, respuestas):
        self._respuestas = list(respuestas)
        self.llamadas = []

    def chat(self, messages, *, tools=None, **kwargs):
        # Snapshot superficial: el agente solo *añade* dicts, no muta los previos.
        self.llamadas.append({"messages": list(messages), "tools": tools})
        idx = min(len(self.llamadas) - 1, len(self._respuestas) - 1)
        return self._respuestas[idx]


def _registro():
    reg = RegistroHerramientas()
    reg.registrar(crear_tool_dados())
    return reg


def _tool_call(nombre_api, argumentos, cid="call_1"):
    return ToolCall(
        id=cid,
        nombre_api=nombre_api,
        argumentos=argumentos,
        argumentos_json=json.dumps(argumentos),
    )


def _agente(cliente, sesion, max_iter=8, debug=False):
    return AgenteDM(
        cliente,
        _registro(),
        sesion,
        system_prompt=SYSTEM,
        max_iter_turno=max_iter,
        debug=debug,
    )


def test_respuesta_normal(tmp_path):
    cliente = FakeCliente([RespuestaLLM(content="La puerta cruje al abrirse.")])
    sesion = Sesion.crear(tmp_path, id="n")
    agente = _agente(cliente, sesion)

    salida = agente.responder("Abro la puerta")
    assert salida == "La puerta cruje al abrirse."

    tipos = [e["tipo"] for e in sesion.historial()]
    assert tipos == ["user", "assistant"]
    # El system prompt va como primer message y el historial detrás.
    assert cliente.llamadas[0]["messages"][0] == {"role": "system", "content": SYSTEM}
    assert cliente.llamadas[0]["messages"][-1] == {"role": "user", "content": "Abro la puerta"}
    assert cliente.llamadas[0]["tools"] is not None  # se ofrece dados_tirar


def test_tool_call_dados(tmp_path):
    respuestas = [
        RespuestaLLM(
            content=None,
            tool_calls=[_tool_call("dados_tirar", {"expresion": "1d6", "semilla": 1})],
        ),
        RespuestaLLM(content="Sacas el resultado y avanzas."),
    ]
    cliente = FakeCliente(respuestas)
    sesion = Sesion.crear(tmp_path, id="tc")
    agente = _agente(cliente, sesion)

    salida = agente.responder("Tira un dado")
    assert salida == "Sacas el resultado y avanzas."

    tipos = [e["tipo"] for e in sesion.historial()]
    assert tipos == ["user", "tool_call", "tool_result", "assistant"]

    hist = sesion.historial()
    assert hist[1]["nombre_api"] == "dados_tirar"
    assert hist[2]["ok"] is True
    assert 1 <= hist[2]["resultado"]["total"] <= 6

    # La segunda llamada al LLM debe incluir el mensaje role=tool con el resultado.
    segunda = cliente.llamadas[1]["messages"]
    assert any(m.get("role") == "tool" and m.get("name") == "dados_tirar" for m in segunda)


def test_tool_call_desconocida_error_controlado(tmp_path):
    respuestas = [
        RespuestaLLM(content=None, tool_calls=[_tool_call("ficha_leer", {"id": "pj1"})]),
        RespuestaLLM(content="Sigo narrando pese al fallo."),
    ]
    cliente = FakeCliente(respuestas)
    sesion = Sesion.crear(tmp_path, id="desc")
    agente = _agente(cliente, sesion)

    salida = agente.responder("Lee mi ficha")
    assert salida == "Sigo narrando pese al fallo."

    res = [e for e in sesion.historial() if e["tipo"] == "tool_result"][0]
    assert res["ok"] is False
    assert "desconocida" in res["resultado"]["error"]


def test_max_iter_evita_bucle_infinito(tmp_path):
    # El cliente SIEMPRE pide una tool: sin protección sería bucle infinito.
    cliente = FakeCliente(
        [RespuestaLLM(content=None, tool_calls=[_tool_call("dados_tirar", {"expresion": "1d6"})])]
    )
    sesion = Sesion.crear(tmp_path, id="loop")
    agente = _agente(cliente, sesion, max_iter=3)

    salida = agente.responder("bucle")
    assert "límite" in salida
    assert len(cliente.llamadas) == 3  # exactamente max_iter llamadas, no más
