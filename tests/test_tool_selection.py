"""F6.2: selección contextual de tools por turno. Sin red ni LLM real.

Cubre `seleccionar_tools_para_turno` (coincidencia de palabras clave por
categoría: ficha, inventario, combate general, ataque, iniciativa/turno,
reacción, memoria/sesión; `None` para mensajes ambiguos) y que `AgenteDM`
aplica ese filtro a las tools que expone al LLM, mostrándolo en `--debug`.
"""

from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.llm.cliente import RespuestaLLM
from dm_agent.nucleo.agente import AgenteDM
from dm_agent.nucleo.seleccion_tools import seleccionar_tools_para_turno
from dm_agent.persistencia.sesion import Sesion

# --- Parte C.1-9: el detector de intención reconoce cada categoría ----------


def test_mensaje_ataque_selecciona_atacar_enemigo():
    sel = seleccionar_tools_para_turno("Ataca a la rata con tu espada larga.")
    assert sel is not None
    assert "combate_atacar_enemigo" in sel


def test_mensaje_ataque_selecciona_combate_estado():
    sel = seleccionar_tools_para_turno("Ataca a la rata.")
    assert sel is not None
    assert "combate_estado" in sel


def test_mensaje_ataque_no_selecciona_todas_las_tools():
    sel = seleccionar_tools_para_turno("Ataca a la rata con tu espada larga.")
    assert sel is not None
    # "espada" también dispara la categoría inventario (a propósito: el
    # mismo arma puede ser tema de inventario o solo parte de la narración
    # de un ataque), pero el registro real tiene ~45 tools en total
    # (ficha+hp_xp+inventario+narrativa+resumen+sesion+entidad+combate+
    # dados); un ataque no debe acercarse a esa cifra.
    assert len(sel) < 15


def test_mensaje_iniciativa_selecciona_tirar_iniciativa():
    sel = seleccionar_tools_para_turno("Tira iniciativa para el combate.")
    assert sel is not None
    assert "combate_tirar_iniciativa" in sel


def test_mensaje_turno_selecciona_turno_actual():
    sel = seleccionar_tools_para_turno("¿De quién es el turno ahora?")
    assert sel is not None
    assert "combate_turno_actual" in sel


def test_mensaje_reaccion_selecciona_proponer_reaccion():
    sel = seleccionar_tools_para_turno("¿La rata puede hacer un ataque de oportunidad?")
    assert sel is not None
    assert "combate_proponer_reaccion" in sel


def test_mensaje_ficha_selecciona_ficha_leer():
    sel = seleccionar_tools_para_turno("Lee la ficha de Tyr, quiero ver su HP y su CA.")
    assert sel is not None
    assert "ficha_leer" in sel


def test_mensaje_inventario_selecciona_tools_inventario():
    sel = seleccionar_tools_para_turno("Equipa la espada que tienes en el inventario.")
    assert sel is not None
    assert "inventario_equipar" in sel
    assert "inventario_listar" in sel


def test_mensaje_memoria_selecciona_narrativa_resumen_sesion():
    sel = seleccionar_tools_para_turno(
        "Recuerda lo que pasó, haz un resumen y luego cerramos sesión."
    )
    assert sel is not None
    assert sel & {"narrativa_registrar", "narrativa_reciente", "resumen_entradas", "resumen_texto"}
    assert sel & {"sesion_cerrar", "sesion_cerrar_texto"}


def test_mensaje_ambiguo_devuelve_none_fallback():
    """Sin intención clara, se devuelve None: el llamador debe interpretarlo
    como "ofrecer todas las tools" (comportamiento anterior a F6.2)."""
    sel = seleccionar_tools_para_turno("Hola, ¿qué tal el día?")
    assert sel is None


def test_funciona_sin_acentos_en_el_mensaje():
    """El usuario (o el modelo, al repetir su propio texto) puede escribir
    sin tildes; la detección no debe depender de que estén bien escritas."""
    sel = seleccionar_tools_para_turno("Quiero confirmar la reaccion de la rata.")
    assert sel is not None
    assert "combate_resolver_reaccion" in sel or "combate_proponer_reaccion" in sel


