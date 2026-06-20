"""Tests de las tools combate.* (F5.1). Usan tmp_path; sin red."""

import pytest

from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.herramientas.combate import crear_tools_combate
from dm_agent.herramientas.registro import RegistroHerramientas

CAMP = "campana_demo"

_ENEMIGO_RATA = {
    "id": "rata_1",
    "nombre": "Rata gigante",
    "hp_max": 7,
    "hp_actual": 7,
    "ca": 12,
    "estado": "activo",
    "descripcion": "Una rata enorme con ojos febriles.",
    "distancia": "cuerpo_a_cuerpo",
    "tags": ["bestia", "sotano"],
}


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    eventos = RegistroEventosEstado(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_combate(gestor, eventos):
        reg.registrar(tool)
    return reg, gestor, eventos


def _iniciar(reg, **kwargs):
    args = {
        "campaña_id": CAMP,
        "sesion_id": "sesion_001",
        "personaje_id": "pj_tyr",
        "descripcion_escena": "Tyr baja al sótano y dos ratas gigantes emergen.",
        "enemigos": [_ENEMIGO_RATA],
    }
    args.update(kwargs)
    return reg.dispatch("combate.iniciar", ctx=None, **args)


def test_iniciar_crea_combate_activo(entorno):
    reg, gestor, _ = entorno
    res = _iniciar(reg)
    assert res.ok
    combate_id = res.datos["combate"]["id"]
    activo = gestor.cargar_activo(CAMP)
    assert activo is not None
    assert activo.id == combate_id
    assert activo.estado == "activo"
    assert len(activo.enemigos) == 1


def test_iniciar_rechaza_si_ya_hay_combate_activo(entorno):
    reg, _, _ = entorno
    _iniciar(reg)
    res = _iniciar(reg)
    assert res.ok is False
    assert res.errores


def test_iniciar_permite_nuevo_combate_si_el_anterior_esta_terminado(entorno):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    reg.dispatch("combate.terminar", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    res2 = _iniciar(reg)
    assert res2.ok


def test_estado_sin_combate_id_devuelve_activo(entorno):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch("combate.estado", ctx=None, campaña_id=CAMP)
    assert res.ok
    assert res.datos["combate"]["id"] == combate_id


def test_estado_no_registra_evento(entorno):
    reg, _, eventos = entorno
    _iniciar(reg)
    n_antes = len(eventos.listar(CAMP))
    reg.dispatch("combate.estado", ctx=None, campaña_id=CAMP)
    assert len(eventos.listar(CAMP)) == n_antes


def test_estado_sin_combate_activo_devuelve_error(entorno):
    reg, _, _ = entorno
    res = reg.dispatch("combate.estado", ctx=None, campaña_id=CAMP)
    assert res.ok is False


def test_añadir_enemigo(entorno):
    reg, _, _ = entorno
    res1 = _iniciar(reg, enemigos=[])
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch(
        "combate.añadir_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo={**_ENEMIGO_RATA, "id": "rata_2"},
    )
    assert res.ok
    assert len(res.datos["combate"]["enemigos"]) == 1
    assert res.datos["combate"]["enemigos"][0]["id"] == "rata_2"


def test_añadir_enemigo_rechaza_id_duplicado(entorno):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch(
        "combate.añadir_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo=_ENEMIGO_RATA,
    )
    assert res.ok is False
    assert res.errores


def test_daño_enemigo_reduce_hp(entorno):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch(
        "combate.daño_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", cantidad=4, motivo="Tyr golpea con su espada",
    )
    assert res.ok
    assert res.datos["hp_antes"] == 7
    assert res.datos["hp_despues"] == 3
    assert res.datos["estado"] == "herido"


def test_daño_enemigo_no_baja_de_cero(entorno):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch(
        "combate.daño_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", cantidad=999,
    )
    assert res.ok
    assert res.datos["hp_despues"] == 0


def test_daño_enemigo_actualiza_estado_a_derrotado(entorno):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch(
        "combate.daño_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", cantidad=7,
    )
    assert res.ok
    assert res.datos["estado"] == "derrotado"


@pytest.mark.parametrize("cantidad", [0, -3, True])
def test_daño_enemigo_rechaza_cantidad_invalida(entorno, cantidad):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch(
        "combate.daño_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", cantidad=cantidad,
    )
    assert res.ok is False


def test_terminar_marca_terminado_y_limpia_activo(entorno):
    reg, gestor, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch(
        "combate.terminar", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        resultado="Tyr derrota a las ratas.", motivo="enemigos derrotados",
    )
    assert res.ok
    assert res.datos["combate"]["estado"] == "terminado"
    assert gestor.cargar_activo(CAMP) is None
    assert gestor.cargar(CAMP, combate_id).estado == "terminado"


def test_cada_mutacion_registra_evento(entorno):
    reg, _, eventos = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    reg.dispatch(
        "combate.añadir_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo={**_ENEMIGO_RATA, "id": "rata_2"},
    )
    reg.dispatch(
        "combate.daño_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", cantidad=2,
    )
    reg.dispatch("combate.terminar", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert tipos == ["combate_iniciado", "enemigo_añadido", "daño_enemigo", "combate_terminado"]


def test_dispatch_api_dano_enemigo(entorno):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    res = reg.dispatch_api(
        "combate_dano_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", cantidad=1,
    )
    assert res.ok
    assert res.datos["hp_despues"] == 6


def test_esquemas_disponibles_contienen_tools_combate(entorno):
    reg, _, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    esperados = {
        "combate_iniciar", "combate_estado", "combate_anadir_enemigo",
        "combate_dano_enemigo", "combate_terminar",
        "combate_tirar_iniciativa", "combate_turno_actual", "combate_avanzar_turno",
    }
    assert esperados <= nombres


def test_dispatch_api_tirar_iniciativa(entorno, monkeypatch):
    reg, _, _ = entorno
    res1 = _iniciar(reg)
    combate_id = res1.datos["combate"]["id"]
    monkeypatch.setattr(
        "dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: 10 + mod
    )
    res = reg.dispatch_api(
        "combate_tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        personaje={"id": "pj_tyr", "mod_destreza": 2},
    )
    assert res.ok
    assert len(res.datos["orden_iniciativa"]) == 2
