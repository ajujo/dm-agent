"""Tests de esquemas y GestorEntidadesNarrativas (F4.6). Usan tmp_path; sin red."""

import pytest
from pydantic import ValidationError

from dm_agent.esquemas.entidades import PNJ, FrenteAbierto, Lugar, Objetivo, Pista
from dm_agent.memoria.entidades import GestorEntidadesNarrativas

CAMP = "campana_demo"


def test_crear_pnj_valido():
    pnj = PNJ(id="pnj_mara", nombre="Mara", rol="posadera", descripcion="Posadera de la taberna")
    assert pnj.id == "pnj_mara"
    assert pnj.importancia == 3
    assert pnj.version_schema == 1


def test_rechaza_entidad_sin_nombre():
    with pytest.raises(ValidationError):
        PNJ(id="pnj_x", nombre="")


def test_rechaza_importancia_fuera_de_rango():
    with pytest.raises(ValidationError):
        PNJ(id="pnj_x", nombre="X", importancia=9)


def test_guardar_y_listar_pnj(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    gestor.guardar_pnj(CAMP, PNJ(id="pnj_mara", nombre="Mara", rol="posadera"))
    pnjs = gestor.listar_pnj(CAMP)
    assert len(pnjs) == 1
    assert pnjs[0].nombre == "Mara"


def test_guardar_y_listar_lugar(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    gestor.guardar_lugar(CAMP, Lugar(id="lugar_taberna", nombre="Taberna del Ciervo Gris"))
    lugares = gestor.listar_lugares(CAMP)
    assert len(lugares) == 1
    assert lugares[0].id == "lugar_taberna"


def test_guardar_y_listar_pista(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    gestor.guardar_pista(CAMP, Pista(id="pista_llave", nombre="Llave oxidada"))
    pistas = gestor.listar_pistas(CAMP)
    assert len(pistas) == 1
    assert pistas[0].nombre == "Llave oxidada"


def test_guardar_y_listar_objetivo(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    gestor.guardar_objetivo(
        CAMP, Objetivo(id="obj_sotano", nombre="Investigar los ruidos del sótano", estado="activo")
    )
    objetivos = gestor.listar_objetivos(CAMP)
    assert len(objetivos) == 1
    assert objetivos[0].estado == "activo"


def test_guardar_y_listar_frente(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    gestor.guardar_frente(
        CAMP, FrenteAbierto(id="frente_bruja", nombre="La bruja del medallón", reloj=2)
    )
    frentes = gestor.listar_frentes(CAMP)
    assert len(frentes) == 1
    assert frentes[0].reloj == 2


def test_guardar_reemplaza_entidad_con_mismo_id(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    gestor.guardar_pnj(CAMP, PNJ(id="pnj_mara", nombre="Mara", actitud="reservada"))
    gestor.guardar_pnj(CAMP, PNJ(id="pnj_mara", nombre="Mara", actitud="amistosa"))
    pnjs = gestor.listar_pnj(CAMP)
    assert len(pnjs) == 1
    assert pnjs[0].actitud == "amistosa"


def test_listar_ordenado_por_importancia_descendente_y_nombre(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    gestor.guardar_pnj(CAMP, PNJ(id="pnj_b", nombre="Beto", importancia=2))
    gestor.guardar_pnj(CAMP, PNJ(id="pnj_a", nombre="Ana", importancia=5))
    gestor.guardar_pnj(CAMP, PNJ(id="pnj_c", nombre="Carla", importancia=5))
    pnjs = gestor.listar_pnj(CAMP)
    assert [p.nombre for p in pnjs] == ["Ana", "Carla", "Beto"]


def test_listar_en_campaña_sin_entidades_devuelve_vacio(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    assert gestor.listar_pnj(CAMP) == []
    assert gestor.listar_lugares(CAMP) == []
    assert gestor.listar_pistas(CAMP) == []
    assert gestor.listar_objetivos(CAMP) == []
    assert gestor.listar_frentes(CAMP) == []
