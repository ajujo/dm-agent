"""Tests de resolución de ataques contra CA (F5.3) y ventaja/desventaja (F5.4).

Usan tmp_path; sin red. Las tiradas se mockean a través de
`_tirar_tiradas_ataque` (devuelve la lista de tiradas brutas, 1 o 2 según
modo_tirada) y `_tirar_dano`, para que el resultado sea determinista sin
depender de valores concretos del motor de dados. El total de ataque se
calcula de verdad (`tirada_elegida + modificador_ataque +
modificador_situacional`), así que los valores de tirada en cada test están
elegidos para producir el escenario deseado dado el modificador por defecto.
"""

import pytest

from dm_agent.esquemas.ficha import Ficha
from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.combate import crear_tools_combate
from dm_agent.herramientas.registro import RegistroHerramientas

CAMP = "campana_demo"

_ENEMIGO_RATA = {"id": "rata_1", "nombre": "Rata gigante", "hp_max": 7, "hp_actual": 7, "ca": 12}


def _ficha_dict(personaje_id="pj_tyr", hp_actual=20, hp_max=20, ca=14):
    return {
        "id": personaje_id,
        "nombre": "Tyr",
        "clase": "Guerrero",
        "nivel": 2,
        "raza": "Humano",
        "atributos": {
            "fuerza": 16, "destreza": 12, "constitucion": 14,
            "inteligencia": 10, "sabiduria": 11, "carisma": 8,
        },
        "hp_max": hp_max,
        "hp_actual": hp_actual,
        "ca": ca,
        "bonificador_competencia": 2,
    }


@pytest.fixture
def entorno(tmp_path):
    gestor = GestorCombateNarrativo(tmp_path)
    eventos = RegistroEventosEstado(tmp_path)
    gestor_estado = GestorEstado(tmp_path)
    reg = RegistroHerramientas()
    for tool in crear_tools_combate(gestor, eventos, gestor_estado):
        reg.registrar(tool)
    return reg, gestor, eventos, gestor_estado


def _iniciar(reg, **kwargs):
    args = {
        "campaña_id": CAMP,
        "personaje_id": "pj_tyr",
        "enemigos": [_ENEMIGO_RATA],
    }
    args.update(kwargs)
    return reg.dispatch("combate.iniciar", ctx=None, **args)


def _crear_ficha(gestor_estado, **kwargs):
    gestor_estado.guardar_ficha(CAMP, Ficha.model_validate(_ficha_dict(**kwargs)))


def _mock_tiradas(monkeypatch, *valores):
    """Fija las tiradas brutas devueltas por `_tirar_tiradas_ataque` (ignora modo/semilla)."""
    monkeypatch.setattr(
        "dm_agent.herramientas.combate._tirar_tiradas_ataque",
        lambda modo, semilla: list(valores),
    )


def _mock_dano(monkeypatch, valor):
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_dano", lambda expr, semilla: valor)


def _atacar_enemigo(reg, combate_id, **kwargs):
    args = {
        "campaña_id": CAMP,
        "combate_id": combate_id,
        "atacante_id": "pj_tyr",
        "enemigo_id": "rata_1",
        "modificador_ataque": 5,
        "dano": "1d8+3",
    }
    args.update(kwargs)
    return reg.dispatch("combate.atacar_enemigo", ctx=None, **args)


def _atacar_personaje(reg, combate_id, **kwargs):
    args = {
        "campaña_id": CAMP,
        "combate_id": combate_id,
        "enemigo_id": "rata_1",
        "personaje_id": "pj_tyr",
        "modificador_ataque": 4,
        "dano": "1d6+2",
    }
    args.update(kwargs)
    return reg.dispatch("combate.atacar_personaje", ctx=None, **args)


# --- ataque a enemigo (F5.3, comportamiento base sin campos nuevos) -----------------------


def test_ataque_enemigo_impacta_si_total_mayor_igual_ca(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)  # mod=5 -> total=15 >= ca=12
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["impacta"] is True


def test_ataque_enemigo_falla_si_total_menor_que_ca(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 3)  # mod=5 -> total=8 < ca=12
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["impacta"] is False
    assert res.datos["hp_despues"] == res.datos["hp_antes"]


# --- F6.5-E: señal todos_los_enemigos_derrotados / deberia_terminar_combate ---------------


def test_ataque_que_derrota_al_unico_enemigo_señala_todos_derrotados(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)  # impacta
    _mock_dano(monkeypatch, 7)  # hp_max=7 -> hp_despues=0

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["hp_despues"] == 0
    assert res.datos["estado"] == "derrotado"
    assert res.datos["todos_los_enemigos_derrotados"] is True
    assert res.datos["deberia_terminar_combate"] is True


