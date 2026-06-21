"""F6.5.1: el chat template de algunos modelos (confirmado con vLLM+Qwen3)
rechaza la petición entera (`ValueError: System message must be at the
beginning.`) si hay más de un mensaje `system`, aunque todos vayan al
principio. `construir_mensajes_llm` fusiona system_prompt + memoria +
contexto operativo en un único mensaje `system`, y `_messages_base` lo usa
para construir los messages reales del turno. Sin red ni LLM real.
"""

from dm_agent.esquemas.combate import CombateNarrativo
from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.llm.cliente import RespuestaLLM, ToolCall
from dm_agent.nucleo.agente import AgenteDM, construir_mensajes_llm
from dm_agent.persistencia.sesion import Sesion

CAMP = "campana_tyr"


def _assert_orden_valido(messages):
    """Ningún mensaje system puede aparecer después del primer no-system."""
    visto_no_system = False
    for m in messages:
        if m["role"] == "system":
            assert not visto_no_system, f"system fuera de orden: {messages}"
        else:
            visto_no_system = True


class _ToolContador:
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.descripcion = f"tool de prueba: {nombre}"
        self.schema = {"type": "object", "properties": {}, "additionalProperties": False}
        self.requiere: list[str] = []
        self.modifica: list[str] = []

    def disponible(self, ctx):
        return True, ""

    def ejecutar(self, ctx, **args):
        return ResultadoHerramienta(ok=True, datos={})


def _registro(*nombres_internos):
    registro = RegistroHerramientas()
    for nombre in nombres_internos:
        registro.registrar(_ToolContador(nombre))
    return registro


class _ClienteSecuencia:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def chat(self, messages, **kwargs):
        self.llamadas.append([dict(m) for m in messages])
        return self.respuestas.pop(0)


def _combate_activo(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path / "storage")
    combate = CombateNarrativo(id="combate_aa6049b2", campaña_id=CAMP, personaje_id="tyr")
    gestor.guardar(combate)
    gestor.marcar_activo(combate)
    return gestor


# -- construir_mensajes_llm directamente -------------------------------------


def test_un_unico_mensaje_system_aunque_haya_memoria_y_contexto():
    historial = [{"role": "user", "content": "hola"}]
    messages = construir_mensajes_llm(
        "SYSTEM-BASE", "MEMORIA-BLOQUE", "CONTEXTO OPERATIVO ACTUAL\n- campaña_id activa: x",
        historial,
    )
    systems = [m for m in messages if m["role"] == "system"]
    assert len(systems) == 1
    assert "SYSTEM-BASE" in systems[0]["content"]
    assert "MEMORIA-BLOQUE" in systems[0]["content"]
    assert "CONTEXTO OPERATIVO ACTUAL" in systems[0]["content"]
    _assert_orden_valido(messages)


def test_sin_memoria_ni_contexto_solo_el_system_base():
    messages = construir_mensajes_llm("SYSTEM-BASE", "", "", [])
    systems = [m for m in messages if m["role"] == "system"]
    assert len(systems) == 1
    assert systems[0]["content"] == "SYSTEM-BASE"


def test_assert_dispara_si_se_intenta_meter_system_tras_historial():
    historial = [{"role": "user", "content": "hola"}, {"role": "system", "content": "tarde"}]
    try:
        construir_mensajes_llm("SYSTEM-BASE", "", "", historial)
    except AssertionError:
        pass
    else:
        raise AssertionError("se esperaba AssertionError por system fuera de orden")


# -- A través de AgenteDM (contexto operativo real, F6.5-B) -----------------


def test_contexto_operativo_aparece_en_los_mensajes_enviados(tmp_path):
    gestor_combate = _combate_activo(tmp_path)
    cliente = _ClienteSecuencia([RespuestaLLM(content="ok")])
    sesion = Sesion.crear(tmp_path / "sesiones", id="s1")
    agente = AgenteDM(
        cliente, _registro(), sesion, system_prompt="SYSTEM-BASE-DM",
        campaña_id=CAMP, gestor_combate=gestor_combate,
    )

    agente.responder("¿Qué hago ahora?")

    msgs = cliente.llamadas[0]
    systems = [m for m in msgs if m["role"] == "system"]
    assert len(systems) == 1
    assert "CONTEXTO OPERATIVO ACTUAL" in systems[0]["content"]
    assert "combate_aa6049b2" in systems[0]["content"]


