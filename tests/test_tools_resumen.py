"""Tests de las tools resumen.* (F4.2). Mock del cliente LLM; sin red ni storage real."""

import pytest

from dm_agent.esquemas.narrativa import crear_entrada
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.herramientas.resumen import crear_tools_resumen
from dm_agent.llm.cliente import RespuestaLLM
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.memoria.resumen import ResumidorNarrativo

CAMP = "campana_demo"


class FakeCliente:
    def __init__(self, contenido="## Estado actual\nResumen de prueba."):
        self.contenido = contenido
        self.llamadas = 0

    def chat(self, messages, **kwargs):
        self.llamadas += 1
        return RespuestaLLM(content=self.contenido)


@pytest.fixture
def entorno(tmp_path):
    memoria = GestorMemoriaNarrativa(tmp_path)
    resumidor = ResumidorNarrativo(FakeCliente(), memoria)
    reg = RegistroHerramientas()
    for tool in crear_tools_resumen(resumidor):
        reg.registrar(tool)
    return reg, memoria


def test_resumen_texto_dispatch(entorno):
    reg, memoria = entorno
    res = reg.dispatch("resumen.texto", ctx=None, campaña_id=CAMP, texto="Escena en la taberna.")
    assert res.ok
    assert res.datos["entrada"]["tipo"] == "resumen"
    assert len(memoria.listar_entradas(CAMP)) == 1


def test_resumen_texto_rechaza_vacio(entorno):
    reg, _ = entorno
    res = reg.dispatch("resumen.texto", ctx=None, campaña_id=CAMP, texto="   ")
    assert res.ok is False
    assert res.errores


def test_resumen_entradas_dispatch(entorno):
    reg, memoria = entorno
    memoria.registrar_entrada(crear_entrada(CAMP, "nota", "pasó algo importante"))
    res = reg.dispatch("resumen.entradas", ctx=None, campaña_id=CAMP, limite=10)
    assert res.ok
    assert res.datos["entrada"]["tipo"] == "resumen"


def test_resumen_entradas_sin_entradas_error_controlado(entorno):
    reg, _ = entorno
    res = reg.dispatch("resumen.entradas", ctx=None, campaña_id="vacia")
    assert res.ok is False
    assert res.errores


def test_dispatch_api_resumen_texto(entorno):
    reg, memoria = entorno
    res = reg.dispatch_api("resumen_texto", ctx=None, campaña_id=CAMP, texto="material")
    assert res.ok
    assert len(memoria.listar_entradas(CAMP)) == 1


def test_dispatch_api_resumen_entradas(entorno):
    reg, memoria = entorno
    memoria.registrar_entrada(crear_entrada(CAMP, "nota", "algo"))
    res = reg.dispatch_api("resumen_entradas", ctx=None, campaña_id=CAMP)
    assert res.ok


def test_schemas_disponibles_incluyen_resumen(entorno):
    reg, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    assert "resumen_texto" in nombres
    assert "resumen_entradas" in nombres
