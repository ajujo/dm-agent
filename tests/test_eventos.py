"""Tests del bus de eventos (runtime) sobre el Evento canónico."""

from dm_agent.nucleo.eventos import BusEventos, Evento, crear_evento


def test_publicar_invoca_subscribers():
    bus = BusEventos()
    recibidos: list[Evento] = []
    bus.subscribirse(recibidos.append)
    bus.publicar(crear_evento("prueba", datos={"x": 1}))
    assert len(recibidos) == 1
    assert recibidos[0].tipo == "prueba"


def test_evento_tiene_timestamp_iso():
    evt = crear_evento("x")
    assert evt.timestamp.endswith("+00:00")


def test_limpiar_subscribers():
    bus = BusEventos()
    visto: list[int] = []
    bus.subscribirse(lambda e: visto.append(1))
    bus.limpiar()
    bus.publicar(crear_evento("x"))
    assert visto == []
