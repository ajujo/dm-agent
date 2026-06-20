"""F6.1: disciplina de uso de tools (prompt + detector + reintento). Sin red.

Cubre: el prompt del DM prohíbe tool calls simuladas en texto y exige tools
reales para cambios de estado mecánico; el detector de tool calls simuladas
(`_contiene_tool_call_simulada`) distingue una llamada falsa de JSON narrativo
normal; el agent loop reintenta como máximo una vez por turno cuando detecta
una tool call simulada, sin parsearla ni ejecutarla.
"""

from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.llm.cliente import RespuestaLLM
from dm_agent.nucleo.agente import AgenteDM, _contiene_tool_call_simulada
from dm_agent.persistencia.sesion import Sesion
from dm_agent.prompts import SYSTEM_DM_MINIMO, cargar_prompt

_PROMPT = cargar_prompt(SYSTEM_DM_MINIMO).lower()


class FakeClienteSecuencia:
    """Devuelve una RespuestaLLM distinta por cada llamada, en orden."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def chat(self, messages, **kwargs):
        self.llamadas.append([dict(m) for m in messages])
        return self.respuestas.pop(0)


def _resp(content):
    return RespuestaLLM(content=content)


# --- Parte F.1-3: el prompt prohíbe tool calls simuladas / exige tools reales --------------


def test_prompt_prohibe_tool_calls_simuladas():
    assert "prohibido" in _PROMPT
    assert "tool" in _PROMPT and "herramienta" in _PROMPT
    assert '"name"' in _PROMPT and '"arguments"' in _PROMPT


def test_prompt_exige_tool_real_para_cambios_mecanicos():
    assert "requieren tool real" in _PROMPT or "tool real" in _PROMPT
    for palabra in ["ficha", "hp", "inventario", "combate", "iniciativa", "turno"]:
        assert palabra in _PROMPT


def test_prompt_prohibe_afirmar_acciones_sin_tool_real():
    assert "no digas que has" in _PROMPT
    for verbo in ["leído", "guardado", "tirado", "atacado", "dañado", "cerrado"]:
        assert verbo in _PROMPT
    assert "no simules" in _PROMPT


def test_prompt_incluye_campaña_por_defecto_y_no_duplicar_combate():
    assert "campaña activa" in _PROMPT
    assert "no inventes" in _PROMPT
    assert "combate_estado" in _PROMPT
    assert "no inicies otro combate" in _PROMPT


# --- Parte F.4-5: el detector reconoce tool calls simuladas, no JSON narrativo normal -------


def test_detecta_tool_call_simulada_en_lista():
    texto = '[{"name": "ficha_leer", "arguments": {"campaña_id": "campana_demo"}}]'
    assert _contiene_tool_call_simulada(texto)


def test_detecta_tool_call_simulada_en_bloque_multilinea():
    texto = (
        "Voy a usar la tool:\n"
        "{\n"
        '  "name": "combate_iniciar",\n'
        '  "arguments": {"campaña_id": "campana_demo"}\n'
        "}\n"
    )
    assert _contiene_tool_call_simulada(texto)


def test_no_marca_json_narrativo_normal():
    casos = [
        "Tyr entra en la taberna y pide una cerveza.",
        '{"escena": "sotano", "enemigos": 2}',
        "El personaje se llama Tyr; tiene un arguments de pelea complicado con el tabernero.",
    ]
    for texto in casos:
        assert not _contiene_tool_call_simulada(texto), texto


# --- Parte F.6: el reintento automático ocurre como máximo una vez por turno ---------------


def test_reintenta_una_vez_y_luego_devuelve_respuesta_real(tmp_path):
    simulada = '[{"name": "ficha_leer", "arguments": {"personaje_id": "pj_tyr"}}]'
    cliente = FakeClienteSecuencia([_resp(simulada), _resp("Tyr abre la puerta del sótano.")])
    sesion = Sesion.crear(tmp_path / "sesiones", id="sesion-tool-disc-1")
    agente = AgenteDM(
        cliente, RegistroHerramientas(), sesion, system_prompt="SYSTEM-BASE-DM",
    )

    salida = agente.responder("Lee la ficha de Tyr.")

    assert salida == "Tyr abre la puerta del sótano."
    assert len(cliente.llamadas) == 2
    # el mensaje correctivo se inyectó como turno intermedio antes del segundo chat().
    segunda_llamada = cliente.llamadas[1]
    assert any(
        m["role"] == "user" and "prohibido" in m["content"].lower() for m in segunda_llamada
    )


def test_no_reintenta_mas_de_una_vez_por_turno(tmp_path):
    simulada_1 = '[{"name": "ficha_leer", "arguments": {}}]'
    simulada_2 = '[{"name": "combate_iniciar", "arguments": {}}]'
    cliente = FakeClienteSecuencia([_resp(simulada_1), _resp(simulada_2)])
    sesion = Sesion.crear(tmp_path / "sesiones", id="sesion-tool-disc-2")
    agente = AgenteDM(
        cliente, RegistroHerramientas(), sesion, system_prompt="SYSTEM-BASE-DM",
    )

    salida = agente.responder("Lee la ficha de Tyr.")

    # tras un único reintento, si sigue mal, se devuelve tal cual (no hay tercera llamada).
    assert salida == simulada_2
    assert len(cliente.llamadas) == 2


def test_respuesta_limpia_no_dispara_reintento(tmp_path):
    cliente = FakeClienteSecuencia([_resp("Tyr entra en la taberna bajo la lluvia.")])
    sesion = Sesion.crear(tmp_path / "sesiones", id="sesion-tool-disc-3")
    agente = AgenteDM(
        cliente, RegistroHerramientas(), sesion, system_prompt="SYSTEM-BASE-DM",
    )

    salida = agente.responder("Describe la escena.")

    assert salida == "Tyr entra en la taberna bajo la lluvia."
    assert len(cliente.llamadas) == 1