def test_ataque_que_no_derrota_al_ultimo_enemigo_no_señala_todos_derrotados(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)  # impacta
    _mock_dano(monkeypatch, 2)  # hp_max=7 -> hp_despues=5, sigue activo

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["hp_despues"] == 5
    assert res.datos["todos_los_enemigos_derrotados"] is False
    assert res.datos["deberia_terminar_combate"] is False


def test_ataque_con_otro_enemigo_activo_no_señala_todos_derrotados(entorno, monkeypatch):
    reg, _, _, _ = entorno
    rata_2 = {**_ENEMIGO_RATA, "id": "rata_2", "nombre": "Rata gigante 2"}
    combate_id = _iniciar(reg, enemigos=[_ENEMIGO_RATA, rata_2]).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)
    _mock_dano(monkeypatch, 7)  # derrota a rata_1; rata_2 sigue activa

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["estado"] == "derrotado"
    assert res.datos["todos_los_enemigos_derrotados"] is False
    assert res.datos["deberia_terminar_combate"] is False


def test_ataque_no_rompe_campos_existentes_del_resultado(entorno, monkeypatch):
    """No regresión: los campos de F5.3/F5.4 siguen presentes junto a los
    nuevos de F6.5-E."""
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    campos_previos = [
        "impacta", "critico", "pifia", "dano", "tipo_dano",
        "hp_antes", "hp_despues", "estado", "combate",
    ]
    for campo in campos_previos:
        assert campo in res.datos
    assert "todos_los_enemigos_derrotados" in res.datos
    assert "deberia_terminar_combate" in res.datos


def test_ataque_enemigo_natural_1_falla_aunque_total_alcance_ca(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 1)  # natural 1; modificador_ataque alto fuerza total >= ca=12
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modificador_ataque=15)
    assert res.ok
    assert res.datos["total_ataque"] >= res.datos["ca_objetivo"]
    assert res.datos["pifia"] is True
    assert res.datos["impacta"] is False


def test_ataque_enemigo_natural_20_impacta_aunque_total_no_alcance_ca(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 20)  # natural 20; modificador_ataque negativo deja total < ca=12
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modificador_ataque=-15)
    assert res.ok
    assert res.datos["total_ataque"] < res.datos["ca_objetivo"]
    assert res.datos["critico"] is True
    assert res.datos["impacta"] is True


def test_ataque_enemigo_aplica_dano_si_impacta(entorno, monkeypatch):
    reg, gestor, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.datos["hp_antes"] == 7
    assert res.datos["hp_despues"] == 3
    combate = gestor.cargar(CAMP, combate_id)
    assert combate.enemigos[0].hp_actual == 3


def test_ataque_enemigo_no_aplica_dano_si_falla(entorno, monkeypatch):
    reg, gestor, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 3)
    _mock_dano(monkeypatch, 4)

    _atacar_enemigo(reg, combate_id)
    combate = gestor.cargar(CAMP, combate_id)
    assert combate.enemigos[0].hp_actual == 7


def test_ataque_enemigo_no_baja_hp_por_debajo_de_cero(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)
    _mock_dano(monkeypatch, 999)

    res = _atacar_enemigo(reg, combate_id)
    assert res.datos["hp_despues"] == 0


def test_ataque_enemigo_actualiza_estado_a_derrotado(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)
    _mock_dano(monkeypatch, 7)

    res = _atacar_enemigo(reg, combate_id)
    assert res.datos["hp_despues"] == 0
    assert res.datos["estado"] == "derrotado"


def test_ataque_enemigo_no_avanza_turno(entorno, monkeypatch):
    reg, gestor, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: 15)
    reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        personaje={"id": "pj_tyr"},
    )
    indice_antes = gestor.cargar(CAMP, combate_id).indice_turno_actual

    _mock_tiradas(monkeypatch, 10)
    _mock_dano(monkeypatch, 4)
    _atacar_enemigo(reg, combate_id)

    assert gestor.cargar(CAMP, combate_id).indice_turno_actual == indice_antes


def test_ataque_enemigo_registra_evento(entorno, monkeypatch):
    reg, _, eventos, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)
    _mock_dano(monkeypatch, 4)

    _atacar_enemigo(reg, combate_id)
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    assert "ataque_enemigo_resuelto" in tipos


def test_ataque_enemigo_sin_campos_nuevos_mantiene_comportamiento_f53(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id)
    assert res.ok
    assert res.datos["modo_tirada"] == "normal"
    assert res.datos["tiradas_d20"] == [10]
    assert res.datos["tirada_d20"] == 10
    assert res.datos["modificador_situacional"] == 0
    assert res.datos["motivo_modificador"] is None
    assert res.datos["total_ataque"] == 15
    assert res.datos["impacta"] is True


