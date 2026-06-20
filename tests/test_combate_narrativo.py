"""Tests de esquemas y GestorCombateNarrativo (F5.1, iniciativa F5.2, reacciones F5.5).

Usan tmp_path; sin red.
"""

import pytest
from pydantic import ValidationError

from dm_agent.esquemas.combate import (
    AccionTurno,
    CombateNarrativo,
    EnemigoCombate,
    EntradaIniciativa,
    PropuestaReaccion,
)
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


@pytest.mark.parametrize(
    "distancia", ["cuerpo_a_cuerpo", "corta", "media", "larga", "fuera_de_alcance"]
)
def test_distancia_valida(distancia):
    enemigo = _enemigo(distancia=distancia)
    assert enemigo.distancia == distancia


def test_rechaza_distancia_invalida():
    with pytest.raises(ValidationError):
        _enemigo(distancia="cerca")


def test_crear_combate_valido():
    combate = _combate(enemigos=[_enemigo().model_dump()])
    assert combate.estado == "activo"
    assert combate.turno == 0
    assert len(combate.enemigos) == 1


def test_entrada_iniciativa_valida():
    entrada = EntradaIniciativa(
        participante_id="pj_tyr", nombre="Tyr", tipo="personaje", iniciativa=15, es_personaje=True
    )
    assert entrada.iniciativa == 15
    assert entrada.es_personaje is True


def test_combate_acepta_orden_de_iniciativa():
    entradas = [
        EntradaIniciativa(participante_id="pj_tyr", nombre="Tyr", tipo="personaje", iniciativa=15, es_personaje=True),
        EntradaIniciativa(participante_id="rata_1", nombre="Rata gigante", tipo="enemigo", iniciativa=8),
    ]
    combate = _combate(orden_iniciativa=entradas, indice_turno_actual=0, ronda=1)
    assert len(combate.orden_iniciativa) == 2
    assert combate.orden_iniciativa[0].participante_id == "pj_tyr"
    assert combate.ronda == 1
    assert combate.indice_turno_actual == 0


def test_enemigo_mod_destreza_e_iniciativa_son_opcionales():
    enemigo = _enemigo()
    assert enemigo.mod_destreza is None
    assert enemigo.iniciativa is None
    enemigo_con_mod = _enemigo(mod_destreza=2, iniciativa=14)
    assert enemigo_con_mod.mod_destreza == 2
    assert enemigo_con_mod.iniciativa == 14


def test_rechaza_mod_destreza_fuera_de_rango():
    with pytest.raises(ValidationError):
        _enemigo(mod_destreza=11)
    with pytest.raises(ValidationError):
        _enemigo(mod_destreza=-11)


def test_crear_accion_turno_valida():
    accion = AccionTurno(turno_participante_id="pj_tyr", tipo="accion", id="accion_1")
    assert accion.consumida is False
    assert accion.version_schema == 1


def test_crear_propuesta_reaccion_valida():
    propuesta = PropuestaReaccion(
        id="reaccion_1", combate_id="combate_001", ronda=1, tipo="ataque_oportunidad",
        quien_reacciona_id="rata_1", objetivo_id="pj_tyr",
    )
    assert propuesta.estado == "pendiente"
    assert propuesta.confirmada is False
    assert propuesta.version_schema == 1


def test_combate_acepta_acciones_turno_y_propuestas_reaccion():
    accion = AccionTurno(id="accion_1", turno_participante_id="pj_tyr", tipo="accion")
    propuesta = PropuestaReaccion(
        id="reaccion_1", combate_id="combate_001", ronda=1, tipo="ataque_oportunidad",
        quien_reacciona_id="rata_1", objetivo_id="pj_tyr",
    )
    combate = _combate(acciones_turno=[accion], propuestas_reaccion=[propuesta])
    assert len(combate.acciones_turno) == 1
    assert len(combate.propuestas_reaccion) == 1
    assert combate.propuestas_reaccion[0].estado == "pendiente"


def test_combate_sin_acciones_ni_propuestas_devuelve_listas_vacias():
    combate = _combate()
    assert combate.acciones_turno == []
    assert combate.propuestas_reaccion == []


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
