"""Tests de acciones de turno y propuestas de reacción (F5.5). Usan tmp_path; sin red.

`combate.proponer_reaccion`/`combate.resolver_reaccion` nunca tiran dados ni
aplican daño: solo gestionan el ciclo de vida de una `PropuestaReaccion`
(pendiente -> confirmada/rechazada/caducada). Aplicar de verdad una reacción
confirmada requiere una llamada explícita aparte a una tool de ataque
(D-COMBATE-04), que no se hace desde aquí.
"""

import pytest

from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.combate import crear_tools_combate
from dm_agent.herramientas.registro import RegistroHerramientas

CAMP = "campana_demo"

_ENEMIGO_RATA = {"id": "rata_1", "nombre": "Rata gigante", "hp_max": 7, "hp_actual": 7, "ca": 12}


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    eventos = RegistroEventosEstado(tmp_path)
    gestor_estado = GestorEstado(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_combate(gestor, eventos, gestor_estado):
        reg.registrar(tool)
    return reg, gestor, eventos


def _iniciar(reg, **kwargs):
    args = {
        "campaña_id": CAMP,
        "personaje_id": "pj_tyr",
        "enemigos": [_ENEMIGO_RATA],
    }
    args.update(kwargs)
    return reg.dispatch("combate.iniciar", ctx=None, **args)


def _registrar_accion(reg, combate_id, **kwargs):
    args = {
        "campaña_id": CAMP,
        "combate_id": combate_id,
        "turno_participante_id": "pj_tyr",
        "tipo": "accion",
        "descripcion": "Tyr ataca a la rata con su espada larga.",
        "consumida": True,
    }
    args.update(kwargs)
    return reg.dispatch("combate.registrar_accion_turno", ctx=None, **args)


def _proponer_reaccion(reg, combate_id, **kwargs):
    args = {
        "campaña_id": CAMP,
        "combate_id": combate_id,
        "tipo": "ataque_oportunidad",
        "quien_reacciona_id": "rata_1",
        "objetivo_id": "pj_tyr",
        "descripcion": "La rata podría morder a Tyr cuando intenta retirarse de cuerpo_a_cuerpo.",
        "motivo": "Tyr abandona cuerpo_a_cuerpo sin cubrirse.",
    }
    args.update(kwargs)
    return reg.dispatch("combate.proponer_reaccion", ctx=None, **args)


def _resolver_reaccion(reg, combate_id, propuesta_id, **kwargs):
    args = {
        "campaña_id": CAMP,
        "combate_id": combate_id,
        "propuesta_id": propuesta_id,
        "decision": "confirmar",
    }
    args.update(kwargs)
    return reg.dispatch("combate.resolver_reaccion", ctx=None, **args)


# --- combate.registrar_accion_turno ---------------------------------------------------


def test_registrar_accion_turno_anade_accion(entorno):
    reg, gestor, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    res = _registrar_accion(reg, combate_id)
    assert res.ok
    assert len(res.datos["combate"]["acciones_turno"]) == 1
    combate = gestor.cargar(CAMP, combate_id)
    assert combate.acciones_turno[0].turno_participante_id == "pj_tyr"
    assert combate.acciones_turno[0].tipo == "accion"
    assert combate.acciones_turno[0].consumida is True


def test_registrar_accion_turno_registra_evento(entorno):
    reg, _, eventos = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    _registrar_accion(reg, combate_id)
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert "accion_turno_registrada" in tipos


def test_registrar_accion_turno_no_avanza_turno(entorno, monkeypatch):
    reg, gestor, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: 15)
    reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        personaje={"id": "pj_tyr"},
    )
    indice_antes = gestor.cargar(CAMP, combate_id).indice_turno_actual

    _registrar_accion(reg, combate_id)
    assert gestor.cargar(CAMP, combate_id).indice_turno_actual == indice_antes


def test_registrar_accion_turno_no_falla_si_no_coincide_con_turno_actual(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: 15)
    reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        personaje={"id": "pj_tyr"},
    )
    # tiradas iguales -> empate -> gana el personaje: el turno actual es "pj_tyr".
    # registramos la acción a nombre de "rata_1" (no coincide) y comprobamos que no falla,
    # solo advierte.
    res = _registrar_accion(reg, combate_id, turno_participante_id="rata_1")
    assert res.ok
    assert res.datos["aviso"] is not None
    assert "rata_1" in res.datos["aviso"]


# --- combate.proponer_reaccion ---------------------------------------------------------


def test_proponer_reaccion_crea_propuesta_pendiente(entorno):
    reg, gestor, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    res = _proponer_reaccion(reg, combate_id)
    assert res.ok
    assert res.datos["propuesta"]["estado"] == "pendiente"
    assert res.datos["propuesta"]["confirmada"] is False
    combate = gestor.cargar(CAMP, combate_id)
    assert len(combate.propuestas_reaccion) == 1
    assert combate.propuestas_reaccion[0].estado == "pendiente"


def test_proponer_reaccion_no_aplica_dano_ni_tira_dados(entorno):
    reg, gestor, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    _proponer_reaccion(reg, combate_id)
    combate = gestor.cargar(CAMP, combate_id)
    # el HP del enemigo (potencial "quien_reacciona") no cambia: proponer no tira ni daña.
    assert combate.enemigos[0].hp_actual == 7


