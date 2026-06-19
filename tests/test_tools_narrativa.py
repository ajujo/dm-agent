"""Tests de las tools narrativa.* (F4.1). Usan tmp_path; no tocan storage real."""

import pytest

from dm_agent.herramientas.narrativa import crear_tools_narrativa
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa

CAMP = "campana_demo"


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorMemoriaNarrativa(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_narrativa(gestor):
        reg.registrar(tool)
    return reg, gestor


def test_registrar_persiste_entrada(entorno):
    reg, gestor = entorno
    res = reg.dispatch(
        "narrativa.registrar", ctx=None,
        campaña_id=CAMP, sesion_id="sesion_001", tipo="decision",
        titulo="Acepta el pacto", contenido="Tyr acepta llevar el medallón.",
        tags=["bruja", "pacto"], importancia=4, origen="agente",
    )
    assert res.ok
    assert res.datos["entrada"]["tipo"] == "decision"
    assert res.datos["entrada"]["importancia"] == 4
    assert gestor.ruta_entradas(CAMP).is_file()
    assert len(gestor.listar_entradas(CAMP)) == 1


def test_registrar_rechaza_contenido_vacio(entorno):
    reg, _ = entorno
    res = reg.dispatch("narrativa.registrar", ctx=None, campaña_id=CAMP, tipo="nota", contenido="  ")
    assert res.ok is False
    assert res.errores


def test_registrar_rechaza_importancia_invalida(entorno):
    reg, _ = entorno
    res = reg.dispatch(
        "narrativa.registrar", ctx=None, campaña_id=CAMP, tipo="nota",
        contenido="algo", importancia=9,
    )
    assert res.ok is False


def test_reciente_devuelve_ultimas(entorno):
    reg, _ = entorno
    for i in range(3):
        reg.dispatch("narrativa.registrar", ctx=None, campaña_id=CAMP, tipo="nota",
                     contenido=f"nota {i}")
    res = reg.dispatch("narrativa.reciente", ctx=None, campaña_id=CAMP, limite=2)
    assert res.ok
    assert len(res.datos["entradas"]) == 2
    assert res.datos["entradas"][-1]["contenido"] == "nota 2"
    assert res.datos["markdown"].startswith("## ")


def test_reciente_no_modifica_archivos(entorno):
    reg, gestor = entorno
    reg.dispatch("narrativa.registrar", ctx=None, campaña_id=CAMP, tipo="nota", contenido="x")
    antes = gestor.ruta_entradas(CAMP).read_text(encoding="utf-8")
    reg.dispatch("narrativa.reciente", ctx=None, campaña_id=CAMP)
    despues = gestor.ruta_entradas(CAMP).read_text(encoding="utf-8")
    assert antes == despues


def test_reciente_campaña_vacia(entorno):
    reg, _ = entorno
    res = reg.dispatch("narrativa.reciente", ctx=None, campaña_id="sin_nada")
    assert res.ok
    assert res.datos["entradas"] == []
    assert res.datos["markdown"] == ""


# --- integración --------------------------------------------------------------


def test_dispatch_api_narrativa_registrar(entorno):
    reg, gestor = entorno
    res = reg.dispatch_api(
        "narrativa_registrar", ctx=None, campaña_id=CAMP, tipo="pista",
        contenido="Hay marcas de garras en la puerta.",
    )
    assert res.ok
    assert len(gestor.listar_entradas(CAMP)) == 1


def test_schemas_disponibles_incluyen_narrativa(entorno):
    reg, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    assert "narrativa_registrar" in nombres
    assert "narrativa_reciente" in nombres
