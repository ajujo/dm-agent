"""Tests de GestorEstado (F3.2). Usan tmp_path; no tocan el storage real."""

import json

import pytest

from dm_agent.esquemas.estado import EstadoPartida, FaseActual
from dm_agent.esquemas.ficha import Atributos, Ficha
from dm_agent.estado.gestor import (
    ErrorEstadoInvalido,
    ErrorEstadoNoEncontrado,
    GestorEstado,
)

CAMP = "camp-1"


def _ficha(pid="pj-1", hp_actual=24):
    return Ficha(
        id=pid,
        nombre="Aelar",
        clase="Pícaro",
        nivel=3,
        raza="Elfo",
        trasfondo="Criminal",
        atributos=Atributos(
            fuerza=10, destreza=16, constitucion=12, inteligencia=8, sabiduria=13, carisma=11
        ),
        hp_max=24,
        hp_actual=hp_actual,
        ca=15,
        bonificador_competencia=2,
        xp=900,
    )


def _estado(turno=0):
    return EstadoPartida(
        id="estado-1",
        campaña_id=CAMP,
        personaje_activo_id="pj-1",
        fase_actual=FaseActual.EXPLORACION,
        turno=turno,
    )


# --- Campaña ------------------------------------------------------------------


def test_crear_campaña_si_no_existe(tmp_path):
    g = GestorEstado(tmp_path)
    assert g.existe_campaña(CAMP) is False
    ruta = g.crear_campaña_si_no_existe(CAMP)
    assert ruta.is_dir()
    assert (ruta / "fichas").is_dir()
    assert g.existe_campaña(CAMP) is True


# --- Ficha --------------------------------------------------------------------


def test_guardar_y_cargar_ficha(tmp_path):
    g = GestorEstado(tmp_path)
    ruta = g.guardar_ficha(CAMP, _ficha())
    assert ruta.is_file()
    cargada = g.cargar_ficha(CAMP, "pj-1")
    assert cargada == _ficha()


def test_listar_fichas(tmp_path):
    g = GestorEstado(tmp_path)
    assert g.listar_fichas(CAMP) == []
    g.guardar_ficha(CAMP, _ficha("pj-1"))
    g.guardar_ficha(CAMP, _ficha("pj-2"))
    assert g.listar_fichas(CAMP) == ["pj-1", "pj-2"]


def test_error_si_ficha_no_existe(tmp_path):
    g = GestorEstado(tmp_path)
    g.crear_campaña_si_no_existe(CAMP)
    with pytest.raises(ErrorEstadoNoEncontrado):
        g.cargar_ficha(CAMP, "fantasma")


# --- EstadoPartida ------------------------------------------------------------


def test_guardar_y_cargar_estado(tmp_path):
    g = GestorEstado(tmp_path)
    ruta = g.guardar_estado_partida(_estado(turno=5))
    assert ruta.is_file()
    cargado = g.cargar_estado_partida(CAMP)
    assert cargado.turno == 5
    assert cargado == _estado(turno=5)


def test_error_si_estado_no_existe(tmp_path):
    g = GestorEstado(tmp_path)
    with pytest.raises(ErrorEstadoNoEncontrado):
        g.cargar_estado_partida("inexistente")


# --- Errores de contenido -----------------------------------------------------


def test_error_si_json_corrupto(tmp_path):
    g = GestorEstado(tmp_path)
    g.guardar_ficha(CAMP, _ficha())
    ruta = g._ruta_ficha(CAMP, "pj-1")
    ruta.write_text("{ esto no es json", encoding="utf-8")
    with pytest.raises(ErrorEstadoInvalido):
        g.cargar_ficha(CAMP, "pj-1")


def test_error_si_schema_invalido(tmp_path):
    g = GestorEstado(tmp_path)
    g.guardar_ficha(CAMP, _ficha())
    ruta = g._ruta_ficha(CAMP, "pj-1")
    # JSON válido pero hp_actual > hp_max -> viola el esquema.
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["hp_actual"] = datos["hp_max"] + 100
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(ErrorEstadoInvalido):
        g.cargar_ficha(CAMP, "pj-1")


# --- Escritura atómica --------------------------------------------------------


def test_escritura_genera_json_valido_y_sin_temporales(tmp_path):
    g = GestorEstado(tmp_path)
    ruta = g.guardar_ficha(CAMP, _ficha())
    # El destino es JSON parseable...
    json.loads(ruta.read_text(encoding="utf-8"))
    # ...y no quedan ficheros temporales por la escritura atómica.
    assert list(ruta.parent.glob("*.tmp")) == []


# --- Snapshots ----------------------------------------------------------------


def _snaps(g, campaña=CAMP):
    snap_dir = g.ruta_campaña(campaña) / "snapshots"
    return sorted(snap_dir.glob("*.json")) if snap_dir.is_dir() else []


def test_snapshots_desactivados_por_defecto(tmp_path):
    g = GestorEstado(tmp_path)  # snapshots=False
    g.guardar_ficha(CAMP, _ficha())
    g.guardar_ficha(CAMP, _ficha(hp_actual=10))  # sobrescribe
    assert _snaps(g) == []


def test_snapshots_activados_al_sobrescribir_ficha(tmp_path):
    g = GestorEstado(tmp_path, snapshots=True)
    g.guardar_ficha(CAMP, _ficha())  # primera vez: sin snapshot
    assert _snaps(g) == []
    g.guardar_ficha(CAMP, _ficha(hp_actual=10))  # sobrescribe -> snapshot
    snaps = _snaps(g)
    assert len(snaps) == 1
    assert snaps[0].name.startswith("ficha_pj-1_")
    # El snapshot conserva el contenido ANTERIOR (hp_actual=24).
    assert json.loads(snaps[0].read_text(encoding="utf-8"))["hp_actual"] == 24


def test_snapshots_activados_al_sobrescribir_estado(tmp_path):
    g = GestorEstado(tmp_path, snapshots=True)
    g.guardar_estado_partida(_estado(turno=1))
    g.guardar_estado_partida(_estado(turno=2))
    snaps = _snaps(g)
    assert len(snaps) == 1
    assert snaps[0].name.startswith("estado_partida_")
    assert json.loads(snaps[0].read_text(encoding="utf-8"))["turno"] == 1


def test_no_snapshot_si_no_habia_previo(tmp_path):
    g = GestorEstado(tmp_path, snapshots=True)
    g.guardar_ficha(CAMP, _ficha())
    g.guardar_estado_partida(_estado())
    assert _snaps(g) == []


# --- Aislamiento --------------------------------------------------------------


def test_no_toca_rutas_fuera_de_tmp(tmp_path):
    g = GestorEstado(tmp_path)
    g.guardar_ficha(CAMP, _ficha())
    g.guardar_estado_partida(_estado())
    # Todo lo escrito cuelga de tmp_path.
    creados = list(tmp_path.rglob("*"))
    assert creados, "debería haber creado algo"
    for p in creados:
        assert str(p).startswith(str(tmp_path))
