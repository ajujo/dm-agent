"""Tests del ConstructorContextoMemoria (F4.3). Usan tmp_path; sin red."""

from dm_agent.esquemas.narrativa import crear_entrada
from dm_agent.memoria.contexto import ConstructorContextoMemoria
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa

CAMP = "campana_demo"


def _memoria(tmp_path):
    return GestorMemoriaNarrativa(tmp_path)


def _entrada(tipo="nota", contenido="pasó algo", **kw):
    return crear_entrada(CAMP, tipo, contenido, **kw)


def test_vacio_si_no_hay_entradas(tmp_path):
    c = ConstructorContextoMemoria(_memoria(tmp_path))
    assert c.construir_bloque_memoria(CAMP) == ""
    assert c.construir_bloque_memoria("otra") == ""


def test_incluye_resumen_reciente(tmp_path):
    mem = _memoria(tmp_path)
    mem.registrar_entrada(_entrada(tipo="resumen", contenido="Tyr está en la taberna.",
                                   titulo="Resumen", tags=["resumen"], importancia=5,
                                   origen="resumen"))
    bloque = ConstructorContextoMemoria(mem).construir_bloque_memoria(CAMP)
    assert "# Memoria narrativa de campaña" in bloque
    assert "## Resumen reciente" in bloque
    assert "Tyr está en la taberna." in bloque


def test_incluye_entradas_recientes(tmp_path):
    mem = _memoria(tmp_path)
    mem.registrar_entrada(_entrada(tipo="decision", titulo="Acepta el pacto"))
    bloque = ConstructorContextoMemoria(mem).construir_bloque_memoria(CAMP)
    assert "## Entradas recientes" in bloque
    assert "[decision] Acepta el pacto" in bloque


def test_respeta_limite_de_entradas(tmp_path):
    mem = _memoria(tmp_path)
    for i in range(10):
        mem.registrar_entrada(_entrada(contenido=f"nota {i}"))
    bloque = ConstructorContextoMemoria(mem, limite_entradas=3).construir_bloque_memoria(CAMP)
    lineas = [ln for ln in bloque.splitlines() if ln.startswith("- [")]
    assert len(lineas) == 3
    assert "nota 9" in bloque
    assert "nota 6" not in bloque  # quedó fuera del límite


def test_prioriza_ultimo_resumen_aunque_no_este_entre_recientes(tmp_path):
    mem = _memoria(tmp_path)
    mem.registrar_entrada(_entrada(tipo="resumen", contenido="RESUMEN VIEJO PERO PRESENTE",
                                   tags=["resumen"], importancia=5, origen="resumen"))
    for i in range(10):
        mem.registrar_entrada(_entrada(contenido=f"nota {i}"))
    bloque = ConstructorContextoMemoria(mem, limite_entradas=3).construir_bloque_memoria(CAMP)
    assert "RESUMEN VIEJO PERO PRESENTE" in bloque


def test_incluir_resumenes_false(tmp_path):
    mem = _memoria(tmp_path)
    mem.registrar_entrada(_entrada(tipo="resumen", contenido="no debería salir",
                                   tags=["resumen"], importancia=5, origen="resumen"))
    mem.registrar_entrada(_entrada(contenido="esto sí"))
    bloque = ConstructorContextoMemoria(mem, incluir_resumenes=False).construir_bloque_memoria(CAMP)
    assert "no debería salir" not in bloque
    assert "esto sí" in bloque


def test_no_modifica_archivos(tmp_path):
    mem = _memoria(tmp_path)
    mem.registrar_entrada(_entrada())
    antes = mem.ruta_entradas(CAMP).read_text(encoding="utf-8")
    ConstructorContextoMemoria(mem).construir_bloque_memoria(CAMP)
    assert mem.ruta_entradas(CAMP).read_text(encoding="utf-8") == antes