def test_proponer_reaccion_registra_evento(entorno):
    reg, _, eventos = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    _proponer_reaccion(reg, combate_id)
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert "reaccion_propuesta" in tipos


# --- combate.resolver_reaccion ----------------------------------------------------------


def test_resolver_reaccion_confirmar_cambia_a_confirmada(entorno):
    reg, gestor, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    propuesta_id = _proponer_reaccion(reg, combate_id).datos["propuesta"]["id"]

    res = _resolver_reaccion(reg, combate_id, propuesta_id, decision="confirmar")
    assert res.ok
    assert res.datos["propuesta"]["estado"] == "confirmada"
    assert res.datos["propuesta"]["confirmada"] is True
    combate = gestor.cargar(CAMP, combate_id)
    assert combate.propuestas_reaccion[0].estado == "confirmada"


def test_resolver_reaccion_rechazar_cambia_a_rechazada(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    propuesta_id = _proponer_reaccion(reg, combate_id).datos["propuesta"]["id"]

    res = _resolver_reaccion(reg, combate_id, propuesta_id, decision="rechazar")
    assert res.ok
    assert res.datos["propuesta"]["estado"] == "rechazada"
    assert res.datos["propuesta"]["confirmada"] is False


def test_resolver_reaccion_caducar_cambia_a_caducada(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    propuesta_id = _proponer_reaccion(reg, combate_id).datos["propuesta"]["id"]

    res = _resolver_reaccion(reg, combate_id, propuesta_id, decision="caducar")
    assert res.ok
    assert res.datos["propuesta"]["estado"] == "caducada"
    assert res.datos["propuesta"]["confirmada"] is False


def test_resolver_reaccion_no_aplica_ataque_ni_dano(entorno):
    reg, gestor, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    propuesta_id = _proponer_reaccion(reg, combate_id).datos["propuesta"]["id"]

    _resolver_reaccion(reg, combate_id, propuesta_id, decision="confirmar")
    combate = gestor.cargar(CAMP, combate_id)
    # confirmar no aplica el ataque de oportunidad: el HP del personaje/enemigo no cambia aquí.
    assert combate.enemigos[0].hp_actual == 7


def test_resolver_reaccion_propuesta_inexistente_da_error(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    res = _resolver_reaccion(reg, combate_id, "reaccion_no_existe", decision="confirmar")
    assert res.ok is False


def test_resolver_reaccion_decision_invalida_da_error(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    propuesta_id = _proponer_reaccion(reg, combate_id).datos["propuesta"]["id"]

    res = _resolver_reaccion(reg, combate_id, propuesta_id, decision="aceptar")
    assert res.ok is False


def test_resolver_reaccion_registra_evento(entorno):
    reg, _, eventos = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    propuesta_id = _proponer_reaccion(reg, combate_id).datos["propuesta"]["id"]

    _resolver_reaccion(reg, combate_id, propuesta_id, decision="confirmar")
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert "reaccion_resuelta" in tipos


# --- combate.listar_reacciones ----------------------------------------------------------


def test_listar_reacciones_filtra_pendientes(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    id_1 = _proponer_reaccion(reg, combate_id).datos["propuesta"]["id"]
    id_2 = _proponer_reaccion(reg, combate_id, descripcion="Segunda propuesta").datos["propuesta"]["id"]
    _resolver_reaccion(reg, combate_id, id_2, decision="rechazar")

    res = reg.dispatch(
        "combate.listar_reacciones", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        estado="pendiente",
    )
    assert res.ok
    assert res.datos["total"] == 1
    assert res.datos["propuestas"][0]["id"] == id_1


def test_listar_reacciones_sin_filtro_devuelve_todas(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _proponer_reaccion(reg, combate_id)
    _proponer_reaccion(reg, combate_id, descripcion="Segunda propuesta")

    res = reg.dispatch("combate.listar_reacciones", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    assert res.ok
    assert res.datos["total"] == 2


def test_listar_reacciones_no_registra_evento(entorno):
    reg, _, eventos = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _proponer_reaccion(reg, combate_id)
    n_antes = len(eventos.listar(CAMP))

    reg.dispatch("combate.listar_reacciones", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    assert len(eventos.listar(CAMP)) == n_antes


# --- dispatch_api / esquemas -------------------------------------------------------------


def test_dispatch_api_proponer_reaccion_funciona(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    res = reg.dispatch_api(
        "combate_proponer_reaccion", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        tipo="ataque_oportunidad", quien_reacciona_id="rata_1", objetivo_id="pj_tyr",
    )
    assert res.ok
    assert res.datos["propuesta"]["estado"] == "pendiente"


def test_dispatch_api_resolver_reaccion_funciona(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    propuesta_id = _proponer_reaccion(reg, combate_id).datos["propuesta"]["id"]

    res = reg.dispatch_api(
        "combate_resolver_reaccion", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        propuesta_id=propuesta_id, decision="confirmar",
    )
    assert res.ok
    assert res.datos["propuesta"]["estado"] == "confirmada"


def test_esquemas_disponibles_contienen_tools_reaccion(entorno):
    reg, _, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    esperados = {
        "combate_registrar_accion_turno", "combate_proponer_reaccion",
        "combate_resolver_reaccion", "combate_listar_reacciones",
    }
    assert esperados <= nombres
