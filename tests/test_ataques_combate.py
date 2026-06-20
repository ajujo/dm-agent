"""Tests de resolución de ataques contra CA (F5.3). Usan tmp_path; sin red.

Las tiradas se mockean a través de `_tirar_ataque_d20` (devuelve (natural, total))
y `_tirar_dano` para que el resultado sea determinista, sin depender de
valores concretos del motor de dados.
"""

import pytest

from dm_agent.esquemas.ficha import Ficha
from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.combate import crear_tools_combate
from dm_agent.herramientas.registro import RegistroHerramientas

CAMP = "campana_demo"

_ENEMIGO_RATA = {"id": "rata_1", "nombre": "Rata gigante", "hp_max": 7, "hp_actual": 7, "ca": 12}


def _ficha_dict(personaje_id="pj_tyr", hp_actual=20, hp_max=20, ca=14):
    return {
        "id": personaje_id,
        "nombre": "Tyr",
        "clase": "Guerrero",
        "nivel": 2,
        "raza": "Humano",
        "atributos": {
            "fuerza": 16, "destreza": 12, "constitucion": 14,
            "inteligencia": 10, "sabiduria": 11, "carisma": 8,
        },
        "hp_max": hp_max,
        "hp_actual": hp_actual,
        "ca": ca,
        "bonificador_competencia": 2,
    }


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    eventos = RegistroEventosEstado(tmp_path)
    gestor_estado = GestorEstado(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_combate(gestor, eventos, gestor_estado):
        reg.registrar(tool)
    return reg, gestor, eventos, gestor_estado


def _iniciar(reg, **kwargs):
    args = {
        "campaña_id": CAMP,
        "personaje_id": "pj_tyr",
        "enemigos": [_ENEMIGO_RATA],
    }
    args.update(kwargs)
    return reg.dispatch("combate.iniciar", ctx=None, **args)


def _crear_ficha(gestor_estado, **kwargs):
    gestor_estado.guardar_ficha(CAMP, Ficha.model_validate(_ficha_dict(**kwargs)))


def _mock_ataque(monkeypatch, natural, total):
    monkeypatch.setattr(
        "dm_agent.herramientas.combate._tirar_ataque_d20", lambda mod, semilla: (natural, total)
    )


def _mock_dano(monkeypatch, valor):
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_dano", lambda expr, semilla: valor)


def _atacar_enemigo(reg, combate_id, **kwargs):
    args = {
        "campaña_id": CAMP,
        "combate_id": combate_id,
        "atacante_id": "pj_tyr",
        "enemigo_id": "rata_1",
        "modificador_ataque": 5,
        "dano": "1d8+3",
    }
    args.update(kwargs)
    return reg.dispatch("combate.atacar_enemigo", ctx=None, **args)


def _atacar_personaje(reg, combate_id, **kwargs):
    args = {
        "campaña_id": CAMP,
        "combate_id": combate_id,
        "enemigo_id": "rata_1",
        "personaje_id": "pj_tyr",
        "modificador_ataque": 4,
        "dano": "1d6+2",
    }
    args.update(kwargs)
    return reg.dispatch("combate.atacar_personaje", ctx=None, **args)


# --- ataque a enemigo ---------------------------------------------------------------


def test_ataque_enemigo_impacta_si_total_mayor_igual_ca(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 10, 15)  # ca=12 -> impacta
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["impacta"] is True


def test_ataque_enemigo_falla_si_total_menor_que_ca(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 5, 8)  # ca=12 -> falla
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["impacta"] is False
    assert res.datos["hp_despues"] == res.datos["hp_antes"]


def test_ataque_enemigo_natural_1_falla_aunque_total_alcance_ca(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 1, 16)  # natural 1, total 16 >= ca=12, pero pifia
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["pifia"] is True
    assert res.datos["impacta"] is False


def test_ataque_enemigo_natural_20_impacta_aunque_total_no_alcance_ca(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 20, 5)  # natural 20, total 5 < ca=12, pero crítico
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["critico"] is True
    assert res.datos["impacta"] is True


def test_ataque_enemigo_aplica_dano_si_impacta(entorno, monkeypatch):
    reg, gestor, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 10, 15)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.datos["hp_antes"] == 7
    assert res.datos["hp_despues"] == 3
    combate = gestor.cargar(CAMP, combate_id)
    assert combate.enemigos[0].hp_actual == 3


def test_ataque_enemigo_no_aplica_dano_si_falla(entorno, monkeypatch):
    reg, gestor, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 5, 8)
    _mock_dano(monkeypatch, 4)

    _atacar_enemigo(reg, combate_id)
    combate = gestor.cargar(CAMP, combate_id)
    assert combate.enemigos[0].hp_actual == 7


