"""F6.3: robustez del agent loop contra tool calls duplicadas, respuestas
vacías y tools explícitas no ejecutadas. Sin red ni LLM real.

Cubre:
- (A) la misma tool con los mismos argumentos no se ejecuta dos veces en el
  mismo turno; argumentos distintos sí se ejecutan ambos; el mismo par
  tool+argumentos en turnos distintos también se ejecuta de nuevo.
- (B) una respuesta sin texto útil y sin tool calls produce un mensaje
  seguro en vez de un turno vacío.
- (C) si el usuario pide explícitamente una tool expuesta por su nombre API
  y el modelo no la llama de verdad, hay un reintento corrector único; si
  sigue sin llamarla, se informa de que no se pudo ejecutar (sin afirmar lo
  contrario).
- Ninguno de estos casos parsea ni ejecuta JSON/XML simulado: la prioridad
  de F6.1/F6.1.1 sobre pseudo-calls se mantiene intacta.
"""

from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.llm.cliente import RespuestaLLM, ToolCall
from dm_agent.nucleo.agente import _MENSAJE_RESPUESTA_VACIA, AgenteDM
from dm_agent.persistencia.sesion import Sesion


class _ToolContador:
    """Tool real mínima que cuenta cuántas veces se ejecuta de verdad."""

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.descripcion = f"tool de prueba: {nombre}"
        self.schema = {"type": "object", "properties": {}, "additionalProperties": False}
        self.requiere: list[str] = []
        self.modifica: list[str] = []
        self.contador = 0

    def disponible(self, ctx):
        return True, ""

    def ejecutar(self, ctx, **args):
        self.contador += 1
        return ResultadoHerramienta(ok=True, datos={"llamada_numero": self.contador})


