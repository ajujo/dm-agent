"""Tests de los esquemas base F3.1: Ficha, EstadoPartida, Evento."""

import json

import pytest
from pydantic import ValidationError

from dm_agent.esquemas import (
    Atributos,
    EstadoPartida,
    Evento,
    Ficha,
    ObjetoInventario,
    crear_evento,
)
from dm_agent.esquemas.estado import FaseActual


def _atributos():
    return Atributos(
        fuerza=10, destreza=14, constitucion=12, inteligencia=8, sabiduria=13, carisma=11
    )


def _ficha(**overrides):
    base = {
        "id": "pj-1",
        "nombre": "Aelar",
        "clase": "Pícaro",
        "nivel": 3,
        "raza": "Elfo",
        "trasfondo": "Criminal",
        "atributos": _atributos(),
        "hp_max": 24,
        "hp_actual": 24,
        "ca": 15,
        "bonificador_competencia": 2,
        "xp": 900,
    }
    base.update(overrides)
    return Ficha(**base)


# --- Ficha --------------------------------------------------------------------


def test_crear_ficha_valida():
    f = _ficha()
    assert f.nombre == "Aelar"
    assert f.version_schema == 1
    assert f.condiciones == []
    assert f.inventario == []


def test_ficha_con_inventario_valido():
    f = _ficha(
        inventario=[ObjetoInventario(id="obj-1", nombre="Daga", cantidad=2, equipado=True)]
    )
    assert f.inventario[0].cantidad == 2
    assert f.inventario[0].equipado is True


def test_rechazar_hp_actual_mayor_que_hp_max():
    with pytest.raises(ValidationError):
        _ficha(hp_max=20, hp_actual=21)


def test_rechazar_hp_actual_negativo():
    with pytest.raises(ValidationError):
        _ficha(hp_actual=-1)


def test_rechazar_atributo_fuera_de_rango():
    with pytest.raises(ValidationError):
        Atributos(
            fuerza=31, destreza=10, constitucion=10, inteligencia=10, sabiduria=10, carisma=10
        )
    with pytest.raises(ValidationError):
        Atributos(
            fuerza=0, destreza=10, constitucion=10, inteligencia=10, sabiduria=10, carisma=10
        )


def test_rechazar_nivel_cero():
    with pytest.raises(ValidationError):
        _ficha(nivel=0)


def test_rechazar_nivel_mayor_que_veinte():
    with pytest.raises(ValidationError):
        _ficha(nivel=21)


def test_rechazar_inventario_cantidad_cero():
    with pytest.raises(ValidationError):
        ObjetoInventario(id="x", nombre="Cuerda", cantidad=0)


def test_rechazar_campos_obligatorios_vacios():
    with pytest.raises(ValidationError):
        _ficha(nombre="   ")
    with pytest.raises(ValidationError):
        _ficha(clase="")
    with pytest.raises(ValidationError):
        _ficha(raza="")


def test_rechazar_ca_y_hp_no_positivos():
    with pytest.raises(ValidationError):
        _ficha(ca=0)
    with pytest.raises(ValidationError):
        _ficha(hp_max=0, hp_actual=0)


def test_rechazar_bonificador_competencia_bajo():
    with pytest.raises(ValidationError):
        _ficha(bonificador_competencia=1)


def test_exportar_importar_ficha():
    f = _ficha(condiciones=["envenenado"])
    dump = f.model_dump()
    f2 = Ficha.model_validate(dump)
    assert f2 == f
    # round-trip por JSON también
    f3 = Ficha.model_validate_json(f.model_dump_json())
    assert f3 == f


# --- EstadoPartida ------------------------------------------------------------


def test_crear_estado_valido():
    e = EstadoPartida(id="estado-1", campaña_id="camp-1", personaje_activo_id="pj-1")
    assert e.fase_actual == FaseActual.EXPLORACION
    assert e.turno == 0
    assert e.version_schema == 1


def test_estado_acepta_todas_las_fases():
    for fase in ["exploracion", "social", "combate", "descanso", "viaje", "gestion"]:
        e = EstadoPartida(id="e", campaña_id="c", fase_actual=fase)
        assert e.fase_actual.value == fase


def test_rechazar_fase_actual_invalida():
    with pytest.raises(ValidationError):
        EstadoPartida(id="e", campaña_id="c", fase_actual="picnic")


def test_rechazar_turno_negativo():
    with pytest.raises(ValidationError):
        EstadoPartida(id="e", campaña_id="c", turno=-1)


def test_rechazar_id_o_campaña_vacios():
    with pytest.raises(ValidationError):
        EstadoPartida(id="", campaña_id="c")
    with pytest.raises(ValidationError):
        EstadoPartida(id="e", campaña_id="  ")


def test_personaje_activo_opcional_pero_no_vacio_si_existe():
    e = EstadoPartida(id="e", campaña_id="c")
    assert e.personaje_activo_id is None
    with pytest.raises(ValidationError):
        EstadoPartida(id="e", campaña_id="c", personaje_activo_id="")


# --- Evento -------------------------------------------------------------------


def test_crear_evento_valido():
    ev = Evento(id="ev-1", tipo="dados_tirados", datos={"total": 15})
    assert ev.tipo == "dados_tirados"
    assert ev.datos == {"total": 15}
    assert ev.version_schema == 1
    assert ev.actor is None


def test_evento_genera_timestamp_utc_por_defecto():
    ev = Evento(id="ev-2", tipo="x")
    assert ev.timestamp.endswith("+00:00") or "T" in ev.timestamp
    # parseable y con tz
    from datetime import datetime

    dt = datetime.fromisoformat(ev.timestamp)
    assert dt.utcoffset() is not None


def test_evento_serializa_y_deserializa():
    ev = crear_evento("hp_aplicado", actor="motor", objetivo="pj-1", datos={"delta": -5})
    como_json = ev.model_dump_json()
    recuperado = Evento.model_validate_json(como_json)
    assert recuperado == ev
    # y es JSON estándar
    assert json.loads(como_json)["tipo"] == "hp_aplicado"


def test_crear_evento_genera_id_si_no_se_da():
    ev = crear_evento("algo")
    assert ev.id  # uuid no vacío
    ev2 = crear_evento("algo")
    assert ev.id != ev2.id


def test_rechazar_evento_sin_tipo():
    with pytest.raises(ValidationError):
        Evento(id="ev", tipo="")


def test_version_schema_por_defecto_en_los_tres():
    assert _ficha().version_schema == 1
    assert EstadoPartida(id="e", campaña_id="c").version_schema == 1
    assert Evento(id="ev", tipo="t").version_schema == 1
