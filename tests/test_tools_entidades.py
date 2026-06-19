"""Tests de las tools entidad.* (F4.6). Usan tmp_path; sin red."""

import pytest

from dm_agent.herramientas.entidades import crear_tools_entidades
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.memoria.entidades import GestorEntidadesNarrativas

CAMP = "campana_demo"


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorEntidadesNarrativas(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_entidades(gestor):
        reg.registrar(tool)
    return reg, gestor


def test_guardar_pnj_dispatch(entorno):
    reg, gestor = entorno
    res = reg.dispatch(
        "entidad.guardar_pnj", ctx=None, campaña_id=CAMP,
        id="pnj_mara", nombre="Mara", rol="posadera", descripcion="Ayudó a Tyr",
    )
    assert res.ok
    assert res.datos["pnj"]["nombre"] == "Mara"
    assert gestor.listar_pnj(CAMP)[0].rol == "posadera"


def test_guardar_pnj_dispatch_api(entorno):
    reg, _ = entorno
    res = reg.dispatch_api(
        "entidad_guardar_pnj", ctx=None, campaña_id=CAMP, id="pnj_mara", nombre="Mara",
    )
    assert res.ok


def test_listar_pnj_dispatch_api(entorno):
    reg, _ = entorno
    reg.dispatch_api("entidad_guardar_pnj", ctx=None, campaña_id=CAMP, id="pnj_mara", nombre="Mara")
    res = reg.dispatch_api("entidad_listar_pnj", ctx=None, campaña_id=CAMP)
    assert res.ok
    assert len(res.datos["pnj"]) == 1
    assert res.datos["pnj"][0]["nombre"] == "Mara"


def test_guardar_pnj_rechaza_sin_nombre(entorno):
    reg, _ = entorno
    res = reg.dispatch("entidad.guardar_pnj", ctx=None, campaña_id=CAMP, id="pnj_x", nombre="")
    assert res.ok is False
    assert res.errores


def test_guardar_pnj_rechaza_importancia_invalida(entorno):
    reg, _ = entorno
    res = reg.dispatch(
        "entidad.guardar_pnj", ctx=None, campaña_id=CAMP, id="pnj_x", nombre="X", importancia=9,
    )
    assert res.ok is False


def test_guardar_pnj_rechaza_sin_campaña_id(entorno):
    reg, _ = entorno
    res = reg.dispatch("entidad.guardar_pnj", ctx=None, id="pnj_x", nombre="X")
    assert res.ok is False


def test_guardar_y_listar_lugar(entorno):
    reg, _ = entorno
    res = reg.dispatch(
        "entidad.guardar_lugar", ctx=None, campaña_id=CAMP, id="lugar_taberna",
        nombre="Taberna del Ciervo Gris", tipo="taberna",
    )
    assert res.ok
    res = reg.dispatch("entidad.listar_lugares", ctx=None, campaña_id=CAMP)
    assert res.ok
    assert res.datos["lugares"][0]["nombre"] == "Taberna del Ciervo Gris"


def test_guardar_y_listar_pista(entorno):
    reg, _ = entorno
    reg.dispatch("entidad.guardar_pista", ctx=None, campaña_id=CAMP, id="pista_llave", nombre="Llave oxidada")
    res = reg.dispatch("entidad.listar_pistas", ctx=None, campaña_id=CAMP)
    assert res.ok
    assert res.datos["pistas"][0]["id"] == "pista_llave"


def test_guardar_y_listar_objetivo(entorno):
    reg, _ = entorno
    reg.dispatch(
        "entidad.guardar_objetivo", ctx=None, campaña_id=CAMP, id="obj_sotano",
        nombre="Investigar el sótano", estado="activo",
    )
    res = reg.dispatch("entidad.listar_objetivos", ctx=None, campaña_id=CAMP)
    assert res.ok
    assert res.datos["objetivos"][0]["estado"] == "activo"


def test_guardar_y_listar_frente(entorno):
    reg, _ = entorno
    reg.dispatch(
        "entidad.guardar_frente", ctx=None, campaña_id=CAMP, id="frente_bruja",
        nombre="La bruja del medallón", reloj=2,
    )
    res = reg.dispatch("entidad.listar_frentes", ctx=None, campaña_id=CAMP)
    assert res.ok
    assert res.datos["frentes"][0]["reloj"] == 2


def test_listar_en_campaña_sin_entidades_devuelve_vacio(entorno):
    reg, _ = entorno
    res = reg.dispatch("entidad.listar_pnj", ctx=None, campaña_id=CAMP)
    assert res.ok
    assert res.datos["pnj"] == []


def test_esquemas_disponibles_contienen_tools_entidades(entorno):
    reg, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    esperados = {
        "entidad_guardar_pnj", "entidad_listar_pnj",
        "entidad_guardar_lugar", "entidad_listar_lugares",
        "entidad_guardar_pista", "entidad_listar_pistas",
        "entidad_guardar_objetivo", "entidad_listar_objetivos",
        "entidad_guardar_frente", "entidad_listar_frentes",
    }
    assert esperados <= nombres