def test_todos_los_system_van_antes_del_primer_user(tmp_path):
    gestor_combate = _combate_activo(tmp_path)
    cliente = _ClienteSecuencia([RespuestaLLM(content="ok"), RespuestaLLM(content="ok2")])
    sesion = Sesion.crear(tmp_path / "sesiones", id="s2")
    agente = AgenteDM(
        cliente, _registro(), sesion, system_prompt="SYSTEM-BASE-DM",
        campaña_id=CAMP, gestor_combate=gestor_combate,
    )

    agente.responder("primer turno")
    agente.responder("segundo turno")

    for llamada in cliente.llamadas:
        _assert_orden_valido(llamada)
        idx_primer_no_system = next(
            i for i, m in enumerate(llamada) if m["role"] != "system"
        )
        assert all(m["role"] == "system" for m in llamada[:idx_primer_no_system])
        assert llamada[idx_primer_no_system]["role"] == "user"


def test_no_hay_system_despues_de_user_assistant_o_tool(tmp_path):
    gestor_combate = _combate_activo(tmp_path)
    cliente = _ClienteSecuencia(
        [
            RespuestaLLM(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c1", nombre_api="combate_resolver_reaccion",
                        argumentos={}, argumentos_json="{}",
                    )
                ],
            ),
            RespuestaLLM(content="Resuelto."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s3")
    agente = AgenteDM(
        cliente, _registro("combate.resolver_reaccion"), sesion, system_prompt="SYSTEM-BASE-DM",
        campaña_id=CAMP, gestor_combate=gestor_combate,
    )

    agente.responder("Resuelve la reacción.")

    # La segunda llamada al LLM ya incluye el assistant con tool_calls y el
    # mensaje role=tool con el resultado: ningún system puede ir después.
    segunda_llamada = cliente.llamadas[1]
    roles = [m["role"] for m in segunda_llamada]
    assert "tool" in roles
    _assert_orden_valido(segunda_llamada)


def test_reprompt_tool_explicita_no_ejecutada_respeta_el_orden(tmp_path):
    gestor_combate = _combate_activo(tmp_path)
    registro = _registro("combate.resolver_reaccion")
    cliente = _ClienteSecuencia(
        [
            RespuestaLLM(content=""),
            RespuestaLLM(content="Vale, lo confirmo."),
        ]
    )
    sesion = Sesion.crear(tmp_path / "sesiones", id="s4")
    agente = AgenteDM(
        cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM",
        campaña_id=CAMP, gestor_combate=gestor_combate,
    )

    agente.responder("Usa combate_resolver_reaccion para confirmar reaccion_f8b95457.")

    segunda_llamada = cliente.llamadas[1]
    _assert_orden_valido(segunda_llamada)
    # El reprompt (turno user sintético) incluye los IDs reales activos, no
    # como mensaje system adicional.
    mensaje_reintento = [m for m in segunda_llamada if m["role"] == "user"][-1]["content"]
    assert "combate_aa6049b2" in mensaje_reintento
    assert "campana_tyr" in mensaje_reintento
    assert all(m["role"] != "system" for m in segunda_llamada[1:])


def test_contenido_prohibe_placeholders(tmp_path):
    gestor_combate = _combate_activo(tmp_path)
    cliente = _ClienteSecuencia([RespuestaLLM(content="ok")])
    sesion = Sesion.crear(tmp_path / "sesiones", id="s5")
    agente = AgenteDM(
        cliente, _registro(), sesion, system_prompt="SYSTEM-BASE-DM",
        campaña_id=CAMP, gestor_combate=gestor_combate,
    )

    agente.responder("¿Qué hago ahora?")

    contenido_system = next(
        m["content"] for m in cliente.llamadas[0] if m["role"] == "system"
    )
    assert "campaña_actual" in contenido_system
    assert "combate_actual" in contenido_system
    assert "personaje_actual" in contenido_system
    assert "No uses placeholders" in contenido_system
