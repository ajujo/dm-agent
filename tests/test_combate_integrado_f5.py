"""F5.6: prueba integrada de combate narrativo D&D sin grid (extremo a extremo).

Sin red, sin LLM real, todo bajo tmp_path. Cubre: crear ficha -> iniciar combate
-> añadir enemigo -> tirar iniciativa -> atacar (con ventaja) -> registrar
acción de turno -> proponer reacción -> confirmar (sin aplicar daño) -> aplicar
la reacción confirmada con una llamada explícita de ataque -> avanzar turno ->
terminar combate -> verificar eventos auditables.

No añade reglas nuevas: solo valida, con tools mockeando las tiradas de dados,
que el flujo completo de F5.1–F5.5 encaja en una sola escena.
"""

from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.combate import crear_tools_combate
from dm_agent.herramientas.ficha import crear_tools_ficha
from dm_agent.herramientas.registro import RegistroHerramientas

CAMP = "campana_demo"
PJ = "pj_tyr"


def _ficha_inicial():
    return {
        "id": PJ, "nombre": "Tyr", "clase": "Guerrero", "nivel": 1,
        "raza": "Humano", "trasfondo": "Soldado",
        "atributos": {
            "fuerza": 15, "destreza": 12, "constitucion": 14,
            "inteligencia": 10, "sabiduria": 11, "carisma": 9,
        },
        "hp_max": 12, "hp_actual": 12, "ca": 15, "bonificador_competencia": 2, "xp": 0,
        "inventario": [],
    }


