"""Tests de la CLI / REPL (`dm_agent.cli`, `dm_agent.nucleo.bucle`)."""

from types import SimpleNamespace

import pytest

from dm_agent.cli import main
from dm_agent.nucleo.bucle import COMANDOS, SesionInteractiva, _texto_ayuda, repl


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
