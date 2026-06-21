"""Tests de inyección de memoria narrativa en AgenteDM (F4.3). Mock LLM; tmp_path."""

import json

from dm_agent.esquemas.narrativa import crear_entrada
from dm_agent.herramientas.dados import crear_tool_dados
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.llm.cliente import RespuestaLLM, ToolCall
from dm_agent.memoria.contexto import ConstructorContextoMemoria
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.nucleo.agente import AgenteDM
from dm_agent.persistencia.sesion import Sesion

SYSTEM = "Eres un DM de prueba."
CAMP = "campana_demo"


class FakeCliente:
    def __init__(self, respuestas):
        self._respuestas = list(respuestas)
        self.llamadas = []

    def chat(self, messages, **kwargs):
        self.llamadas.append([dict(m) for m in messages])
        idx = min(len(self.llamadas) - 1, len(self._respuestas) - 1)
        return self._respuestas[idx]


def _registro():
    reg = RegistroHerramientas()
    reg.registrar(crear_tool_dados())
    return reg


def _agente(tmp_path, cliente, *, con_memoria, sembrar=True, campaña_id=CAMP):
    mem = GestorMemoriaNarrativa(tmp_path)
    if sembrar:
        mem.registrar_entrada(crear_entrada(CAMP, "decision", "Tyr aceptó el pacto de la bruja",
                                            titulo="El pacto"))
    sesion = Sesion.crear(tmp_path / "sesiones", id="s1")
    constructor = ConstructorContextoMemoria(mem) if con_memoria else None
    return AgenteDM(
        cliente, _registro(), sesion, system_prompt=SYSTEM,
        constructor_memoria=constructor, campaña_id=campaña_id if con_memoria else None,
    )


def test_agente_sin_memoria_funciona_como_antes(tmp_path):
    cliente = FakeCliente([RespuestaLLM(content="Narras la escena.")])
    agente = _agente(tmp_path, cliente, con_memoria=False)
    salida = agente.responder("Entro en la taberna")
    assert salida == "Narras la escena."
    msgs = cliente.llamadas[0]
    # Solo un system message (el base), sin bloque de memoria.
    systems = [m for m in msgs if m["role"] == "system"]
    assert len(systems) == 1
    assert systems[0]["content"] == SYSTEM


def test_agente_con_memoria_inyecta_bloque(tmp_path):
    cliente = FakeCliente([RespuestaLLM(content="ok")])
    agente = _agente(tmp_path, cliente, con_memoria=True)
    agente.responder("¿Qué hago ahora?")
    msgs = cliente.llamadas[0]
    # F6.5.1: un único mensaje system (algunas plantillas de chat rechazan
    # más de uno), pero el base no se sustituye: ambos bloques van fusionados.
    systems = [m for m in msgs if m["role"] == "system"]
    assert len(systems) == 1
    assert systems[0]["content"].startswith(SYSTEM)
    assert "Memoria narrativa de campaña" in systems[0]["content"]
    assert "El pacto" in systems[0]["content"]


def test_sin_memoria_no_anade_bloque_innecesario(tmp_path):
    # Constructor presente pero campaña sin entradas -> bloque vacío -> no se añade.
    cliente = FakeCliente([RespuestaLLM(content="ok")])
    agente = _agente(tmp_path, cliente, con_memoria=True, sembrar=False)
    agente.responder("hola")
    systems = [m for m in cliente.llamadas[0] if m["role"] == "system"]
    assert len(systems) == 1


def test_memoria_aparece_antes_del_mensaje_de_usuario(tmp_path):
    cliente = FakeCliente([RespuestaLLM(content="ok")])
    agente = _agente(tmp_path, cliente, con_memoria=True)
    agente.responder("acción del jugador")
    msgs = cliente.llamadas[0]
    roles = [m["role"] for m in msgs]
    # F6.5.1: la memoria vive dentro del único mensaje system fusionado.
    idx_mem = next(i for i, m in enumerate(msgs)
                   if m["role"] == "system" and "Memoria narrativa" in m["content"])
    idx_user = next(i for i, m in enumerate(msgs)
                    if m["role"] == "user" and m["content"] == "acción del jugador")
    assert idx_mem < idx_user
    assert roles[0] == "system"  # el base sigue primero
    assert roles.count("system") == 1


def test_memoria_presente_en_llamada_inicial_con_tool_call(tmp_path):
    respuestas = [
        RespuestaLLM(content=None, tool_calls=[ToolCall(
            id="c1", nombre_api="dados_tirar",
            argumentos={"expresion": "1d6", "semilla": 1}, argumentos_json="{}")]),
        RespuestaLLM(content="Resultado integrado."),
    ]
    cliente = FakeCliente(respuestas)
    agente = _agente(tmp_path, cliente, con_memoria=True)
    salida = agente.responder("tiro un dado")
    assert salida == "Resultado integrado."
    # La primera llamada (antes de la tool) ya incluye el bloque de memoria.
    systems_inicial = [m for m in cliente.llamadas[0] if m["role"] == "system"]
    assert any("Memoria narrativa" in m["content"] for m in systems_inicial)


def test_no_hace_red_ni_toca_storage_real(tmp_path):
    # Garantiza que todo cuelga de tmp_path.
    cliente = FakeCliente([RespuestaLLM(content="ok")])
    agente = _agente(tmp_path, cliente, con_memoria=True)
    agente.responder("x")
    # la sesión y la memoria están bajo tmp_path
    assert str(agente.sesion.ruta).startswith(str(tmp_path))
    # sanity: el historial es JSON válido
    for linea in agente.sesion.ruta.read_text(encoding="utf-8").splitlines():
        json.loads(linea)