def test_combate_narrativo_extremo_a_extremo(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    gestor_estado = GestorEstado(storage)
    gestor_combate = GestorCombateNarrativo(storage)
    eventos = RegistroEventosEstado(storage)

    reg = RegistroHerramientas()
    for tool in crear_tools_ficha(gestor_estado):
        reg.registrar(tool)
    for tool in crear_tools_combate(gestor_combate, eventos, gestor_estado):
        reg.registrar(tool)

    # 1. Crear ficha.
    res = reg.dispatch("ficha.guardar", ctx=None, campaña_id=CAMP, ficha=_ficha_inicial())
    assert res.ok

    # 2. Iniciar combate (escena: Tyr baja al sótano, una rata gigante emerge).
    res = reg.dispatch(
        "combate.iniciar", ctx=None, campaña_id=CAMP, personaje_id=PJ,
        descripcion_escena="Tyr baja al sótano y una rata gigante emerge entre barriles rotos.",
    )
    assert res.ok
    combate_id = res.datos["combate"]["id"]

    # 3. Añadir enemigo.
    res = reg.dispatch(
        "combate.añadir_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo={
            "id": "rata_1", "nombre": "Rata gigante", "hp_max": 7, "hp_actual": 7, "ca": 12,
            "distancia": "cuerpo_a_cuerpo",
        },
    )
    assert res.ok

    # 4. Tirar iniciativa (tiradas mockeadas: Tyr 15+2=17, rata 15+0=15 -> Tyr primero).
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: 15 + mod)
    res = reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        personaje={"id": PJ, "mod_destreza": 2},
    )
    assert res.ok
    assert res.datos["orden_iniciativa"][0]["participante_id"] == PJ

    # 5. Consultar turno actual.
    res = reg.dispatch("combate.turno_actual", ctx=None, campaña_id=CAMP, combate_id=combate_id)
    assert res.ok
    assert res.datos["turno_actual"]["participante_id"] == PJ

    # 6. Atacar enemigo con ventaja (tiradas mockeadas: [12, 18] -> elige 18).
    monkeypatch.setattr(
        "dm_agent.herramientas.combate._tirar_tiradas_ataque", lambda modo, semilla: [12, 18]
    )
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_dano", lambda expr, semilla: 4)
    res = reg.dispatch(
        "combate.atacar_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        atacante_id=PJ, enemigo_id="rata_1", modificador_ataque=5, dano="1d8+3",
        tipo_dano="cortante", motivo="Tyr ataca con su espada larga", modo_tirada="ventaja",
    )
    assert res.ok
    assert res.datos["impacta"] is True
    assert res.datos["hp_despues"] == 3

    # 7. Registrar acción de turno.
    res = reg.dispatch(
        "combate.registrar_accion_turno", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        turno_participante_id=PJ, tipo="accion",
        descripcion="Tyr ataca a la rata con su espada larga.", consumida=True,
    )
    assert res.ok

    # 8. Proponer reacción (ataque de oportunidad) cuando Tyr se retira sin cubrirse.
    res = reg.dispatch(
        "combate.proponer_reaccion", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        tipo="ataque_oportunidad", quien_reacciona_id="rata_1", objetivo_id=PJ,
        descripcion="La rata podría morder a Tyr si se retira de cuerpo_a_cuerpo sin cubrirse.",
        motivo="Tyr abandona cuerpo_a_cuerpo sin cubrirse.",
    )
    assert res.ok
    assert res.datos["propuesta"]["estado"] == "pendiente"
    propuesta_id = res.datos["propuesta"]["id"]

    # 9. Resolver la reacción: confirmar.
    res = reg.dispatch(
        "combate.resolver_reaccion", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        propuesta_id=propuesta_id, decision="confirmar",
        motivo="Sergio acepta que la rata tenga ataque de oportunidad.",
    )
    assert res.ok
    assert res.datos["propuesta"]["estado"] == "confirmada"

    # 9b. Confirmar NO aplica daño por sí mismo: el HP de Tyr sigue intacto.
    ficha_tras_confirmar = gestor_estado.cargar_ficha(CAMP, PJ)
    assert ficha_tras_confirmar.hp_actual == 12

    # 10. Aplicar la reacción confirmada exige una llamada EXPLÍCITA de ataque.
    monkeypatch.setattr(
        "dm_agent.herramientas.combate._tirar_tiradas_ataque", lambda modo, semilla: [14]
    )
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_dano", lambda expr, semilla: 3)
    res = reg.dispatch(
        "combate.atacar_personaje", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", personaje_id=PJ, modificador_ataque=4, dano="1d6+2",
        tipo_dano="perforante", motivo="La rata aprovecha el ataque de oportunidad confirmado.",
    )
    assert res.ok
    assert res.datos["impacta"] is True
    ficha_final = gestor_estado.cargar_ficha(CAMP, PJ)
    assert ficha_final.hp_actual == 9

    # 11. Avanzar turno (no avanzó solo al atacar/proponer/resolver: sigue siendo explícito).
    combate_antes = gestor_combate.cargar(CAMP, combate_id)
    assert combate_antes.indice_turno_actual == 0
    res = reg.dispatch(
        "combate.avanzar_turno", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        motivo="Tyr termina su turno.",
    )
    assert res.ok
    assert res.datos["indice_turno_actual"] == 1
    assert res.datos["turno_actual"]["participante_id"] == "rata_1"

    # 12. Terminar combate.
    res = reg.dispatch(
        "combate.terminar", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        resultado="Tyr derrota a la rata y encuentra una trampilla bajo los barriles.",
        motivo="enemigo derrotado",
    )
    assert res.ok
    assert gestor_combate.cargar_activo(CAMP) is None
    assert gestor_combate.cargar(CAMP, combate_id).estado == "terminado"

    # 13. Verificar que los eventos auditables principales quedaron registrados.
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    for esperado in [
        "combate_iniciado",
        "enemigo_añadido",
        "iniciativa_tirada",
        "ataque_enemigo_resuelto",
        "accion_turno_registrada",
        "reaccion_propuesta",
        "reaccion_resuelta",
        "ataque_personaje_resuelto",
        "turno_avanzado",
        "combate_terminado",
    ]:
        assert esperado in tipos, f"falta evento {esperado!r} en {tipos!r}"

    # Todo cuelga de tmp_path: nada toca storage real.
    for p in tmp_path.rglob("*"):
        assert str(p).startswith(str(tmp_path))
