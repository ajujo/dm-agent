"""Tests del bus de eventos."""

from dm_agent.nucleo.eventos import BusEventos, Evento


def test_publicar_invoca_subscribers():
    bus = BusEventos()
    recibidos: list[Evento] = []
    bus.subscribirse(recibidos.append)
    bus.publicar(Evento(tipo="prueba", datos={"x": 1}))
    assert len(recibidos) == 1
    assert recibidos[0].tipo == "prueba"


def test_evento_tiene_momento_iso():
    evt = Evento(tipo="x")
    assert evt.momento.endswith("+00:00")


def test_limpiar_subscribers():
    bus = BusEventos()
    visto: list[int] = []
    bus.subscribirse(lambda e: visto.append(1))
    bus.limpiar()
    bus.publicar(Evento(tipo="x"))
    assert visto == []
