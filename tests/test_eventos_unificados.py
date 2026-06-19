"""Tests de la unificación de eventos (F3.5).

Verifica que `nucleo.eventos.Evento` es el modelo canónico
(`esquemas.evento.Evento`), que el bus runtime lo publica, que
`RegistroEventosEstado` hace round-trip JSONL, y que las tools `hp_xp.*` siguen
registrando (o no) eventos según corresponde.
"""

import pytest

from dm_agent.esquemas.evento import Evento as EventoCanonico
from dm_agent.esquemas.ficha import Ficha
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.hp_xp import crear_tools_hp_xp
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.nucleo.eventos import BusEventos, Evento, crear_evento

CAMP = "campana_demo"
PJ = "pj_tyr"


def _ficha_dict(hp_actual=20, hp_max=20, xp=100):
    return {
        "id": PJ,
        "nombre": "Tyr",
        "clase": "Guerrero",
        "nivel": 2,
        "raza": "Humano",
        "trasfondo": "Soldado",
        "atributos": {
            "fuerza": 16, "destreza": 12, "constitucion": 14,
            "inteligencia": 10, "sabiduria": 11, "carisma": 8,
        },
        "hp_max": hp_max,
        "hp_actual": hp_actual,
        "ca": 16,
        "bonificador_competencia": 2,
        "xp": xp,
    }


# --- modelo canónico ----------------------------------------------------------


def test_nucleo_evento_es_el_canonico():
    assert Evento is EventoCanonico


def test_crear_evento_canonico_valido():
    ev = crear_evento("daño_aplicado", actor="dm", objetivo=PJ, tool="hp_xp.aplicar_daño",
                       datos={"cantidad": 5})
    assert isinstance(ev, EventoCanonico)
    assert ev.id and ev.tipo == "daño_aplicado"
    assert ev.version_schema == 1


# --- bus runtime --------------------------------------------------------------


def test_bus_publica_evento_canonico():
    bus = BusEventos()
    recibidos: list[Evento] = []
    bus.subscribirse(recibidos.append)
    bus.publicar(crear_evento("prueba", datos={"x": 1}))
    assert len(recibidos) == 1
    assert isinstance(recibidos[0], EventoCanonico)


# --- registro JSONL round-trip ------------------------------------------------


def test_registrar_y_leer_jsonl(tmp_path):
    reg = RegistroEventosEstado(tmp_path)
    ev = crear_evento("daño_aplicado", actor="dm", objetivo=PJ, tool="hp_xp.aplicar_daño",
                      datos={"cantidad": 7, "hp_antes": 18, "hp_despues": 11})
    reg.registrar(CAMP, ev)
    leidos = reg.listar(CAMP)
    assert len(leidos) == 1
    leido = leidos[0]
    assert isinstance(leido, EventoCanonico)
    assert leido.tipo == "daño_aplicado"
    assert leido.tool == "hp_xp.aplicar_daño"
    assert leido.objetivo == PJ
    assert leido.datos == {"cantidad": 7, "hp_antes": 18, "hp_despues": 11}


# --- hp_xp sigue registrando vía canónica -------------------------------------


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorEstado(tmp_path)
    eventos = RegistroEventosEstado(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_hp_xp(gestor, eventos):
        reg.registrar(tool)
    gestor.guardar_ficha(CAMP, Ficha.model_validate(_ficha_dict(hp_actual=18)))
    return reg, eventos


def test_hp_xp_daño_registra_evento(entorno):
    reg, eventos = entorno
    reg.dispatch("hp_xp.aplicar_daño", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=7)
    ev = eventos.listar(CAMP)
    assert len(ev) == 1
    assert ev[0].tipo == "daño_aplicado"
    assert isinstance(ev[0], EventoCanonico)


def test_hp_xp_curacion_registra_evento(entorno):
    reg, eventos = entorno
    reg.dispatch("hp_xp.aplicar_curacion", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=1)
    ev = eventos.listar(CAMP)
    assert [e.tipo for e in ev] == ["curacion_aplicada"]


def test_hp_xp_xp_registra_evento(entorno):
    reg, eventos = entorno
    reg.dispatch("hp_xp.otorgar_xp", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=50)
    ev = eventos.listar(CAMP)
    assert [e.tipo for e in ev] == ["xp_otorgada"]


def test_hp_xp_consulta_no_registra_evento(entorno):
    reg, eventos = entorno
    reg.dispatch("hp_xp.consultar_estado_vital", ctx=None, campaña_id=CAMP, personaje_id=PJ)
    assert eventos.listar(CAMP) == []
