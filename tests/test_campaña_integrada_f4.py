"""F4.5: prueba integrada de campaña persistente básica (extremo a extremo).

Mock del cliente LLM; todo bajo tmp_path; sin red. Cubre el flujo:
ficha → escena → tools mecánicas → cierre de sesión → continuar con memoria
inyectada en el siguiente turno.
"""

from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.ficha import crear_tools_ficha
from dm_agent.herramientas.hp_xp import crear_tools_hp_xp
from dm_agent.herramientas.inventario import crear_tools_inventario
from dm_agent.herramientas.narrativa import crear_tools_narrativa
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.llm.cliente import RespuestaLLM
from dm_agent.memoria.cierre_sesion import CierreSesionNarrativa
from dm_agent.memoria.contexto import ConstructorContextoMemoria
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.nucleo.agente import AgenteDM
from dm_agent.persistencia.sesion import Sesion

CAMP = "campana_demo"
PJ = "pj_tyr"
SES = "sesion-int-001"

_CIERRE = """# Resumen de cierre

Tyr entró en la taberna bajo la lluvia, encontró una llave oxidada y terminó herido tras un breve altercado.

# Preparación de próxima sesión

La próxima sesión empieza con Tyr sentado junto al fuego, observando la llave oxidada mientras escucha pasos en la escalera."""


class FakeClienteFijo:
    """Devuelve siempre el mismo contenido y captura los messages."""

    def __init__(self, contenido):
        self.contenido = contenido
        self.llamadas = []

    def chat(self, messages, **kwargs):
        self.llamadas.append([dict(m) for m in messages])
        return RespuestaLLM(content=self.contenido)


def _ficha_inicial():
    return {
        "id": PJ, "nombre": "Tyr", "clase": "Guerrero", "nivel": 1,
        "raza": "Humano", "trasfondo": "Soldado",
        "atributos": {"fuerza": 15, "destreza": 12, "constitucion": 14,
                      "inteligencia": 10, "sabiduria": 11, "carisma": 9},
        "hp_max": 12, "hp_actual": 12, "ca": 15, "bonificador_competencia": 2, "xp": 0,
        "inventario": [],
    }


def _registro_mecanico(gestor, eventos, memoria):
    reg = RegistroHerramientas()
    for tool in crear_tools_ficha(gestor):
        reg.registrar(tool)
    for tool in crear_tools_hp_xp(gestor, eventos):
        reg.registrar(tool)
    for tool in crear_tools_inventario(gestor, eventos):
        reg.registrar(tool)
    for tool in crear_tools_narrativa(memoria):
        reg.registrar(tool)
    return reg


def test_campaña_persistente_basica_extremo_a_extremo(tmp_path):
    storage = tmp_path / "storage"
    gestor = GestorEstado(storage)
    eventos = RegistroEventosEstado(storage)
    memoria = GestorMemoriaNarrativa(storage)
    reg = _registro_mecanico(gestor, eventos, memoria)

    # 1-2. Campaña + ficha inicial.
    res = reg.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_inicial())
    assert res.ok
    assert gestor.existe_campaña(CAMP)

    # 3. Entrada narrativa inicial (escena).
    res = reg.dispatch(
        "narrativa.registrar", ctx=None, campaña_id=CAMP, sesion_id=SES, tipo="escena",
        titulo="Llegada a la taberna",
        contenido="Tyr entra en una taberna bajo la lluvia.", origen="agente",
    )
    assert res.ok

    # 4. Mutaciones mecánicas: añadir objeto + aplicar daño.
    res = reg.dispatch(
        "inventario.añadir", ctx=None, campaña_id=CAMP, personaje_id=PJ,
        objeto={"id": "obj_llave_oxidada", "nombre": "Llave oxidada", "cantidad": 1},
    )
    assert res.ok
    res = reg.dispatch(
        "hp_xp.aplicar_daño", ctx=None, campaña_id=CAMP, personaje_id=PJ,
        cantidad=3, motivo="trampa sencilla",
    )
    assert res.ok and res.datos["hp_despues"] == 9

    # 5. Comprobaciones: ficha actualizada, evento mecánico, entrada narrativa.
    ficha = gestor.cargar_ficha(CAMP, PJ)
    assert ficha.hp_actual == 9
    assert [o.id for o in ficha.inventario] == ["obj_llave_oxidada"]
    tipos_evento = [e.tipo for e in eventos.listar(CAMP)]
    assert "objeto_añadido" in tipos_evento and "daño_aplicado" in tipos_evento
    assert any(e.tipo == "escena" for e in memoria.listar_entradas(CAMP))

    # 6-7. Cierre de sesión con fake LLM -> dos entradas (resumen + siguiente_sesion).
    cierre = CierreSesionNarrativa(FakeClienteFijo(_CIERRE), memoria)
    entradas = cierre.cerrar_sesion(CAMP, SES, "Transcripción de la sesión jugada.")
    assert entradas["resumen"].tipo == "resumen"
    assert entradas["preparacion"].tipo == "siguiente_sesion"
    assert entradas["resumen"].campaña_id == entradas["preparacion"].campaña_id == CAMP
    assert entradas["resumen"].sesion_id == entradas["preparacion"].sesion_id == SES

    # 8-10. Continuar: agente con memoria inyectada y un turno nuevo.
    constructor = ConstructorContextoMemoria(memoria)
    cliente_agente = FakeClienteFijo("Tyr recuerda la llave y los pasos en la escalera.")
    sesion2 = Sesion.crear(storage / "sesiones", id="sesion-int-002")
    agente = AgenteDM(
        cliente_agente, reg, sesion2, system_prompt="SYSTEM-BASE-DM",
        constructor_memoria=constructor, campaña_id=CAMP,
    )
    salida = agente.responder("Continúa desde donde lo dejamos. ¿Qué recuerda Tyr?")
    assert salida

    # 11-12. Los messages incluyen base + memoria (resumen + preparación) antes del usuario.
    msgs = cliente_agente.llamadas[0]
    systems = [m for m in msgs if m["role"] == "system"]
    assert systems[0]["content"] == "SYSTEM-BASE-DM"  # base no sustituido
    bloque = next(m["content"] for m in systems if "Memoria narrativa de campaña" in m["content"])
    assert "encontró una llave oxidada" in bloque          # resumen de cierre
    assert "junto al fuego" in bloque                       # preparación próxima sesión
    idx_mem = next(i for i, m in enumerate(msgs)
                   if m["role"] == "system" and "Memoria narrativa" in m["content"])
    idx_user = next(i for i, m in enumerate(msgs) if m["role"] == "user")
    assert idx_mem < idx_user

    # 13. Todo cuelga de tmp_path.
    for p in tmp_path.rglob("*"):
        assert str(p).startswith(str(tmp_path))