# --- ataque a personaje (F5.3, comportamiento base) ---------------------------------------


def test_ataque_personaje_impacta_contra_ca_de_ficha(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 12)  # mod=4 -> total=16 >= ca=14
    _mock_dano(monkeypatch, 3)

    res = _atacar_personaje(reg, combate_id)
    assert res.ok
    assert res.datos["impacta"] is True


def test_ataque_personaje_falla_contra_ca_de_ficha(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 5)  # mod=4 -> total=9 < ca=14
    _mock_dano(monkeypatch, 3)

    res = _atacar_personaje(reg, combate_id)
    assert res.ok
    assert res.datos["impacta"] is False


def test_ataque_personaje_aplica_dano_a_ficha_si_impacta(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, hp_actual=20, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 12)
    _mock_dano(monkeypatch, 5)

    res = _atacar_personaje(reg, combate_id)
    assert res.datos["hp_antes"] == 20
    assert res.datos["hp_despues"] == 15
    ficha = gestor_estado.cargar_ficha(CAMP, "pj_tyr")
    assert ficha.hp_actual == 15


def test_ataque_personaje_no_modifica_ficha_si_falla(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, hp_actual=20, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 5)
    _mock_dano(monkeypatch, 5)

    _atacar_personaje(reg, combate_id)
    ficha = gestor_estado.cargar_ficha(CAMP, "pj_tyr")
    assert ficha.hp_actual == 20


def test_ataque_personaje_devuelve_estado_vital(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, hp_actual=20, hp_max=20, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 12)
    _mock_dano(monkeypatch, 18)

    res = _atacar_personaje(reg, combate_id)
    assert res.datos["hp_despues"] == 2
    assert res.datos["estado_vital"] == "critico"


def test_ataque_personaje_no_avanza_turno(entorno, monkeypatch):
    reg, gestor, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    monkeypatch.setattr("dm_agent.herramientas.combate._tirar_d20", lambda mod, semilla: 15)
    reg.dispatch(
        "combate.tirar_iniciativa", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        personaje={"id": "pj_tyr"},
    )
    indice_antes = gestor.cargar(CAMP, combate_id).indice_turno_actual

    _mock_tiradas(monkeypatch, 12)
    _mock_dano(monkeypatch, 3)
    _atacar_personaje(reg, combate_id)

    assert gestor.cargar(CAMP, combate_id).indice_turno_actual == indice_antes


def test_ataque_personaje_registra_un_solo_evento(entorno, monkeypatch):
    reg, _, eventos, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 12)
    _mock_dano(monkeypatch, 3)

    _atacar_personaje(reg, combate_id)
    tipos = [e.tipo for e in eventos.listar(CAMP)]
    # solo ataque_personaje_resuelto: NO se llama a hp_xp.aplicar_daño (sin doble evento).
    assert tipos.count("ataque_personaje_resuelto") == 1
    assert "daño_aplicado" not in tipos


# --- ventaja / desventaja / modificador situacional (F5.4) --------------------------------


def test_ataque_normal_usa_una_sola_tirada(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 12)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modo_tirada="normal")
    assert res.ok
    assert res.datos["tiradas_d20"] == [12]
    assert res.datos["tirada_d20"] == 12


def test_ataque_con_ventaja_usa_dos_tiradas_y_elige_la_mayor(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 7, 16)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modo_tirada="ventaja")
    assert res.ok
    assert res.datos["tiradas_d20"] == [7, 16]
    assert res.datos["tirada_d20"] == 16


def test_ataque_con_desventaja_usa_dos_tiradas_y_elige_la_menor(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 18, 5)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modo_tirada="desventaja")
    assert res.ok
    assert res.datos["tiradas_d20"] == [18, 5]
    assert res.datos["tirada_d20"] == 5


def test_ventaja_con_1_y_20_produce_critico(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 1, 20)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modo_tirada="ventaja")
    assert res.datos["tirada_d20"] == 20
    assert res.datos["critico"] is True
    assert res.datos["impacta"] is True


def test_desventaja_con_1_y_20_produce_pifia(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 1, 20)
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modo_tirada="desventaja")
    assert res.datos["tirada_d20"] == 1
    assert res.datos["pifia"] is True
    assert res.datos["impacta"] is False


def test_modificador_situacional_suma_al_total(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 5)  # mod=5 -> sin situacional total=10 < ca=12
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modificador_situacional=5)
    assert res.datos["total_ataque"] == 15  # 5 + 5 + 5
    assert res.datos["impacta"] is True


