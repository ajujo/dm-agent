"""Tests de esquemas y GestorCombateNarrativo (F5.1). Usan tmp_path; sin red."""

import pytest
from pydantic import ValidationError

from dm_agent.esquemas.combate import CombateNarrativo, EnemigoCombate
from dm_agent.estado.combate import ErrorCombateNoEncontrado, GestorCombateNarrativo

CAMP = "campana_demo"


def _enemigo(**kwargs):
    base = {"id": "rata_1", "nombre": "Rata gigante", "hp_max": 7, "hp_actual": 7, "ca": 12}
    base.update(kwargs)
    return EnemigoCombate(**base)


def _combate(**kwargs):
    base = {"id": "combate_001", "campaña_id": CAMP, "personaje_id": "pj_tyr"}
    base.update(kwargs)
    return CombateNarrativo(**base)


def test_crear_enemigo_valido():
    enemigo = _enemigo()
    assert enemigo.estado == "activo"
    assert enemigo.version_schema == 1


def test_rechaza_enemigo_con_hp_actual_mayor_que_hp_max():
    with pytest.raises(ValidationError):
        _enemigo(hp_actual=10)


def test_crear_combate_valido():
    combate = _combate(enemigos=[_enemigo().model_dump()])
    assert combate.estado == "activo"
    assert combate.turno == 0
    assert len(combate.enemigos) == 1


def test_guardar_y_cargar_combate(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    combate = _combate()
    gestor.guardar(combate)
    cargado = gestor.cargar(CAMP, combate.id)
    assert cargado.id == combate.id
    assert cargado.personaje_id == "pj_tyr"


def test_cargar_combate_inexistente_lanza_error(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    with pytest.raises(ErrorCombateNoEncontrado):
        gestor.cargar(CAMP, "no_existe")


def test_solo_un_combate_activo_por_campaña(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    c1 = _combate(id="combate_1")
    c2 = _combate(id="combate_2")
    gestor.guardar(c1)
    gestor.guardar(c2)
    gestor.marcar_activo(c1)
    gestor.marcar_activo(c2)
    activo = gestor.cargar_activo(CAMP)
    assert activo is not None
    assert activo.id == "combate_2"


def test_cargar_activo_sin_combate_devuelve_none(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    assert gestor.cargar_activo(CAMP) is None


def test_limpiar_activo(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    combate = _combate()
    gestor.guardar(combate)
    gestor.marcar_activo(combate)
    gestor.limpiar_activo(CAMP)
    assert gestor.cargar_activo(CAMP) is None


def test_listar_combates(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    gestor.guardar(_combate(id="combate_1"))
    gestor.guardar(_combate(id="combate_2"))
    gestor.marcar_activo(gestor.cargar(CAMP, "combate_1"))
    combates = gestor.listar(CAMP)
    assert {c.id for c in combates} == {"combate_1", "combate_2"}


def test_listar_campaña_sin_combates_devuelve_vacio(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    assert gestor.listar(CAMP) == []
