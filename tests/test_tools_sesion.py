"""Tests de las tools sesion.* y del comando /cerrar (F4.4). Mock LLM; tmp_path."""

from types import SimpleNamespace

from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.herramientas.sesion import crear_tools_sesion
from dm_agent.llm.cliente import RespuestaLLM
from dm_agent.memoria.cierre_sesion import CierreSesionNarrativa
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa
from dm_agent.nucleo.bucle import COMANDOS, _texto_ayuda, repl
from dm_agent.persistencia.sesion import Sesion

CAMP = "campana_demo"

_CIERRE = """# Resumen de cierre

Pasó algo importante.

# Preparación de próxima sesión

Se retoma en la puerta."""


class FakeCliente:
    def chat(self, messages, **kwargs):
        return RespuestaLLM(content=_CIERRE)


def _entorno(tmp_path):
    memoria = GestorMemoriaNarrativa(tmp_path)
    cierre = CierreSesionNarrativa(FakeCliente(), memoria)
    dir_sesiones = tmp_path / "sesiones"
    reg = RegistroHerramientas()
    for tool in crear_tools_sesion(cierre, dir_sesiones):
        reg.registrar(tool)
    return reg, memoria, dir_sesiones


def test_cerrar_texto_dispatch(tmp_path):
    reg, memoria, _ = _entorno(tmp_path)
    res = reg.dispatch(
        "sesion.cerrar_texto", ctx=None, campaña_id=CAMP, sesion_id="manual_001",
        texto="Lo que ocurrió en la sesión.",
    )
    assert res.ok
    assert res.datos["resumen"]["tipo"] == "resumen"
    assert res.datos["preparacion"]["tipo"] == "siguiente_sesion"
    assert len(memoria.listar_entradas(CAMP)) == 2


def test_cerrar_texto_dispatch_api(tmp_path):
    reg, memoria, _ = _entorno(tmp_path)
    res = reg.dispatch_api(
        "sesion_cerrar_texto", ctx=None, campaña_id=CAMP, sesion_id="m1", texto="algo",
    )
    assert res.ok
    assert len(memoria.listar_entradas(CAMP)) == 2


def test_cerrar_sesion_inexistente_error_controlado(tmp_path):
    reg, _, _ = _entorno(tmp_path)
    res = reg.dispatch("sesion.cerrar", ctx=None, campaña_id=CAMP, sesion_id="no_existe")
    assert res.ok is False
    assert any("no existe" in e for e in res.errores)


def test_cerrar_sesion_existente(tmp_path):
    reg, memoria, dir_sesiones = _entorno(tmp_path)
    sesion = Sesion.crear(dir_sesiones, id="sesion-xyz")
    sesion.registrar_usuario("Entro en la taberna")
    sesion.registrar_asistente("La taberna está llena de humo.")
    res = reg.dispatch("sesion.cerrar", ctx=None, campaña_id=CAMP, sesion_id="sesion-xyz")
    assert res.ok
    assert res.datos["preparacion"]["tipo"] == "siguiente_sesion"


def test_schemas_disponibles_incluyen_sesion(tmp_path):
    reg, _, _ = _entorno(tmp_path)
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    assert "sesion_cerrar" in nombres
    assert "sesion_cerrar_texto" in nombres


# --- comando /cerrar ----------------------------------------------------------


def test_cerrar_en_ayuda():
    assert "/cerrar" in COMANDOS
    assert "/cerrar" in _texto_ayuda()


def test_repl_cerrar_invoca_ctx():
    llamado = {"n": 0}

    def _cerrar():
        llamado["n"] += 1
        return "cierre hecho"

    ctx = SimpleNamespace(cerrar_sesion=_cerrar)
    salidas = []
    it = iter(["/cerrar", "/salir"])
    code = repl(ctx, leer=lambda _p: next(it), escribir=salidas.append)
    assert code == 0
    assert llamado["n"] == 1
    assert "cierre hecho" in salidas