class _ClienteSecuencia:
    """Devuelve una RespuestaLLM distinta por cada llamada, en orden."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def chat(self, messages, **kwargs):
        self.llamadas.append([dict(m) for m in messages])
        return self.respuestas.pop(0)


def _resp(content=None, tool_calls=None):
    return RespuestaLLM(content=content, tool_calls=tool_calls or [])


def _tc(id_, nombre_api, argumentos):
    return ToolCall(id=id_, nombre_api=nombre_api, argumentos=argumentos, argumentos_json="{}")


def _registro(*nombres_internos):
    registro = RegistroHerramientas()
    tools = {}
    for nombre in nombres_internos:
        tool = _ToolContador(nombre)
        registro.registrar(tool)
        tools[nombre] = tool
    return registro, tools


# --- Parte A: deduplicación de tool calls idénticas dentro de un turno -----


def test_tool_duplicada_idéntica_en_el_mismo_turno_se_ejecuta_una_vez(tmp_path):
    registro, tools = _registro("combate.proponer_reaccion")
    args = {"campaña_id": "campana_tyr", "enemigo_id": "rata_1"}
    cliente = _ClienteSecuencia(
        [
            _resp(tool_calls=[_tc("call-1", "combate_proponer_reaccion", args)]),
            _resp(tool_calls=[_tc("call-2", "combate_proponer_reaccion", args)]),
            _resp(content="Reacción propuesta."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s1")
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM")

    salida = agente.responder("Propón una reacción para rata_1.")

    assert salida == "Reacción propuesta."
    assert tools["combate.proponer_reaccion"].contador == 1


def test_tool_calls_con_argumentos_distintos_se_ejecutan_ambas(tmp_path):
    registro, tools = _registro("combate.proponer_reaccion")
    cliente = _ClienteSecuencia(
        [
            _resp(
                tool_calls=[
                    _tc("call-1", "combate_proponer_reaccion", {"enemigo_id": "rata_1"})
                ]
            ),
            _resp(
                tool_calls=[
                    _tc("call-2", "combate_proponer_reaccion", {"enemigo_id": "rata_2"})
                ]
            ),
            _resp(content="Dos reacciones propuestas."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s2")
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM")

    salida = agente.responder("Propón reacciones para rata_1 y rata_2.")

    assert salida == "Dos reacciones propuestas."
    assert tools["combate.proponer_reaccion"].contador == 2


def test_misma_tool_y_argumentos_en_turnos_distintos_se_puede_ejecutar(tmp_path):
    registro, tools = _registro("combate.proponer_reaccion")
    args = {"enemigo_id": "rata_1"}
    cliente = _ClienteSecuencia(
        [
            _resp(tool_calls=[_tc("call-1", "combate_proponer_reaccion", args)]),
            _resp(content="Reacción propuesta (turno 1)."),
            _resp(tool_calls=[_tc("call-2", "combate_proponer_reaccion", args)]),
            _resp(content="Reacción propuesta (turno 2)."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s3")
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM")

    salida1 = agente.responder("Propón una reacción para rata_1.")
    salida2 = agente.responder("Propón otra vez una reacción para rata_1.")

    assert salida1 == "Reacción propuesta (turno 1)."
    assert salida2 == "Reacción propuesta (turno 2)."
    assert tools["combate.proponer_reaccion"].contador == 2


def test_debug_informa_tool_duplicada_ignorada(tmp_path, capsys):
    registro, _tools = _registro("combate.proponer_reaccion")
    args = {"enemigo_id": "rata_1"}
    cliente = _ClienteSecuencia(
        [
            _resp(tool_calls=[_tc("call-1", "combate_proponer_reaccion", args)]),
            _resp(tool_calls=[_tc("call-2", "combate_proponer_reaccion", args)]),
            _resp(content="Reacción propuesta."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s4")
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM", debug=True)

    agente.responder("Propón una reacción para rata_1.")

    salida = capsys.readouterr().out
    assert "[debug] tool duplicada ignorada: combate_proponer_reaccion" in salida


# --- Parte B: respuesta vacía sin tool calls --------------------------------


def test_respuesta_vacia_sin_tools_produce_mensaje_seguro(tmp_path):
    cliente = _ClienteSecuencia([_resp(content="")])
    sesion = Sesion.crear(tmp_path / "sesiones", id="s5")
    agente = AgenteDM(cliente, RegistroHerramientas(), sesion, system_prompt="SYSTEM-BASE-DM")

    salida = agente.responder("Continúa la escena.")

    assert salida == _MENSAJE_RESPUESTA_VACIA
    assert len(cliente.llamadas) == 1


def test_debug_informa_respuesta_vacia(tmp_path, capsys):
    cliente = _ClienteSecuencia([_resp(content=None)])
    sesion = Sesion.crear(tmp_path / "sesiones", id="s6")
    agente = AgenteDM(
        cliente, RegistroHerramientas(), sesion, system_prompt="SYSTEM-BASE-DM", debug=True
    )

    agente.responder("Continúa la escena.")

    salida = capsys.readouterr().out
    assert "[debug] respuesta vacía del modelo sin tool calls" in salida


# --- Parte C: tool explícita mencionada pero no ejecutada -------------------


def test_mensaje_con_tool_explicita_no_ejecutada_activa_reintento(tmp_path):
    registro, tools = _registro("combate.resolver_reaccion")
    cliente = _ClienteSecuencia(
        [
            _resp(content=""),  # F6.3: ni texto ni tool call, mismo patrón del fallo real.
            _resp(
                tool_calls=[
                    _tc(
                        "call-1",
                        "combate_resolver_reaccion",
                        {"reaccion_id": "reaccion_f8b95457", "decision": "confirmar"},
                    )
                ]
            ),
            _resp(content="Reacción confirmada."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s7")
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM")

    salida = agente.responder(
        "Usa combate_resolver_reaccion para confirmar reaccion_f8b95457. "
        "Decision: confirmar."
    )

    assert salida == "Reacción confirmada."
    assert tools["combate.resolver_reaccion"].contador == 1
    assert len(cliente.llamadas) == 3
    # El reintento se envió como turno user sintético antes de la 2ª llamada.
    segunda_llamada = cliente.llamadas[1]
    assert any(
        m["role"] == "user" and "combate_resolver_reaccion" in m["content"]
        for m in segunda_llamada
    )


def test_reintento_tool_explicita_incluye_contexto_operativo_activo(tmp_path):
    """F6.5-B: el reprompt de tool explícita no ejecutada debe incluir los
    IDs reales activos (campaña/combate), no solo el nombre de la tool."""
    from dm_agent.esquemas.combate import CombateNarrativo
    from dm_agent.estado.combate import GestorCombateNarrativo

    registro, _tools = _registro("combate.resolver_reaccion")
    gestor_combate = GestorCombateNarrativo(tmp_path / "storage")
    combate = CombateNarrativo(id="combate_aa6049b2", campaña_id="campana_tyr", personaje_id="tyr")
    gestor_combate.guardar(combate)
    gestor_combate.marcar_activo(combate)

    cliente = _ClienteSecuencia(
        [
            _resp(content=""),
            _resp(content="Vale, lo confirmo."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s7b")
    agente = AgenteDM(
        cliente,
        registro,
        sesion,
        system_prompt="SYSTEM-BASE-DM",
        campaña_id="campana_tyr",
        gestor_combate=gestor_combate,
    )

    agente.responder("Usa combate_resolver_reaccion para confirmar reaccion_f8b95457.")

    segunda_llamada = cliente.llamadas[1]
    # El reintento es el último turno `user` sintético añadido (el primero es
    # la entrada original del usuario, que no menciona el combate_id).
    mensaje_reintento = [m for m in segunda_llamada if m["role"] == "user"][-1]["content"]
    assert "combate_aa6049b2" in mensaje_reintento
    assert "campana_tyr" in mensaje_reintento


def test_tool_explicita_no_ejecutada_tras_reintento_responde_mensaje_seguro(tmp_path):
    registro, tools = _registro("combate.resolver_reaccion")
    cliente = _ClienteSecuencia(
        [
            _resp(content=""),
            _resp(content="Vale, lo confirmo."),  # sigue sin llamar la tool real.
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s8")
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM")

    salida = agente.responder("Usa combate_resolver_reaccion para confirmar reaccion_f8b95457.")

    assert salida == "No se ha podido ejecutar la herramienta solicitada: combate_resolver_reaccion."
    assert tools["combate.resolver_reaccion"].contador == 0
    assert len(cliente.llamadas) == 2


def test_debug_informa_tool_explicita_no_ejecutada(tmp_path, capsys):
    registro, _tools = _registro("combate.resolver_reaccion")
    cliente = _ClienteSecuencia(
        [
            _resp(content=""),
            _resp(content="Vale, lo confirmo."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s9")
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM", debug=True)

    agente.responder("Usa combate_resolver_reaccion para confirmar reaccion_f8b95457.")

    salida = capsys.readouterr().out
    assert "[debug] tool explícita mencionada pero no ejecutada: combate_resolver_reaccion" in salida


# --- Prioridad: la detección de pseudo-calls (F6.1/F6.1.1) no se rompe -----


def test_simulada_tiene_prioridad_y_no_se_parsea_ni_ejecuta(tmp_path):
    """Si el modelo escribe una tool call simulada en vez de llamarla (y el
    usuario además la nombró explícitamente), F6.1/F6.1.1 sigue mandando: se
    detecta y reintenta como pseudo-call, nunca se parsea/ejecuta, y F6.3-C
    no sustituye esa política por un mensaje de "no se pudo ejecutar"."""
    registro, tools = _registro("combate.resolver_reaccion")
    simulada = '<tool_call>{"name": "combate_resolver_reaccion", "arguments": {}}</tool_call>'
    cliente = _ClienteSecuencia([_resp(content=simulada), _resp(content=simulada)])
    sesion = Sesion.crear(tmp_path / "sesiones", id="s10")
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM")

    salida = agente.responder("Usa combate_resolver_reaccion para confirmar reaccion_f8b95457.")

    assert salida == simulada
    assert tools["combate.resolver_reaccion"].contador == 0
    assert len(cliente.llamadas) == 2