def test_ataque_enemigo_no_baja_hp_por_debajo_de_cero(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 10, 15)
    _mock_dano(monkeypatch, 999)

    res = _atacar_enemigo(reg, combate_id)
    assert res.datos["hp_despues"] == 0


def test_ataque_enemigo_actualiza_estado_a_derrotado(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 10, 15)
    _mock_dano(monkeypatch, 7)

    res = _atacar_enemigo(reg, combate_id)
    assert res.datos["hp_despues"] == 0
    assert res.datos["estado"] == "derrotado"


def test_ataque_enemigo_no_avanza_turno(entorno, monkeypatch):
    reg, gestor, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: 15)
    reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        personaje={"id": "pj_tyr"},
    )
    indice_antes = gestor.cargar(CAMP, combate_id).indice_turno_actual

    _mock_ataque(monkeypatch, 10, 15)
    _mock_dano(monkeypatch, 4)
    _atacar_enemigo(reg, combate_id)

    assert gestor.cargar(CAMP, combate_id).indice_turno_actual == indice_antes


def test_ataque_enemigo_registra_evento(entorno, monkeypatch):
    reg, _, eventos, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 10, 15)
    _mock_dano(monkeypatch, 4)

    _atacar_enemigo(reg, combate_id)
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert "ataque_enemigo_resuelto" in tipos


# --- ataque a personaje --------------------------------------------------------------


def test_ataque_personaje_impacta_contra_ca_de_ficha(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 12, 17)  # ca=14 -> impacta
    _mock_dano(monkeypatch, 3)

    res = _atacar_personaje(reg, combate_id)
    assert res.ok
    assert res.datos["impacta"] is True


def test_ataque_personaje_falla_contra_ca_de_ficha(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 5, 9)  # ca=14 -> falla
    _mock_dano(monkeypatch, 3)

    res = _atacar_personaje(reg, combate_id)
    assert res.ok
    assert res.datos["impacta"] is False


def test_ataque_personaje_aplica_dano_a_ficha_si_impacta(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, hp_actual=20, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 12, 17)
    _mock_dano(monkeypatch, 5)

    res = _atacar_personaje(reg, combate_id)
    assert res.datos["hp_antes"] == 20
    assert res.datos["hp_despues"] == 15
    ficha = gestor_estado.cargar_ficha(CAMP, "pj_tyr")
    assert ficha.hp_actual == 15


def test_ataque_personaje_no_modifica_ficha_si_falla(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, hp_actual=20, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 5, 9)
    _mock_dano(monkeypatch, 5)

    _atacar_personaje(reg, combate_id)
    ficha = gestor_estado.cargar_ficha(CAMP, "pj_tyr")
    assert ficha.hp_actual == 20


def test_ataque_personaje_devuelve_estado_vital(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, hp_actual=20, hp_max=20, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 12, 17)
    _mock_dano(monkeypatch, 18)

    res = _atacar_personaje(reg, combate_id)
    assert res.datos["hp_despues"] == 2
    assert res.datos["estado_vital"] == "critico"


def test_ataque_personaje_no_avanza_turno(entorno, monkeypatch):
    reg, gestor, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: 15)
    reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        personaje={"id": "pj_tyr"},
    )
    indice_antes = gestor.cargar(CAMP, combate_id).indice_turno_actual

    _mock_ataque(monkeypatch, 12, 17)
    _mock_dano(monkeypatch, 3)
    _atacar_personaje(reg, combate_id)

    assert gestor.cargar(CAMP, combate_id).indice_turno_actual == indice_antes


def test_ataque_personaje_registra_un_solo_evento(entorno, monkeypatch):
    reg, _, eventos, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 12, 17)
    _mock_dano(monkeypatch, 3)

    _atacar_personaje(reg, combate_id)
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    # solo ataque_personaje_resuelto: NO se llama a hp_xp.aplicar_daño (sin doble evento).
    assert tipos.count("ataque_personaje_resuelto") == 1
    assert "daño_aplicado" not in tipos


# --- dispatch_api / esquemas ----------------------------------------------------------


def test_dispatch_api_atacar_enemigo_funciona(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 10, 15)
    _mock_dano(monkeypatch, 4)

    res = reg.dispatch_api(
        "combate_atacar_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        atacante_id="pj_tyr", enemigo_id="rata_1", modificador_ataque=5, dano="1d8+3",
    )
    assert res.ok


def test_dispatch_api_atacar_personaje_funciona(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_ataque(monkeypatch, 12, 17)
    _mock_dano(monkeypatch, 3)

    res = reg.dispatch_api(
        "combate_atacar_personaje", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", personaje_id="pj_tyr", modificador_ataque=4, dano="1d6+2",
    )
    assert res.ok


def test_esquemas_disponibles_contienen_tools_ataque(entorno):
    reg, _, _, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    assert {"combate_atacar_enemigo", "combate_atacar_personaje"} <= nombres
