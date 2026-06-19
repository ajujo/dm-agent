"""Tests de las tools ficha.* (F3.3). Usan tmp_path; no tocan storage real."""

import pytest

from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.ficha import crear_tools_ficha
from dm_agent.herramientas.registro import RegistroHerramientas

CAMP = "campana_demo"


def _ficha_dict(pid="pj_tyr", **overrides):
    base = {
        "id": pid,
        "nombre": "Tyr",
        "clase": "Guerrero",
        "nivel": 2,
        "raza": "Humano",
        "trasfondo": "Soldado",
        "atributos": {
            "fuerza": 16,
            "destreza": 12,
            "constitucion": 14,
            "inteligencia": 10,
            "sabiduria": 11,
            "carisma": 8,
        },
        "hp_max": 20,
        "hp_actual": 20,
        "ca": 16,
        "bonificador_competencia": 2,
        "xp": 300,
    }
    base.update(overrides)
    return base


@pytest.fixture
def registro(tmp_path):
    gestor = GestorEstado(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_ficha(gestor):
        reg.registrar(tool)
    return reg


# --- validar ------------------------------------------------------------------


def test_validar_acepta_ficha_valida(registro):
    res = registro.dispatch("ficha.validar", ctx=None, ficha=_ficha_dict())
    assert res.ok
    assert res.datos["ficha"]["id"] == "pj_tyr"


def test_validar_rechaza_ficha_invalida(registro):
    res = registro.dispatch("ficha.validar", ctx=None, ficha=_ficha_dict(hp_actual=999))
    assert res.ok is False
    assert res.errores


# --- guardar / leer / listar --------------------------------------------------


def test_guardar_ficha_valida(registro):
    res = registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    assert res.ok
    assert res.datos["personaje_id"] == "pj_tyr"
    assert "fichas/pj_tyr.json" in res.datos["ruta_relativa"]


def test_guardar_ficha_invalida(registro):
    res = registro.dispatch(
        "ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict(nivel=0)
    )
    assert res.ok is False
    assert res.errores


def test_leer_ficha_guardada(registro):
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    res = registro.dispatch("ficha.leer", ctx=None, campaña_id=CAMP, personaje_id="pj_tyr")
    assert res.ok
    assert res.datos["ficha"]["nombre"] == "Tyr"


def test_listar_fichas(registro):
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict("pj_tyr"))
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict("pj_kaelen"))
    res = registro.dispatch("ficha.listar", ctx=None, campaña_id=CAMP)
    assert res.ok
    assert res.datos["personajes"] == ["pj_kaelen", "pj_tyr"]


def test_listar_campaña_inexistente(registro):
    res = registro.dispatch("ficha.listar", ctx=None, campaña_id="no_existe")
    assert res.ok is False
    assert any("campaña no existe" in e for e in res.errores)


# --- leer: errores controlados ------------------------------------------------


def test_leer_ficha_inexistente(registro):
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    res = registro.dispatch("ficha.leer", ctx=None, campaña_id=CAMP, personaje_id="fantasma")
    assert res.ok is False
    assert any("ficha no existe" in e for e in res.errores)


def test_leer_campaña_inexistente(registro):
    res = registro.dispatch("ficha.leer", ctx=None, campaña_id="nope", personaje_id="pj_tyr")
    assert res.ok is False
    assert any("campaña no existe" in e for e in res.errores)


# --- actualizar ---------------------------------------------------------------


def test_actualizar_campo_permitido(registro):
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    res = registro.dispatch(
        "ficha.actualizar",
        ctx=None,
        campaña_id=CAMP,
        personaje_id="pj_tyr",
        cambios={"notas": "Encontró una llave oxidada", "xp": 450},
    )
    assert res.ok
    assert res.datos["ficha"]["notas"] == "Encontró una llave oxidada"
    assert res.datos["ficha"]["xp"] == 450
    # persistido
    leida = registro.dispatch("ficha.leer", ctx=None, campaña_id=CAMP, personaje_id="pj_tyr")
    assert leida.datos["ficha"]["xp"] == 450


def test_actualizar_rechaza_campo_desconocido(registro):
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    res = registro.dispatch(
        "ficha.actualizar",
        ctx=None,
        campaña_id=CAMP,
        personaje_id="pj_tyr",
        cambios={"superpoder": "volar"},
    )
    assert res.ok is False
    assert any("desconocidos" in e for e in res.errores)


def test_actualizar_rechaza_cambiar_id(registro):
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    res = registro.dispatch(
        "ficha.actualizar",
        ctx=None,
        campaña_id=CAMP,
        personaje_id="pj_tyr",
        cambios={"id": "otro"},
    )
    assert res.ok is False
    assert any("no modificables" in e for e in res.errores)


def test_actualizar_rechaza_resultado_invalido(registro):
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    res = registro.dispatch(
        "ficha.actualizar",
        ctx=None,
        campaña_id=CAMP,
        personaje_id="pj_tyr",
        cambios={"hp_actual": 999},  # > hp_max
    )
    assert res.ok is False
    assert res.errores
    # No debe haberse persistido el cambio inválido.
    leida = registro.dispatch("ficha.leer", ctx=None, campaña_id=CAMP, personaje_id="pj_tyr")
    assert leida.datos["ficha"]["hp_actual"] == 20


def test_actualizar_permite_reemplazar_atributos(registro):
    registro.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    nuevos = {
        "fuerza": 18,
        "destreza": 12,
        "constitucion": 14,
        "inteligencia": 10,
        "sabiduria": 11,
        "carisma": 8,
    }
    res = registro.dispatch(
        "ficha.actualizar",
        ctx=None,
        campaña_id=CAMP,
        personaje_id="pj_tyr",
        cambios={"atributos": nuevos},
    )
    assert res.ok
    assert res.datos["ficha"]["atributos"]["fuerza"] == 18


# --- integración con el registro / nombres API --------------------------------


def test_schemas_disponibles_tienen_nombres_api(registro):
    nombres = {e["function"]["name"] for e in registro.esquemas_disponibles(ctx=None)}
    for esperado in (
        "ficha_leer",
        "ficha_guardar",
        "ficha_validar",
        "ficha_actualizar",
        "ficha_listar",
    ):
        assert esperado in nombres


def test_dispatch_api_ficha_leer(registro):
    registro.dispatch_api("ficha_guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_dict())
    res = registro.dispatch_api(
        "ficha_leer", ctx=None, campaña_id=CAMP, personaje_id="pj_tyr"
    )
    assert res.ok
    assert res.datos["ficha"]["id"] == "pj_tyr"
