"""Tests de las tools hp_xp.* (F3.4). Usan tmp_path; no tocan storage real."""

import pytest

from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.ficha import crear_tools_ficha
from dm_agent.herramientas.hp_xp import crear_tools_hp_xp
from dm_agent.herramientas.registro import RegistroHerramientas

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
            "fuerza": 16,
            "destreza": 12,
            "constitucion": 14,
            "inteligencia": 10,
            "sabiduria": 11,
            "carisma": 8,
        },
        "hp_max": hp_max,
        "hp_actual": hp_actual,
        "ca": 16,
        "bonificador_competencia": 2,
        "xp": xp,
    }


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorEstado(tmp_path)
    eventos = RegistroEventosEstado(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_ficha(gestor):
        reg.registrar(tool)
    for tool in crear_tools_hp_xp(gestor, eventos):
        reg.registrar(tool)
    return reg, eventos


def _crear_ficha(reg, **kw):
    res = reg.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict(**kw))
    assert res.ok


# --- daño ---------------------------------------------------------------------


def test_aplicar_daño_reduce_hp(entorno):
    reg, _ = entorno
    _crear_ficha(reg, hp_actual=18)
    res = reg.dispatch(
        "hp_xp.aplicar_daño", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=7,
        tipo_daño="cortante", motivo="ataque de goblin",
    )
    assert res.ok
    assert res.datos["hp_antes"] == 18
    assert res.datos["hp_despues"] == 11
    assert res.datos["hp_max"] == 20
    assert res.datos["estado_vital"] == "herido"


def test_aplicar_daño_no_baja_de_cero(entorno):
    reg, _ = entorno
    _crear_ficha(reg, hp_actual=5)
    res = reg.dispatch("hp_xp.aplicar_daño", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=999)
    assert res.ok
    assert res.datos["hp_despues"] == 0
    assert res.datos["estado_vital"] == "caido"


def test_aplicar_daño_rechaza_cantidad_no_positiva(entorno):
    reg, _ = entorno
    _crear_ficha(reg)
    for mala in (0, -3):
        res = reg.dispatch("hp_xp.aplicar_daño", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=mala)
        assert res.ok is False
        assert res.errores


# --- curación -----------------------------------------------------------------


def test_aplicar_curacion_sube_hp(entorno):
    reg, _ = entorno
    _crear_ficha(reg, hp_actual=6)
    res = reg.dispatch("hp_xp.aplicar_curacion", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=5, motivo="poción menor")
    assert res.ok
    assert res.datos["hp_antes"] == 6
    assert res.datos["hp_despues"] == 11


def test_aplicar_curacion_no_supera_hp_max(entorno):
    reg, _ = entorno
    _crear_ficha(reg, hp_actual=18, hp_max=20)
    res = reg.dispatch("hp_xp.aplicar_curacion", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=999)
    assert res.ok
    assert res.datos["hp_despues"] == 20
    assert res.datos["estado_vital"] == "sano"


def test_aplicar_curacion_rechaza_cantidad_no_positiva(entorno):
    reg, _ = entorno
    _crear_ficha(reg)
    res = reg.dispatch("hp_xp.aplicar_curacion", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=0)
    assert res.ok is False


# --- xp -----------------------------------------------------------------------


def test_otorgar_xp_suma(entorno):
    reg, _ = entorno
    _crear_ficha(reg, xp=100)
    res = reg.dispatch("hp_xp.otorgar_xp", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=50, motivo="encuentro social")
    assert res.ok
    assert res.datos["xp_antes"] == 100
    assert res.datos["xp_despues"] == 150
    assert res.datos["subida_nivel_pendiente"] is None


def test_otorgar_xp_rechaza_cantidad_no_positiva(entorno):
    reg, _ = entorno
    _crear_ficha(reg)
    res = reg.dispatch("hp_xp.otorgar_xp", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=-10)
    assert res.ok is False


# --- estado vital -------------------------------------------------------------


@pytest.mark.parametrize(
    "hp_actual,esperado",
    [(20, "sano"), (10, "herido"), (5, "critico"), (0, "caido")],
)
def test_consultar_estado_vital(entorno, hp_actual, esperado):
    reg, _ = entorno
    _crear_ficha(reg, hp_actual=hp_actual, hp_max=20)
    res = reg.dispatch("hp_xp.consultar_estado_vital", ctx=None, campaña_id=CAMP, personaje_id=PJ)
    assert res.ok
    assert res.datos["estado_vital"] == esperado
    assert res.datos["hp_actual"] == hp_actual
    assert res.datos["hp_max"] == 20


def test_porcentaje_hp(entorno):
    reg, _ = entorno
    _crear_ficha(reg, hp_actual=10, hp_max=20)
    res = reg.dispatch("hp_xp.consultar_estado_vital", ctx=None, campaña_id=CAMP, personaje_id=PJ)
    assert res.datos["porcentaje_hp"] == 50.0


# --- eventos auditables -------------------------------------------------------


def test_cada_cambio_registra_evento(entorno):
    reg, eventos = entorno
    _crear_ficha(reg, hp_actual=18, xp=100)
    reg.dispatch("hp_xp.aplicar_daño", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=7)
    reg.dispatch("hp_xp.aplicar_curacion", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=3)
    reg.dispatch("hp_xp.otorgar_xp", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=50)

    registrados = eventos.listar(CAMP)
    tipos = [e.tipo for e in registrados]
    assert tipos == ["daño_aplicado", "curacion_aplicada", "xp_otorgada"]
    # el evento de daño guarda hp_antes/hp_despues
    dano = registrados[0]
    assert dano.objetivo == PJ
    assert dano.tool == "hp_xp.aplicar_daño"
    assert dano.datos["hp_antes"] == 18
    assert dano.datos["hp_despues"] == 11


def test_consultar_estado_vital_no_registra_evento(entorno):
    reg, eventos = entorno
    _crear_ficha(reg)
    reg.dispatch("hp_xp.consultar_estado_vital", ctx=None, campaña_id=CAMP, personaje_id=PJ)
    assert eventos.listar(CAMP) == []


# --- errores e integración ----------------------------------------------------


def test_error_si_ficha_no_existe(entorno):
    reg, _ = entorno
    res = reg.dispatch("hp_xp.aplicar_daño", ctx=None, campaña_id="nope", personaje_id=PJ, cantidad=5)
    assert res.ok is False
    assert res.errores


def test_dispatch_api_aplicar_dano(entorno):
    reg, _ = entorno
    _crear_ficha(reg, hp_actual=20)
    # El nombre API translitera la ñ a ASCII: hp_xp_aplicar_dano.
    res = reg.dispatch_api("hp_xp_aplicar_dano", ctx=None, campaña_id=CAMP, personaje_id=PJ, cantidad=4)
    assert res.ok
    assert res.datos["hp_despues"] == 16


def test_schemas_disponibles_incluyen_hp_xp(entorno):
    reg, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    for esperado in (
        "hp_xp_aplicar_dano",  # ñ -> n
        "hp_xp_aplicar_curacion",
        "hp_xp_otorgar_xp",
        "hp_xp_consultar_estado_vital",
    ):
        assert esperado in nombres