# --- Parte combate específico no cae al fallback general --------------------


def test_ataque_no_incluye_todo_el_conjunto_de_combate_general():
    from dm_agent.nucleo.seleccion_tools import TOOLS_COMBATE_GENERAL

    sel = seleccionar_tools_para_turno("Ataca a la rata.")
    assert sel is not None
    assert sel != TOOLS_COMBATE_GENERAL
    assert not TOOLS_COMBATE_GENERAL.issubset(sel)


# --- Integración con AgenteDM: filtra tools reales y lo muestra en debug ----


class _ToolFake:
    """Herramienta mínima registrable, sin lógica real (solo para probar
    que `AgenteDM` filtra los esquemas que expone, no qué hacen)."""

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.descripcion = f"tool de prueba: {nombre}"
        self.schema = {"type": "object", "properties": {}, "additionalProperties": False}
        self.requiere: list[str] = []
        self.modifica: list[str] = []

    def disponible(self, ctx):
        return True, ""

    def ejecutar(self, ctx, **args):
        return ResultadoHerramienta(ok=True)


def _registro_combate_y_ficha() -> RegistroHerramientas:
    registro = RegistroHerramientas()
    for nombre in [
        "ficha.leer",
        "ficha.guardar",
        "inventario.listar",
        "inventario.equipar",
        "combate.estado",
        "combate.atacar_enemigo",
        "combate.tirar_iniciativa",
        "narrativa.registrar",
    ]:
        registro.registrar(_ToolFake(nombre))
    return registro


class _ClienteCapturaTools:
    """Devuelve una respuesta fija y memoriza qué `tools` recibió cada chat()."""

    def __init__(self, respuesta: RespuestaLLM) -> None:
        self.respuesta = respuesta
        self.tools_recibidas: list[list[dict] | None] = []

    def chat(self, messages, tools=None, **kwargs):
        self.tools_recibidas.append(tools)
        return self.respuesta


def test_agente_filtra_tools_reales_para_mensaje_de_ataque(tmp_path):
    cliente = _ClienteCapturaTools(RespuestaLLM(content="Tyr golpea a la rata."))
    sesion = Sesion.crear(tmp_path / "sesiones", id="sesion-tool-sel-1")
    agente = AgenteDM(
        cliente, _registro_combate_y_ficha(), sesion, system_prompt="SYSTEM-BASE-DM"
    )

    agente.responder("Ataca a la rata.")

    assert len(cliente.tools_recibidas) == 1
    nombres = {t["function"]["name"] for t in cliente.tools_recibidas[0]}
    assert "combate_atacar_enemigo" in nombres
    assert "combate_estado" in nombres
    # No se exponen tools de ficha/inventario/narrativa ajenas al ataque.
    assert "narrativa_registrar" not in nombres
    assert "inventario_listar" not in nombres


def test_agente_imprime_tools_expuestas_en_debug(tmp_path, capsys):
    cliente = _ClienteCapturaTools(RespuestaLLM(content="Tyr golpea a la rata."))
    sesion = Sesion.crear(tmp_path / "sesiones", id="sesion-tool-sel-2")
    agente = AgenteDM(
        cliente,
        _registro_combate_y_ficha(),
        sesion,
        system_prompt="SYSTEM-BASE-DM",
        debug=True,
    )

    agente.responder("Ataca a la rata.")

    salida = capsys.readouterr().out
    assert "[debug] tools expuestas:" in salida
    assert "combate_atacar_enemigo" in salida


def test_agente_mensaje_ambiguo_expone_todas_las_tools_registradas(tmp_path):
    cliente = _ClienteCapturaTools(RespuestaLLM(content="Hola, buenos días."))
    sesion = Sesion.crear(tmp_path / "sesiones", id="sesion-tool-sel-3")
    registro = _registro_combate_y_ficha()
    agente = AgenteDM(cliente, registro, sesion, system_prompt="SYSTEM-BASE-DM")

    agente.responder("Hola, ¿qué tal el día?")

    nombres = {t["function"]["name"] for t in cliente.tools_recibidas[0]}
    assert len(nombres) == len(registro)
