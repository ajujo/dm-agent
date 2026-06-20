"""Tests de iniciativa clásica y turnos narrativos (F5.2). Usan tmp_path; sin red.

Las tiradas se mockean a través de `_tirar_d20` para que el orden resultante
sea determinista en los tests, sin depender de valores concretos del motor de
dados (ver `_mock_tirar_d20`). El test de `semilla` comprueba reproducibilidad
por igualdad entre dos tiradas independientes, sin fijar valores mágicos.
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


def _mock_tirar_d20(monkeypatch, valores):
    """Sustituye `_tirar_d20` por una cola de totales (mod ya incluido).

    El orden de llamadas es siempre: personaje primero, luego cada enemigo en
    el orden de `combate.enemigos`.
    """
    it = iter(valores)
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: next(it))


def _tirar_iniciativa(reg, combate_id, **kwargs):
    args = {
        "campaña_id": CAMP,
        "combate_id": combate_id,
        "personaje": {"id": "pj_tyr"},
    }
    args.update(kwargs)
    return reg.dispatch("combate.tirar_iniciativa", ctx=None, **args)


def test_tirar_iniciativa_crea_orden(entorno, monkeypatch):
    reg, gestor, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [15, 8])

    res = _tirar_iniciativa(reg, combate_id)
    assert res.ok
    assert len(res.datos["orden_iniciativa"]) == 2
    assert res.datos["ronda"] == 1
    assert res.datos["indice_turno_actual"] == 0

    combate = gestor.cargar(CAMP, combate_id)
    assert combate.ronda == 1
    assert combate.indice_turno_actual == 0
    assert len(combate.orden_iniciativa) == 2


def test_orden_descendente_por_iniciativa(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [8, 15])  # pj=8, rata_1=15 -> la rata va primero

    res = _tirar_iniciativa(reg, combate_id)
    orden = res.datos["orden_iniciativa"]
    assert orden[0]["participante_id"] == "rata_1"
    assert orden[1]["participante_id"] == "pj_tyr"


def test_personaje_gana_empate_contra_enemigo(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [10, 10])  # empate

    res = _tirar_iniciativa(reg, combate_id)
    orden = res.datos["orden_iniciativa"]
    assert orden[0]["participante_id"] == "pj_tyr"
    assert orden[0]["es_personaje"] is True


def test_enemigos_empatados_orden_estable_por_nombre(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(
        reg,
        enemigos=[
            {**_ENEMIGO_RATA, "id": "rata_b", "nombre": "Rata B"},
            {**_ENEMIGO_RATA, "id": "rata_a", "nombre": "Rata A"},
        ],
    ).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [1, 10, 10])  # pj=1, rata_b=10, rata_a=10

    res = _tirar_iniciativa(reg, combate_id)
    orden = res.datos["orden_iniciativa"]
    nombres_empate = [e["nombre"] for e in orden[:2]]
    assert nombres_empate == ["Rata A", "Rata B"]


def test_enemigo_sin_mod_destreza_usa_cero(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    capturados: list[int] = []

    def fake(mod: int, semilla: int | None) -> int:
        capturados.append(mod)
        return 10

    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", fake)

    _tirar_iniciativa(reg, combate_id, personaje={"id": "pj_tyr", "mod_destreza": 3})
    assert capturados == [3, 0]


def test_turno_actual_devuelve_primer_turno_tras_iniciativa(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [15, 8])
    _tirar_iniciativa(reg, combate_id)

    res = reg.dispatch("combate.turno_actual", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    assert res.ok
    assert res.datos["turno_actual"]["participante_id"] == "pj_tyr"
    assert res.datos["ronda"] == 1


def test_turno_actual_sin_iniciativa_da_error(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    res = reg.dispatch("combate.turno_actual", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    assert res.ok is False


def test_avanzar_turno_avanza_al_siguiente(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [15, 8])
    _tirar_iniciativa(reg, combate_id)

    res = reg.dispatch(
        "combate.avanzar_turno", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        motivo="Tyr termina su acción",
    )
    assert res.ok
    assert res.datos["indice_turno_actual"] == 1
    assert res.datos["turno_actual"]["participante_id"] == "rata_1"
    assert res.datos["ronda"] == 1


def test_avanzar_turno_incrementa_ronda_al_cerrar_ciclo(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [15, 8])
    _tirar_iniciativa(reg, combate_id)

    reg.dispatch("combate.avanzar_turno", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    res = reg.dispatch("combate.avanzar_turno", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    assert res.ok
    assert res.datos["indice_turno_actual"] == 0
    assert res.datos["ronda"] == 2


def test_avanzar_turno_sin_iniciativa_da_error(entorno):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    res = reg.dispatch("combate.avanzar_turno", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    assert res.ok is False


def test_avanzar_turno_registra_evento(entorno, monkeypatch):
    reg, _, eventos = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [15, 8])
    _tirar_iniciativa(reg, combate_id)

    reg.dispatch(
        "combate.avanzar_turno", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        motivo="fin de acción",
    )
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert tipos[-1] == "turno_avanzado"


def test_tirar_iniciativa_registra_evento(entorno, monkeypatch):
    reg, _, eventos = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [15, 8])
    _tirar_iniciativa(reg, combate_id)

    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert "iniciativa_tirada" in tipos


def test_tirar_iniciativa_rechaza_personaje_id_distinto(entorno, monkeypatch):
    reg, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tirar_d20(monkeypatch, [15, 8])

    res = _tirar_iniciativa(reg, combate_id, personaje={"id": "otro_pj"})
    assert res.ok is False


def test_semilla_es_reproducible(entorno):
    reg, _, _ = entorno
    combate_id_1 = _iniciar(reg).datos["combate"]["id"]
    combate_id_2 = _iniciar(reg, campaña_id="otra_campana").datos["combate"]["id"]

    r1 = reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id_1,
        personaje={"id": "pj_tyr", "mod_destreza": 2}, semilla=42,
    )
    r2 = reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id="otra_campana", combate_id=combate_id_2,
        personaje={"id": "pj_tyr", "mod_destreza": 2}, semilla=42,
    )
    assert r1.ok and r2.ok
    assert r1.datos["orden_iniciativa"] == r2.datos["orden_iniciativa"]
