"""Tests del servicio CierreSesionNarrativa (F4.4). Mock LLM; sin red ni storage real."""

import pytest

from dm_agent.llm.cliente import RespuestaLLM
from dm_agent.memoria.cierre_sesion import (
    CierreSesionNarrativa,
    CierreVacio,
    TextoSesionVacio,
)
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa

CAMP = "campana_demo"
SES = "sesion-001"

_CIERRE_OK = """# Resumen de cierre

Tyr exploró las ruinas y encontró un medallón. La bruja sigue esperando respuesta.

# Preparación de próxima sesión

Tyr está a las puertas del santuario interior, con el medallón en la mano."""


class FakeCliente:
    def __init__(self, contenido=_CIERRE_OK):
        self.contenido = contenido
        self.llamadas = []

    def chat(self, messages, **kwargs):
        self.llamadas.append({"messages": list(messages), "kwargs": kwargs})
        return RespuestaLLM(content=self.contenido)


@pytest.fixture
def entorno(tmp_path):
    memoria = GestorMemoriaNarrativa(tmp_path)
    cliente = FakeCliente()
    return CierreSesionNarrativa(cliente, memoria), cliente, memoria


def test_cierre_genera_dos_entradas(entorno):
    cierre, cliente, memoria = entorno
    res = cierre.cerrar_sesion(CAMP, SES, "Texto de la sesión jugada.")
    assert set(res) == {"resumen", "preparacion"}
    assert len(memoria.listar_entradas(CAMP)) == 2
    assert cliente.llamadas[0]["kwargs"].get("stream") is False


def test_tipos_de_entradas(entorno):
    cierre, _, _ = entorno
    res = cierre.cerrar_sesion(CAMP, SES, "algo")
    assert res["resumen"].tipo == "resumen"
    assert res["preparacion"].tipo == "siguiente_sesion"


def test_mismo_campaña_y_sesion_id(entorno):
    cierre, _, _ = entorno
    res = cierre.cerrar_sesion(CAMP, SES, "algo")
    for e in res.values():
        assert e.campaña_id == CAMP
        assert e.sesion_id == SES


def test_parseo_con_encabezados(entorno):
    cierre, _, _ = entorno
    res = cierre.cerrar_sesion(CAMP, SES, "algo")
    assert "medallón" in res["resumen"].contenido
    assert "santuario interior" in res["preparacion"].contenido
    # no se cuela el encabezado de preparación en el resumen
    assert "Preparación de próxima sesión" not in res["resumen"].contenido


def test_degradacion_sin_encabezados(tmp_path):
    memoria = GestorMemoriaNarrativa(tmp_path)
    cierre = CierreSesionNarrativa(FakeCliente(contenido="Solo texto plano sin encabezados."), memoria)
    res = cierre.cerrar_sesion(CAMP, SES, "algo")
    assert res["resumen"].contenido == "Solo texto plano sin encabezados."
    assert "Pendiente de preparar" in res["preparacion"].contenido


def test_texto_vacio_error(entorno):
    cierre, _, _ = entorno
    with pytest.raises(TextoSesionVacio):
        cierre.cerrar_sesion(CAMP, SES, "   ")


def test_cierre_vacio_del_modelo_error(tmp_path):
    memoria = GestorMemoriaNarrativa(tmp_path)
    cierre = CierreSesionNarrativa(FakeCliente(contenido="   "), memoria)
    with pytest.raises(CierreVacio):
        cierre.cerrar_sesion(CAMP, SES, "material")


def test_entradas_persisten_en_bitacora(entorno):
    cierre, _, memoria = entorno
    cierre.cerrar_sesion(CAMP, SES, "algo")
    md = memoria.ruta_bitacora(CAMP).read_text(encoding="utf-8")
    assert "Resumen de cierre" in md
    assert "Preparación de próxima sesión" in md
