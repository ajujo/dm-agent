"""Tests de las tools inventario.* (F3.6). Usan tmp_path; no tocan storage real."""

import pytest

from dm_agent.esquemas.ficha import Ficha
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.inventario import crear_tools_inventario
from dm_agent.herramientas.registro import RegistroHerramientas

CAMP = "campana_demo"
PJ = "pj_tyr"


def _ficha_dict(inventario=None):
    return {
        "id": PJ,
        "nombre": "Tyr",
        "clase": "Guerrero",
        "nivel": 2,
        "raza": "Humano",
        "trasfondo": "Soldado",
        "atributos": {
            "fuerza": 16, "destreza": 12, "constitucion": 14,
            "inteligencia": 10, "sabiduria": 11, "carisma": 8,
        },
        "hp_max": 20,
        "hp_actual": 20,
        "ca": 16,
        "bonificador_competencia": 2,
        "xp": 0,
        "inventario": inventario or [],
    }


def _obj(oid="obj_llave", nombre="Llave oxidada", cantidad=1, descripcion=None, equipado=False):
    return {
        "id": oid, "nombre": nombre, "cantidad": cantidad,
        "descripcion": descripcion, "equipado": equipado,
    }


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorEstado(tmp_path)
    eventos = RegistroEventosEstado(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_inventario(gestor, eventos):
        reg.registrar(tool)
    return reg, eventos, gestor


def _crear_ficha(gestor, inventario=None):
    gestor.guardar_ficha(CAMP, Ficha.model_validate(_ficha_dict(inventario)))


def _inv(reg):
    res = reg.dispatch("inventario.listar", ctx=None, campaña_id=CAMP, personaje_id=PJ)
    return res.datos["inventario"]


# --- listar -------------------------------------------------------------------


def test_listar_inventario_vacio(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor)
    res = reg.dispatch("inventario.listar", ctx=None, campaña_id=CAMP, personaje_id=PJ)
    assert res.ok
    assert res.datos == {"personaje_id": PJ, "inventario": []}


# --- añadir -------------------------------------------------------------------


def test_añadir_objeto_nuevo(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor)
    res = reg.dispatch("inventario.añadir", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto=_obj())
    assert res.ok
    assert len(res.datos["inventario"]) == 1
    assert res.datos["inventario"][0]["id"] == "obj_llave"


def test_añadir_suma_cantidad_si_existe(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj(cantidad=2)])
    res = reg.dispatch(
        "inventario.añadir", ctx=None, campaña_id=CAMP, personaje_id=PJ,
        objeto=_obj(cantidad=3, descripcion="actualizada"),
    )
    assert res.ok
    inv = res.datos["inventario"]
    assert len(inv) == 1
    assert inv[0]["cantidad"] == 5
    assert inv[0]["descripcion"] == "actualizada"


def test_añadir_rechaza_objeto_invalido(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor)
    res = reg.dispatch(
        "inventario.añadir", ctx=None, campaña_id=CAMP, personaje_id=PJ,
        objeto=_obj(cantidad=0),  # cantidad < 1
    )
    assert res.ok is False
    assert res.errores


# --- quitar -------------------------------------------------------------------


def test_quitar_resta_cantidad(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj(cantidad=5)])
    res = reg.dispatch("inventario.quitar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_llave", cantidad=2)
    assert res.ok
    assert res.datos["inventario"][0]["cantidad"] == 3


def test_quitar_elimina_si_cantidad_cero(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj(cantidad=2)])
    res = reg.dispatch("inventario.quitar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_llave", cantidad=2)
    assert res.ok
    assert res.datos["inventario"] == []


def test_quitar_rechaza_mas_de_lo_disponible(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj(cantidad=2)])
    res = reg.dispatch("inventario.quitar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_llave", cantidad=5)
    assert res.ok is False
    assert res.errores
    # no se modificó
    assert _inv(reg)[0]["cantidad"] == 2


def test_quitar_rechaza_cantidad_no_positiva(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj(cantidad=2)])
    for mala in (0, -1):
        res = reg.dispatch("inventario.quitar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_llave", cantidad=mala)
        assert res.ok is False


def test_quitar_objeto_inexistente(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor)
    res = reg.dispatch("inventario.quitar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="fantasma", cantidad=1)
    assert res.ok is False


# --- equipar / desequipar -----------------------------------------------------


def test_equipar_marca_equipado(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj(oid="obj_espada", nombre="Espada", equipado=False)])
    res = reg.dispatch("inventario.equipar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_espada")
    assert res.ok
    assert res.datos["inventario"][0]["equipado"] is True


def test_desequipar_marca_no_equipado(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj(oid="obj_espada", nombre="Espada", equipado=True)])
    res = reg.dispatch("inventario.desequipar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_espada")
    assert res.ok
    assert res.datos["inventario"][0]["equipado"] is False


def test_equipar_objeto_inexistente(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor)
    res = reg.dispatch("inventario.equipar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="fantasma")
    assert res.ok is False


def test_desequipar_objeto_inexistente(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor)
    res = reg.dispatch("inventario.desequipar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="fantasma")
    assert res.ok is False


# --- eventos ------------------------------------------------------------------


def test_cada_cambio_registra_evento(entorno):
    reg, eventos, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj(oid="obj_espada", nombre="Espada", cantidad=1)])
    reg.dispatch("inventario.añadir", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto=_obj(cantidad=1))
    reg.dispatch("inventario.equipar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_espada")
    reg.dispatch("inventario.desequipar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_espada")
    reg.dispatch("inventario.quitar", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto_id="obj_espada", cantidad=1)

    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert tipos == ["objeto_añadido", "objeto_equipado", "objeto_desequipado", "objeto_quitado"]
    añadido = eventos.listar(CAMP)[0]
    assert añadido.datos["objeto_id"] == "obj_llave"
    assert añadido.datos["cantidad_antes"] == 0
    assert añadido.datos["cantidad_despues"] == 1


def test_listar_no_registra_evento(entorno):
    reg, eventos, gestor = entorno
    _crear_ficha(gestor, inventario=[_obj()])
    reg.dispatch("inventario.listar", ctx=None, campaña_id=CAMP, personaje_id=PJ)
    assert eventos.listar(CAMP) == []


# --- integración --------------------------------------------------------------


def test_dispatch_api_inventario_anadir(entorno):
    reg, _, gestor = entorno
    _crear_ficha(gestor)
    res = reg.dispatch_api("inventario_anadir", ctx=None, campaña_id=CAMP, personaje_id=PJ, objeto=_obj())
    assert res.ok
    assert res.datos["inventario"][0]["id"] == "obj_llave"


def test_schemas_disponibles_incluyen_inventario(entorno):
    reg, _, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    for esperado in (
        "inventario_listar",
        "inventario_anadir",  # añadir -> anadir
        "inventario_quitar",
        "inventario_equipar",
        "inventario_desequipar",
    ):
        assert esperado in nombres
