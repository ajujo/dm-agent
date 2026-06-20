"""Tests de contexto operativo activo (F6.5-B). Usan tmp_path; sin red.

`construir_bloque_contexto_operativo` deriva IDs reales (campaña/combate/
personaje activos) de `GestorCombateNarrativo`, sin LLM. Cubre: incluye los
IDs reales cuando existen, prohíbe explícitamente placeholders, y no rompe
si no hay combate activo.
"""

from dm_agent.esquemas.combate import CombateNarrativo, EntradaIniciativa
from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.nucleo.contexto_operativo import construir_bloque_contexto_operativo

CAMP = "campana_tyr"


def _combate(**kwargs):
    base = {"id": "combate_aa6049b2", "campaña_id": CAMP, "personaje_id": "tyr"}
    base.update(kwargs)
    return CombateNarrativo(**base)


def test_incluye_campaña_id_real(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    bloque = construir_bloque_contexto_operativo(gestor, CAMP)
    assert "campaña_id activa: campana_tyr" in bloque


def test_sin_combate_activo_no_rompe_y_lo_dice_explicito(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    bloque = construir_bloque_contexto_operativo(gestor, CAMP)
    assert "sin combate activo detectado" in bloque
    assert "combate_id activo" not in bloque


def test_incluye_combate_id_activo_real_si_existe(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    combate = _combate()
    gestor.guardar(combate)
    gestor.marcar_activo(combate)

    bloque = construir_bloque_contexto_operativo(gestor, CAMP)
    assert "combate_id activo: combate_aa6049b2" in bloque
    assert "estado combate: activo" in bloque
    assert "ronda: 1" in bloque


def test_incluye_personaje_id_real_del_combate_activo(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    combate = _combate(personaje_id="tyr")
    gestor.guardar(combate)
    gestor.marcar_activo(combate)

    bloque = construir_bloque_contexto_operativo(gestor, CAMP)
    assert "personaje_id activo: tyr" in bloque


def test_incluye_turno_actual_si_hay_iniciativa(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    combate = _combate(
        orden_iniciativa=[
            EntradaIniciativa(
                participante_id="tyr", nombre="Tyr", tipo="personaje", iniciativa=15,
                es_personaje=True,
            ),
            EntradaIniciativa(
                participante_id="rata_1", nombre="Rata", tipo="enemigo", iniciativa=8,
            ),
        ],
        indice_turno_actual=1,
    )
    gestor.guardar(combate)
    gestor.marcar_activo(combate)

    bloque = construir_bloque_contexto_operativo(gestor, CAMP)
    assert "turno actual: rata_1" in bloque


def test_prohibe_placeholders(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    bloque = construir_bloque_contexto_operativo(gestor, CAMP)
    assert "No uses placeholders" in bloque
    assert "campaña_actual" in bloque
    assert "combate_actual" in bloque
    assert "personaje_actual" in bloque


def test_personaje_id_explicito_tiene_prioridad_sobre_el_del_combate(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    combate = _combate(personaje_id="otro_pj")
    gestor.guardar(combate)
    gestor.marcar_activo(combate)

    bloque = construir_bloque_contexto_operativo(gestor, CAMP, personaje_id="tyr")
    assert "personaje_id activo: tyr" in bloque
