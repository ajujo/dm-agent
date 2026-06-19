"""Tests del esquema y gestor de memoria narrativa (F4.1). Usan tmp_path."""

import pytest
from pydantic import ValidationError

from dm_agent.esquemas.narrativa import EntradaNarrativa, crear_entrada
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa

CAMP = "campana_demo"


def _entrada(contenido="Tyr acepta el pacto.", **kw):
    return crear_entrada(CAMP, kw.pop("tipo", "decision"), contenido, **kw)


# --- esquema ------------------------------------------------------------------


def test_crear_entrada_valida():
    e = _entrada(titulo="El pacto", tags=["bruja"], importancia=4, origen="agente",
                 sesion_id="sesion_001")
    assert isinstance(e, EntradaNarrativa)
    assert e.id and e.timestamp
    assert e.campaña_id == CAMP
    assert e.importancia == 4
    assert e.version_schema == 1


def test_rechaza_contenido_vacio():
    with pytest.raises(ValidationError):
        crear_entrada(CAMP, "nota", "   ")


def test_rechaza_importancia_fuera_de_rango():
    with pytest.raises(ValidationError):
        _entrada(importancia=0)
    with pytest.raises(ValidationError):
        _entrada(importancia=6)


def test_rechaza_campaña_y_tipo_vacios():
    with pytest.raises(ValidationError):
        crear_entrada("", "nota", "algo")
    with pytest.raises(ValidationError):
        crear_entrada(CAMP, "", "algo")


def test_origen_invalido_rechazado():
    with pytest.raises(ValidationError):
        _entrada(origen="marciano")


# --- gestor -------------------------------------------------------------------


def test_registrar_crea_jsonl_y_markdown(tmp_path):
    g = GestorMemoriaNarrativa(tmp_path)
    g.registrar_entrada(_entrada(titulo="El pacto", tags=["bruja", "ruinas"],
                                 importancia=4, origen="agente"))
    assert g.ruta_entradas(CAMP).is_file()
    assert g.ruta_bitacora(CAMP).is_file()
    md = g.ruta_bitacora(CAMP).read_text(encoding="utf-8")
    assert "El pacto" in md
    assert "Tags: bruja, ruinas" in md
    assert "Importancia: 4" in md
    assert "Origen: agente" in md


def test_listar_respeta_limite(tmp_path):
    g = GestorMemoriaNarrativa(tmp_path)
    for i in range(5):
        g.registrar_entrada(_entrada(contenido=f"entrada {i}"))
    ultimas = g.listar_entradas(CAMP, limite=2)
    assert len(ultimas) == 2
    assert ultimas[-1].contenido == "entrada 4"


def test_listar_vacio_si_no_existe(tmp_path):
    g = GestorMemoriaNarrativa(tmp_path)
    assert g.listar_entradas("inexistente") == []


def test_ultimas_entradas_markdown(tmp_path):
    g = GestorMemoriaNarrativa(tmp_path)
    g.registrar_entrada(_entrada(titulo="Escena 1", tipo="escena"))
    md = g.ultimas_entradas_markdown(CAMP, limite=5)
    assert md.startswith("## ")
    assert "Escena 1" in md


def test_append_only_acumula(tmp_path):
    g = GestorMemoriaNarrativa(tmp_path)
    g.registrar_entrada(_entrada(contenido="a"))
    g.registrar_entrada(_entrada(contenido="b"))
    lineas = g.ruta_entradas(CAMP).read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2


def test_no_toca_fuera_de_tmp(tmp_path):
    g = GestorMemoriaNarrativa(tmp_path)
    g.registrar_entrada(_entrada())
    for p in tmp_path.rglob("*"):
        assert str(p).startswith(str(tmp_path))
