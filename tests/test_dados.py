"""Tests de `dados`: determinismo, modos y validación."""

import pytest

from dm_agent.herramientas.dados import (
    TipoTirada,
    crear_tool_dados,
    tirar,
    tirar_desventaja,
    tirar_ventaja,
)


def test_tirada_basica_con_semilla_es_reproducible():
    r1 = tirar("1d20+3", semilla=12345)
    r2 = tirar("1d20+3", semilla=12345)
    assert r1.total == r2.total
    assert r1.dados == r2.dados
    assert r1.modificador == 3
    assert 1 + 3 <= r1.total <= 20 + 3


def test_tirada_2d6_dentro_de_rango():
    for semilla in range(50):
        r = tirar("2d6", semilla=semilla)
        assert len(r.dados) == 2
        assert all(1 <= d <= 6 for d in r.dados)
        assert r.total == sum(r.dados)


def test_expresion_invalida_lanza_value_error():
    with pytest.raises(ValueError):
        tirar("hola")
    with pytest.raises(ValueError):
        tirar("0d20")
    with pytest.raises(ValueError):
        tirar("1d0")


def test_ventaja_toma_mayor_de_dos():
    r = tirar_ventaja("1d20", semilla=7)
    assert r.tipo is TipoTirada.VENTAJA
    assert len(r.dados) == 1
    assert len(r.dados_descartados) == 1
    assert r.dados[0] >= r.dados_descartados[0]


def test_desventaja_toma_menor_de_dos():
    r = tirar_desventaja("1d20", semilla=7)
    assert r.tipo is TipoTirada.DESVENTAJA
    assert r.dados[0] <= r.dados_descartados[0]


def test_critico_y_pifia_se_marcan_en_d20():
    # Forzar variaciones; con varias semillas debe aparecer al menos un 20 o un 1
    vistos_critico = False
    vistos_pifia = False
    for semilla in range(2000):
        r = tirar("1d20", semilla=semilla)
        if r.critico:
            vistos_critico = True
            assert r.dados[0] == 20
        if r.pifia:
            vistos_pifia = True
            assert r.dados[0] == 1
        if vistos_critico and vistos_pifia:
            break
    assert vistos_critico and vistos_pifia


def test_ventaja_exige_un_solo_dado_base():
    with pytest.raises(ValueError):
        tirar_ventaja("2d20")


def test_tool_dados_se_ejecuta_y_devuelve_evento():
    tool = crear_tool_dados()
    res = tool.ejecutar(ctx=None, expresion="1d20+2", semilla=42)
    assert res.ok is True
    assert "total" in res.datos
    assert len(res.eventos) == 1
    evt = res.eventos[0]
    assert evt.tipo == "dados_tirados"
    assert evt.datos["expresion"] == "1d20+2"


def test_tool_dados_rechaza_expresion_invalida():
    tool = crear_tool_dados()
    res = tool.ejecutar(ctx=None, expresion="abc")
    assert res.ok is False
    assert res.errores
