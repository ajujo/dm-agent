"""Smoke test — el paquete importa y reporta su versión."""

import dm_agent


def test_paquete_importa():
    assert hasattr(dm_agent, "__version__")
    assert isinstance(dm_agent.__version__, str)
    assert dm_agent.__version__.count(".") == 2


def test_cli_main_no_crashea():
    from dm_agent.cli import main

    assert main([]) == 0
