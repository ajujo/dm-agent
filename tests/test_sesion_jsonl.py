"""Tests de la persistencia JSONL de sesión (`dm_agent.persistencia.sesion`)."""

import json

from dm_agent.persistencia.sesion import Sesion


def test_crear_sesion_crea_fichero(tmp_path):
    s = Sesion.crear(tmp_path)
    assert s.ruta.exists()
    assert s.ruta.suffix == ".jsonl"
    assert s.id == s.ruta.stem
    assert len(s) == 0


def test_guardar_y_cargar_historial(tmp_path):
    s = Sesion.crear(tmp_path, id="t1")
    s.registrar_usuario("Entro en la taberna")
    s.registrar_asistente("La taberna huele a humo.")
    s.registrar_tool_call("dados_tirar", {"expresion": "1d20+3"})
    s.registrar_tool_result("dados_tirar", {"total": 15}, ok=True)

    hist = s.historial()
    assert [e["tipo"] for e in hist] == ["user", "assistant", "tool_call", "tool_result"]
    assert hist[0]["content"] == "Entro en la taberna"
    assert hist[2]["argumentos"] == {"expresion": "1d20+3"}
    assert hist[3]["ok"] is True
    assert all("timestamp" in e for e in hist)


def test_jsonl_es_append_only_una_linea_por_registro(tmp_path):
    s = Sesion.crear(tmp_path, id="t2")
    s.registrar_usuario("a")
    s.registrar_asistente("b")
    lineas = s.ruta.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    for ln in lineas:
        json.loads(ln)  # cada línea es JSON válido


def test_continuar_sesion_existente(tmp_path):
    s = Sesion.crear(tmp_path, id="t3")
    s.registrar_usuario("hola")
    otra = Sesion.cargar(s.ruta)
    otra.registrar_asistente("respuesta")
    assert len(Sesion.cargar(s.ruta)) == 2


def test_ultima_sesion(tmp_path):
    assert Sesion.ultima(tmp_path) is None
    Sesion.crear(tmp_path, id="aaa")
    s2 = Sesion.crear(tmp_path, id="bbb")
    s2.registrar_usuario("x")  # toca mtime
    ultima = Sesion.ultima(tmp_path)
    assert ultima is not None
    assert ultima.id == "bbb"
