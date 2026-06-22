"""F6.1/F6.1.1: disciplina de uso de tools (prompt + detector + reintento). Sin red.

Cubre: el prompt del DM prohíbe tool calls simuladas en texto (JSON y
XML/pseudo-call) y exige tools reales para cambios de estado mecánico; el
detector de tool calls simuladas (`_contiene_tool_call_simulada`) distingue
una llamada falsa (JSON, `<call:name=...>`, `<call:param=...>`, `<tool_call>`)
de texto narrativo normal; el agent loop reintenta como máximo una vez por
turno cuando detecta una tool call simulada, sin parsearla ni ejecutarla.
"""

from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.llm.cliente import RespuestaLLM
from dm_agent.nucleo.agente import (
    _MENSAJE_CORRECTIVO_TOOL_SIMULADA,
    AgenteDM,
    _contiene_tool_call_simulada,
)
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


def test_prompt_incluye_ambos_ejemplos_prohibidos():
    """F6.1.1: el prompt debe mostrar tanto el ejemplo JSON como el XML."""
    assert '"name"' in _PROMPT and '"arguments"' in _PROMPT
    assert '<call:name="ficha_leer">' in _PROMPT
    assert "texto falso" in _PROMPT


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


def test_detecta_tool_call_simulada_en_xml_call_name():
    texto = (
        '<call:name="ficha_leer"><call:param="campaña_id">campana_tyr'
        '</call:param><call:param="personaje_id">tyr</call:param></call:>'
    )
    assert _contiene_tool_call_simulada(texto)


def test_detecta_tool_call_simulada_en_xml_call_param():
    texto = '<call:param="campaña_id">campana_tyr</call:param>'
    assert _contiene_tool_call_simulada(texto)


def test_detecta_tool_call_simulada_en_tool_call_tag():
    texto = '<tool_call>{"name": "ficha_leer"}</tool_call>'
    assert _contiene_tool_call_simulada(texto)


def test_detecta_pseudo_call_estilo_funcion():
    """F6.5.2a: combate_atacar(campaña_id="campana_demo", personaje_id="tyr")"""
    texto = 'combate_atacar(campaña_id="campana_demo", personaje_id="tyr")'
    assert _contiene_tool_call_simulada(texto)


def test_detecta_pseudo_call_estilo_funcion_combate_atacar_enemigo():
    """F6.5.2a: combate_atacar_enemigo(campaña_id="campana_demo", combate_id="combate_x")"""
    texto = 'combate_atacar_enemigo(campaña_id="campana_demo", combate_id="combate_x")'
    assert _contiene_tool_call_simulada(texto)


def test_detecta_pseudo_call_estilo_funcion_ficha_leer():
    """F6.5.2a: ficha_leer(campaña_id="campana_demo", personaje_id="tyr")"""
    texto = 'ficha_leer(campaña_id="campana_demo", personaje_id="tyr")'
    assert _contiene_tool_call_simulada(texto)


def test_detecta_pseudo_call_estilo_funcion_genérico():
    """F6.5.2a: tool_name(arg="value")"""
    texto = 'tool_name(arg="value")'
    assert _contiene_tool_call_simulada(texto)


def test_detecta_pseudo_call_estilo_funcion_con_valores_no_cotados():
    """F6.5.2a: nombre_funcion(clave=valor_sin_comillas)"""
    texto = "ficha_actualizar(personaje_id=tyr, nivel=5)"
    assert _contiene_tool_call_simulada(texto)


def test_detecta_pseudo_call_estilo_funcion_con_comillas_simples():
    """F6.5.2a: nombre_funcion(clave='valor')"""
    texto = "ficha_leer(campaña_id='campana_demo', personaje_id='tyr')"
    assert _contiene_tool_call_simulada(texto)


def test_detecta_pseudo_call_estilo_funcion_envuelta_en_backticks():
    """F6.5.2a: `combate_atacar(campaña_id="campana_demo", personaje_id="tyr")`"""
    texto = '`combate_atacar(campaña_id="campana_demo", personaje_id="tyr")`'
    assert _contiene_tool_call_simulada(texto)


def test_detecta_pseudo_call_estilo_funcion_en_bloque_multilinea():
    """F6.5.2a: pseudo-call estilo función dentro de un bloque de texto más largo."""
    texto = (
        "Voy a atacar a la rata:\n"
        'combate_atacar(campaña_id="campana_demo", personaje_id="tyr", combate_id="combate_1", objetivo_id="rata_1")\n'
        "Espero el resultado."
    )
    assert _contiene_tool_call_simulada(texto)


def test_no_marca_json_narrativo_normal():
    casos = [
        "Tyr entra en la taberna y pide una cerveza.",
        '{"escena": "sotano", "enemigos": 2}',
        "El personaje se llama Tyr; tiene un arguments de pelea complicado con el tabernero.",
        "Tyr saca su herramienta favorita: una palanca de hierro.",
        # F6.5.2a: narrativa normal sin patrón clave=valor no debe disparar.
        "Tyr gira sobre sí mismo y ataca con la espada larga.",
        "El guerrero desenvaina su espada y carga contra el orco.",
        "La rata huye por el pasillo oscuro.",
        "Tyr usa su habilidad de concentración para mantener el hechizo.",
    ]
    for texto in casos:
        assert not _contiene_tool_call_simulada(texto), texto


def test_mensaje_correctivo_prohibe_json_y_xml():
    """F6.1.1: el reprompt debe nombrar explícitamente ambos formatos prohibidos."""
    mensaje = _MENSAJE_CORRECTIVO_TOOL_SIMULADA.lower()
    assert "json" in mensaje
    assert '<call:name="...">' in mensaje
    assert "<tool_call>" in mensaje


def test_mensaje_correctivo_prohibe_estilo_funcion():
    """F6.5.2a: el reprompt debe mencionar llamadas estilo función."""
    mensaje = _MENSAJE_CORRECTIVO_TOOL_SIMULADA
    assert "nombre_funcion(clave=" in mensaje


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
