"""Tests de la CLI / REPL (`dm_agent.cli`, `dm_agent.nucleo.bucle`)."""

from types import SimpleNamespace

import pytest

from dm_agent.cli import main
from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.herramientas.registro import RegistroHerramientas
from dm_agent.nucleo.bucle import (
    COMANDOS,
    ErrorComandoTool,
    SesionInteractiva,
    _texto_ayuda,
    parsear_comando_tool,
    repl,
)
from dm_agent.persistencia.sesion import Sesion


def test_version_sale_con_cero():
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_help_sale_con_cero():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_texto_ayuda_lista_todos_los_comandos():
    ayuda = _texto_ayuda()
    for cmd in COMANDOS:
        assert cmd in ayuda


def _repl_con_inputs(ctx, inputs):
    it = iter(inputs)
    salidas = []
    return repl(ctx, leer=lambda _prompt: next(it), escribir=salidas.append), salidas


def test_repl_ayuda_y_salir():
    ctx = SimpleNamespace()  # /ayuda y /salir no tocan ctx
    code, salidas = _repl_con_inputs(ctx, ["/ayuda", "/salir"])
    assert code == 0
    texto = "\n".join(salidas)
    assert "/ayuda" in texto and "/salir" in texto


def test_repl_envia_texto_al_agente():
    ctx = SimpleNamespace(procesar=lambda t: f"eco:{t}")
    code, salidas = _repl_con_inputs(ctx, ["hola mundo", "/salir"])
    assert code == 0
    assert "eco:hola mundo" in salidas


# --- F6.4.1: espacios iniciales/finales no deben impedir reconocer comandos -


def test_repl_tool_con_espacios_iniciales_se_reconoce_como_comando():
    llamadas_procesar = []
    llamadas_tool = []
    ctx = SimpleNamespace(
        procesar=lambda t: llamadas_procesar.append(t) or "no debería llamarse",
        ejecutar_tool_manual=lambda linea: llamadas_tool.append(linea) or "[tool] ok",
    )
    code, salidas = _repl_con_inputs(
        ctx, ['   /tool combate_atacar_enemigo {"a": 1}', "/salir"]
    )

    assert code == 0
    assert llamadas_procesar == []  # nunca se envió al LLM
    assert len(llamadas_tool) == 1
    assert any("[tool] ok" in s for s in salidas)


def test_repl_ayuda_con_espacios_iniciales_se_reconoce_como_comando():
    ctx = SimpleNamespace()  # /ayuda no toca ctx
    code, salidas = _repl_con_inputs(ctx, ["   /ayuda", "/salir"])

    assert code == 0
    texto = "\n".join(salidas)
    assert "Comandos disponibles" in texto


def test_perfil_inexistente_error_claro(capsys):
    code = main(["--perfil", "no_existe_perfil"])
    assert code == 2
    out = capsys.readouterr().out
    assert "No se pudo iniciar" in out
    # No debe haberse impreso un traceback.
    assert "Traceback" not in out


def test_sesion_interactiva_perfil_inexistente_lanza():
    from dm_agent.llm.cliente import ErrorConfiguracionLLM

    with pytest.raises(ErrorConfiguracionLLM):
        SesionInteractiva(perfil="no_existe_perfil")


# --- F6.4: comando /tool (ejecuta una tool real sin pasar por el LLM) -------


class _ToolFake:
    """Tool real mínima y registrable: solo memoriza con qué se la llamó."""

    def __init__(self, nombre: str, *, ok: bool = True) -> None:
        self.nombre = nombre
        self.descripcion = f"tool de prueba: {nombre}"
        self.schema = {"type": "object", "properties": {}, "additionalProperties": False}
        self.requiere: list[str] = []
        self.modifica: list[str] = []
        self.ok = ok
        self.llamadas: list[dict] = []

    def disponible(self, ctx):
        return True, ""

    def ejecutar(self, ctx, **args):
        self.llamadas.append(args)
        if self.ok:
            return ResultadoHerramienta(ok=True, datos={"recibido": args})
        return ResultadoHerramienta(ok=False, errores=["fallo simulado"])


class _CtxFakeTool:
    """Objeto mínimo con `registro`/`sesion`, suficiente para probar
    `SesionInteractiva.ejecutar_tool_manual` sin construir la sesión real
    completa (que exige config/perfiles/LLM)."""

    ejecutar_tool_manual = SesionInteractiva.ejecutar_tool_manual

    def __init__(self, registro, sesion=None):
        self.registro = registro
        self.sesion = sesion


