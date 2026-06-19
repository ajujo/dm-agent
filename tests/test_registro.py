"""Tests del registro de herramientas."""

import pytest

from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.herramientas.dados import crear_tool_dados
from dm_agent.herramientas.registro import (
    ColisionNombreApi,
    HerramientaNoRegistrada,
    HerramientaYaRegistrada,
    NombreHerramientaInvalido,
    RegistroHerramientas,
    nombre_interno_a_api,
)


class _ToolDummy:
    nombre = "dummy.eco"
    descripcion = "Devuelve eco de lo recibido."
    schema = {
        "type": "object",
        "properties": {"texto": {"type": "string"}},
        "required": ["texto"],
        "additionalProperties": False,
    }
    requiere: list[str] = []
    modifica: list[str] = []

    def disponible(self, ctx):
        return True, ""

    def ejecutar(self, ctx, **args):
        return ResultadoHerramienta(ok=True, datos={"eco": args["texto"]})


class _ToolNoDisponible:
    nombre = "indisponible.x"
    descripcion = "Nunca está disponible."
    schema = {"type": "object", "properties": {}, "additionalProperties": False}
    requiere: list[str] = []
    modifica: list[str] = []

    def disponible(self, ctx):
        return False, "razón de prueba"

    def ejecutar(self, ctx, **args):  # no debería llamarse
        raise AssertionError("no debe ejecutarse")


def test_registrar_y_dispatchar_dummy():
    reg = RegistroHerramientas()
    reg.registrar(_ToolDummy())
    res = reg.dispatch("dummy.eco", ctx=None, texto="hola")
    assert res.ok and res.datos == {"eco": "hola"}


def test_registro_rechaza_duplicado():
    reg = RegistroHerramientas()
    reg.registrar(_ToolDummy())
    with pytest.raises(HerramientaYaRegistrada):
        reg.registrar(_ToolDummy())


def test_obtener_lanza_si_no_existe():
    reg = RegistroHerramientas()
    with pytest.raises(HerramientaNoRegistrada):
        reg.obtener("no.existe")


def test_dispatch_marca_no_disponible_sin_ejecutar():
    reg = RegistroHerramientas()
    reg.registrar(_ToolNoDisponible())
    res = reg.dispatch("indisponible.x", ctx=None)
    assert res.ok is False
    assert any("razón de prueba" in e for e in res.errores)


def test_esquemas_disponibles_filtra_indisponibles_y_usa_nombre_api():
    reg = RegistroHerramientas()
    reg.registrar(_ToolDummy())
    reg.registrar(_ToolNoDisponible())
    esquemas = reg.esquemas_disponibles(ctx=None)
    nombres = {e["function"]["name"] for e in esquemas}
    # El schema enviado al LLM usa el nombre API (sin puntos), no el interno.
    assert "dummy_eco" in nombres
    assert "dummy.eco" not in nombres
    assert "indisponible_x" not in nombres


def test_tool_dados_se_integra_en_el_registro():
    reg = RegistroHerramientas()
    reg.registrar(crear_tool_dados())
    res = reg.dispatch("dados.tirar", ctx=None, expresion="1d6", semilla=1)
    assert res.ok
    assert 1 <= res.datos["total"] <= 6


# --- Mapeo de nombres interno <-> API (compatibilidad OpenAI-compatible) ------


def test_nombre_interno_a_api_reemplaza_puntos():
    assert nombre_interno_a_api("dados.tirar") == "dados_tirar"
    assert nombre_interno_a_api("combate.iniciar_combate") == "combate_iniciar_combate"
    assert nombre_interno_a_api("dados_tirar") == "dados_tirar"


def test_esquema_dados_usa_nombre_api():
    reg = RegistroHerramientas()
    reg.registrar(crear_tool_dados())
    esquemas = reg.esquemas_disponibles(ctx=None)
    nombres = {e["function"]["name"] for e in esquemas}
    assert "dados_tirar" in nombres
    assert "dados.tirar" not in nombres


def test_dispatch_api_ejecuta_la_tool_interna():
    reg = RegistroHerramientas()
    reg.registrar(crear_tool_dados())
    res = reg.dispatch_api("dados_tirar", ctx=None, expresion="1d6", semilla=1)
    assert res.ok
    assert 1 <= res.datos["total"] <= 6


def test_dispatch_api_desconocido_lanza():
    reg = RegistroHerramientas()
    reg.registrar(crear_tool_dados())
    with pytest.raises(HerramientaNoRegistrada):
        reg.dispatch_api("no_existe", ctx=None)


def test_nombre_api_a_interno_resuelve():
    reg = RegistroHerramientas()
    reg.registrar(crear_tool_dados())
    assert reg.nombre_api_a_interno("dados_tirar") == "dados.tirar"


def test_registrar_nombre_invalido_se_rechaza():
    class _ToolEspacio:
        nombre = "mala tool"  # espacio -> inválido
        descripcion = "x"
        schema = {"type": "object", "properties": {}, "additionalProperties": False}
        requiere: list[str] = []
        modifica: list[str] = []

        def disponible(self, ctx):
            return True, ""

        def ejecutar(self, ctx, **args):
            return ResultadoHerramienta(ok=True)

    reg = RegistroHerramientas()
    with pytest.raises(NombreHerramientaInvalido):
        reg.registrar(_ToolEspacio())


def test_colision_nombre_api_se_rechaza():
    """`a.b` y `a_b` producen el mismo nombre API `a_b`: debe fallar al registrar."""

    def _tool(nombre):
        t = _ToolDummy()
        t.nombre = nombre
        return t

    reg = RegistroHerramientas()
    reg.registrar(_tool("a.b"))
    with pytest.raises(ColisionNombreApi):
        reg.registrar(_tool("a_b"))
