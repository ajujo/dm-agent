"""Tests de inyección de entidades narrativas en ConstructorContextoMemoria (F4.6).

Usan tmp_path; sin red.
"""

from dm_agent.esquemas.entidades import PNJ, FrenteAbierto, Lugar, Objetivo, Pista
from dm_agent.memoria.contexto import ConstructorContextoMemoria
from dm_agent.memoria.entidades import GestorEntidadesNarrativas
from dm_agent.memoria.narrativa import GestorMemoriaNarrativa

CAMP = "campana_demo"


def _gestores(tmp_path):
    return GestorMemoriaNarrativa(tmp_path), GestorEntidadesNarrativas(tmp_path)


def test_inyecta_entidades_si_existen(tmp_path):
    mem, ent = _gestores(tmp_path)
    ent.guardar_pnj(CAMP, PNJ(id="pnj_mara", nombre="Mara", rol="posadera",
                               descripcion="ayudó a Tyr", estado="activa"))
    ent.guardar_lugar(CAMP, Lugar(id="lugar_taberna", nombre="Taberna del Ciervo Gris",
                                  descripcion="punto de inicio"))
    ent.guardar_pista(CAMP, Pista(id="pista_llave", nombre="Llave oxidada",
                                  descripcion="encontrada bajo una mesa"))
    ent.guardar_objetivo(CAMP, Objetivo(id="obj_sotano", nombre="Investigar los ruidos del sótano",
                                        estado="activo"))
    ent.guardar_frente(CAMP, FrenteAbierto(id="frente_bruja", nombre="La bruja del medallón", reloj=2))

    constructor = ConstructorContextoMemoria(mem, gestor_entidades=ent)
    bloque = constructor.construir_bloque_memoria(CAMP)

    assert "# Memoria narrativa de campaña" in bloque
    assert "## Entidades importantes" in bloque
    assert "### PNJ" in bloque
    assert "Mara, posadera" in bloque
    assert "### Lugares" in bloque
    assert "Taberna del Ciervo Gris" in bloque
    assert "### Pistas" in bloque
    assert "Llave oxidada" in bloque
    assert "### Objetivos" in bloque
    assert "Investigar los ruidos del sótano" in bloque
    assert "### Frentes abiertos" in bloque
    assert "Reloj: 2/6" in bloque


def test_no_añade_seccion_si_no_hay_entidades(tmp_path):
    mem, ent = _gestores(tmp_path)
    constructor = ConstructorContextoMemoria(mem, gestor_entidades=ent)
    assert constructor.construir_bloque_memoria(CAMP) == ""


def test_sin_gestor_entidades_no_añade_seccion(tmp_path):
    mem, ent = _gestores(tmp_path)
    ent.guardar_pnj(CAMP, PNJ(id="pnj_mara", nombre="Mara"))
    constructor = ConstructorContextoMemoria(mem)  # sin gestor_entidades
    assert constructor.construir_bloque_memoria(CAMP) == ""


def test_respeta_limite_de_entidades(tmp_path):
    mem, ent = _gestores(tmp_path)
    for i in range(10):
        ent.guardar_pnj(CAMP, PNJ(id=f"pnj_{i}", nombre=f"PNJ {i}", importancia=5))
    constructor = ConstructorContextoMemoria(mem, gestor_entidades=ent, limite_entidades=3)
    bloque = constructor.construir_bloque_memoria(CAMP)
    lineas_pnj = [ln for ln in bloque.splitlines() if ln.startswith("- PNJ ")]
    assert len(lineas_pnj) == 3