def test_parsear_comando_tool_ok():
    nombre, argumentos = parsear_comando_tool(' ficha_leer {"personaje_id": "tyr"}')
    assert nombre == "ficha_leer"
    assert argumentos == {"personaje_id": "tyr"}


def test_parsear_comando_tool_json_invalido():
    with pytest.raises(ErrorComandoTool):
        parsear_comando_tool("ficha_leer {no es json}")


def test_parsear_comando_tool_falta_json():
    with pytest.raises(ErrorComandoTool):
        parsear_comando_tool("ficha_leer")


def test_parsear_comando_tool_json_no_es_objeto():
    with pytest.raises(ErrorComandoTool):
        parsear_comando_tool('ficha_leer ["no", "es", "objeto"]')


def test_ejecutar_tool_manual_invoca_dispatch_api_con_argumentos_correctos(tmp_path):
    registro = RegistroHerramientas()
    tool = _ToolFake("ficha.leer")
    registro.registrar(tool)
    sesion = Sesion.crear(tmp_path / "sesiones", id="s-tool-1")
    ctx = _CtxFakeTool(registro, sesion)

    salida = ctx.ejecutar_tool_manual(' ficha_leer {"campaña_id": "campana_tyr", "personaje_id": "tyr"}')

    assert tool.llamadas == [{"campaña_id": "campana_tyr", "personaje_id": "tyr"}]
    assert "[tool] ficha_leer -> ok=True" in salida
    assert "campana_tyr" in salida


def test_ejecutar_tool_manual_persiste_tool_call_y_result_sin_tocar_conversacion(tmp_path):
    registro = RegistroHerramientas()
    registro.registrar(_ToolFake("ficha.leer"))
    sesion = Sesion.crear(tmp_path / "sesiones", id="s-tool-2")
    ctx = _CtxFakeTool(registro, sesion)

    ctx.ejecutar_tool_manual(' ficha_leer {"personaje_id": "tyr"}')

    historial = sesion.historial()
    tipos = [ev["tipo"] for ev in historial]
    assert tipos == ["tool_call", "tool_result"]
    # No se registra como turno user/assistant: no entra en el historial
    # conversacional que `AgenteDM` reinyecta al LLM.
    assert "user" not in tipos
    assert "assistant" not in tipos


def test_ejecutar_tool_manual_json_invalido_no_rompe():
    registro = RegistroHerramientas()
    registro.registrar(_ToolFake("ficha.leer"))
    ctx = _CtxFakeTool(registro)

    salida = ctx.ejecutar_tool_manual("ficha_leer {esto no es json}")

    assert salida.startswith("[tool] error:")


def test_ejecutar_tool_manual_tool_inexistente():
    ctx = _CtxFakeTool(RegistroHerramientas())

    salida = ctx.ejecutar_tool_manual('tool_que_no_existe {"a": 1}')

    assert salida == "[tool] tool_que_no_existe -> error: herramienta desconocida"


def test_ejecutar_tool_manual_muestra_resultado_de_fallo():
    registro = RegistroHerramientas()
    registro.registrar(_ToolFake("combate.atacar_enemigo", ok=False))
    ctx = _CtxFakeTool(registro)

    salida = ctx.ejecutar_tool_manual("combate_atacar_enemigo {}")

    assert "[tool] combate_atacar_enemigo -> ok=False" in salida
    assert "fallo simulado" in salida


def test_tool_aparece_en_comandos_y_ayuda():
    assert "/tool" in COMANDOS
    assert "/tool" in _texto_ayuda()


def test_repl_tool_no_llama_al_cliente_llm():
    llamadas_procesar = []
    ctx = SimpleNamespace(
        procesar=lambda t: llamadas_procesar.append(t) or "no debería llamarse",
        ejecutar_tool_manual=lambda linea: f"[tool] eco:{linea.strip()}",
    )
    code, salidas = _repl_con_inputs(
        ctx, ['/tool ficha_leer {"personaje_id": "tyr"}', "/salir"]
    )

    assert code == 0
    assert any("[tool] eco:ficha_leer" in s for s in salidas)
    assert llamadas_procesar == []  # el camino normal (LLM) nunca se invocó


def test_repl_tool_sin_argumentos_tambien_se_enruta():
    ctx = SimpleNamespace(ejecutar_tool_manual=lambda linea: f"[tool] eco:{linea!r}")
    code, salidas = _repl_con_inputs(ctx, ["/tool", "/salir"])

    assert code == 0
    assert any(s.startswith("[tool] eco:") for s in salidas)
