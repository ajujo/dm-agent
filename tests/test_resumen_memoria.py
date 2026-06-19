"""Tests del ResumidorNarrativo (F4.2). Mock del cliente LLM; sin red ni storage real."""

import pytest

from dm_agent.esquemas.narrativa import crear_entrada
from dm_agent.llm.cliente import RespuestaLLM
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.memoria.resumen import (
    MaterialVacio,
    ResumenVacio,
    ResumidorNarrativo,
    SinEntradasParaResumir,
)

CAMP = "campana_demo"


class FakeCliente:
    """Cliente LLM falso: devuelve un contenido fijo y captura los messages."""

    def __init__(self, contenido="## Estado actual\nTyr está en la taberna."):
        self.contenido = contenido
        self.llamadas = []

    def chat(self, messages, **kwargs):
        self.llamadas.append({"messages": list(messages), "kwargs": kwargs})
        return RespuestaLLM(content=self.contenido)


@pytest.fixture
def entorno(tmp_path):
    memoria = GestorMemoriaNarrativa(tmp_path)
    cliente = FakeCliente()
    return ResumidorNarrativo(cliente, memoria), cliente, memoria


def _sembrar(memoria, n=3):
    for i in range(n):
        memoria.registrar_entrada(crear_entrada(CAMP, "nota", f"sucedió la cosa {i}"))


# --- resumir_texto ------------------------------------------------------------


def test_resumir_texto_llama_al_cliente_con_prompt(entorno):
    resumidor, cliente, _ = entorno
    resumidor.resumir_texto(CAMP, "Tyr entra en la taberna y pide cerveza.")
    assert len(cliente.llamadas) == 1
    msgs = cliente.llamadas[0]["messages"]
    assert msgs[0]["role"] == "system"
    assert "continuidad" in msgs[0]["content"].lower()
    assert msgs[1]["role"] == "user"
    assert "taberna" in msgs[1]["content"]
    # stream desactivado
    assert cliente.llamadas[0]["kwargs"].get("stream") is False


def test_resumir_texto_guarda_entrada_tipo_resumen(entorno):
    resumidor, _, memoria = entorno
    entrada = resumidor.resumir_texto(CAMP, "Algo que resumir.")
    assert entrada.tipo == "resumen"
    assert entrada.importancia == 5
    assert "resumen" in entrada.tags
    assert entrada.origen == "resumen"
    # persistida
    assert len(memoria.listar_entradas(CAMP)) == 1


def test_resumir_texto_rechaza_texto_vacio(entorno):
    resumidor, _, _ = entorno
    with pytest.raises(MaterialVacio):
        resumidor.resumir_texto(CAMP, "   ")


def test_resumen_vacio_del_modelo_es_error(tmp_path):
    memoria = GestorMemoriaNarrativa(tmp_path)
    resumidor = ResumidorNarrativo(FakeCliente(contenido="   "), memoria)
    with pytest.raises(ResumenVacio):
        resumidor.resumir_texto(CAMP, "material")


# --- resumir_entradas ---------------------------------------------------------


def test_resumir_entradas_resume_existentes(entorno):
    resumidor, cliente, memoria = entorno
    _sembrar(memoria, 3)
    entrada = resumidor.resumir_entradas(CAMP, limite=10)
    assert entrada.tipo == "resumen"
    # el material enviado al LLM contiene las entradas previas
    material = cliente.llamadas[0]["messages"][1]["content"]
    assert "sucedió la cosa 0" in material


def test_resumir_entradas_sin_entradas_es_error(entorno):
    resumidor, _, _ = entorno
    with pytest.raises(SinEntradasParaResumir):
        resumidor.resumir_entradas("campaña_vacia")


def test_resumen_aparece_en_jsonl_y_markdown(entorno):
    resumidor, _, memoria = entorno
    resumidor.resumir_texto(CAMP, "material")
    # JSONL
    entradas = memoria.listar_entradas(CAMP)
    assert any(e.tipo == "resumen" for e in entradas)
    # Markdown
    md = memoria.ruta_bitacora(CAMP).read_text(encoding="utf-8")
    assert "Resumen" in md
    assert "Importancia: 5" in md
