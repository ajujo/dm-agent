"""Smoke test — el paquete importa y reporta su versión."""

import dm_agent


def test_paquete_importa():
    assert hasattr(dm_agent, "__version__")
    assert isinstance(dm_agent.__version__, str)
    assert dm_agent.__version__.count(".") == 2


def test_cli_main_arranca_y_sale_limpio(monkeypatch, tmp_path):
    """main([]) arranca la REPL; con EOF inmediato debe salir con 0 sin traceback."""
    import builtins

    from dm_agent.cli import main
    from dm_agent.nucleo import bucle

    # Evita escribir sesiones en el storage real del repo durante el test.
    monkeypatch.setattr(bucle, "_dir_sesiones", lambda *a, **k: tmp_path)

    def _eof(_prompt=""):
        raise EOFError

    monkeypatch.setattr(builtins, "input", _eof)
    assert main([]) == 0