def test_modificador_situacional_negativo_resta_al_total(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 10)  # mod=5 -> sin situacional total=15 >= ca=12
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modificador_situacional=-5)
    assert res.datos["total_ataque"] == 10  # 10 + 5 - 5
    assert res.datos["impacta"] is False


def test_modo_tirada_invalido_devuelve_error_controlado(entorno):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    res = _atacar_enemigo(reg, combate_id, modo_tirada="super_ventaja")
    assert res.ok is False
    assert res.errores


def test_modificador_situacional_fuera_de_rango_devuelve_error_controlado(entorno):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]

    res = _atacar_enemigo(reg, combate_id, modificador_situacional=11)
    assert res.ok is False
    assert res.errores


def test_eventos_incluyen_modo_tirada_y_tiradas_d20(entorno, monkeypatch):
    reg, _, eventos, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 7, 16)
    _mock_dano(monkeypatch, 4)

    _atacar_enemigo(
        reg, combate_id, modo_tirada="ventaja", motivo_modificador="Tyr ve una abertura",
    )
    evento = next(e for e in eventos.listar(CAMP) if e.tipo == "ataque_enemigo_resuelto")
    assert evento.datos["modo_tirada"] == "ventaja"
    assert evento.datos["tiradas_d20"] == [7, 16]
    assert evento.datos["tirada_d20"] == 16
    assert evento.datos["modificador_situacional"] == 0
    assert evento.datos["motivo_modificador"] == "Tyr ve una abertura"


def test_ataque_enemigo_con_ventaja_aplica_dano_si_impacta(entorno, monkeypatch):
    reg, gestor, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 3, 14)  # elegido 14; mod=5 -> total=19 >= ca=12
    _mock_dano(monkeypatch, 4)

    res = _atacar_enemigo(reg, combate_id, modo_tirada="ventaja")
    assert res.datos["impacta"] is True
    assert res.datos["hp_despues"] == 3
    combate = gestor.cargar(CAMP, combate_id)
    assert combate.enemigos[0].hp_actual == 3


def test_ataque_personaje_con_desventaja_falla_si_corresponde(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, hp_actual=20, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 15, 2)  # elegido 2; mod=4 -> total=6 < ca=14
    _mock_dano(monkeypatch, 5)

    res = _atacar_personaje(reg, combate_id, modo_tirada="desventaja")
    assert res.datos["impacta"] is False
    ficha = gestor_estado.cargar_ficha(CAMP, "pj_tyr")
    assert ficha.hp_actual == 20


# --- dispatch_api / esquemas ----------------------------------------------------------


def test_dispatch_api_atacar_enemigo_acepta_campos_nuevos(entorno, monkeypatch):
    reg, _, _, _ = entorno
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 7, 16)
    _mock_dano(monkeypatch, 4)

    res = reg.dispatch_api(
        "combate_atacar_enemigo", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        atacante_id="pj_tyr", enemigo_id="rata_1", modificador_ataque=5, dano="1d8+3",
        modo_tirada="ventaja", modificador_situacional=2, motivo_modificador="ventaja narrativa",
    )
    assert res.ok
    assert res.datos["modo_tirada"] == "ventaja"
    assert res.datos["tiradas_d20"] == [7, 16]
    assert res.datos["modificador_situacional"] == 2


def test_dispatch_api_atacar_personaje_acepta_campos_nuevos(entorno, monkeypatch):
    reg, _, _, gestor_estado = entorno
    _crear_ficha(gestor_estado, ca=14)
    combate_id = _iniciar(reg).datos["combate"]["id"]
    _mock_tiradas(monkeypatch, 15, 2)
    _mock_dano(monkeypatch, 3)

    res = reg.dispatch_api(
        "combate_atacar_personaje", ctx=None, campaña_id=CAMP, combate_id=combate_id,
        enemigo_id="rata_1", personaje_id="pj_tyr", modificador_ataque=4, dano="1d6+2",
        modo_tirada="desventaja", modificador_situacional=-2, motivo_modificador="desventaja narrativa",
    )
    assert res.ok
    assert res.datos["modo_tirada"] == "desventaja"
    assert res.datos["tiradas_d20"] == [15, 2]
    assert res.datos["modificador_situacional"] == -2


def test_esquemas_disponibles_contienen_tools_ataque(entorno):
    reg, _, _, _ = entorno
    nombres = {e["function"]["name"] for e in reg.esquemas_disponibles(ctx=None)}
    assert {"combate_atacar_enemigo", "combate_atacar_personaje"} <= nombres
