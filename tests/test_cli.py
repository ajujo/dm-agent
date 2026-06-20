"""Tests de la CLI / REPL (`dm_agent.cli`, `dm_agent.nucleo.bucle`)."""

from types import SimpleNamespace

import pytest

from dm_agent.cli import main
from dm_agent.esquemas.combate import CombateNarrativo, EnemigoCombate, PropuestaReaccion
from dm_agent.esquemas.ficha import Ficha
from dm_agent.estado.combate import GestorCombateNarrativo
from dm_agent.estado.eventos import RegistroEventosEstado
from dm_agent.estado.gestor import GestorEstado
from dm_agent.herramientas.base import ResultadoHerramienta
from dm_agent.herramientas.combate import crear_tools_combate
from dm_agent.herramientas.ficha import crear_tools_ficha
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


def test_repl_salir_con_espacios_iniciales_termina():
    ctx = SimpleNamespace()  # /salir no toca ctx
    code, salidas = _repl_con_inputs(ctx, ["   /salir"])

    assert code == 0
    assert any("Hasta la próxima" in s for s in salidas)


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

    _dispatch_y_formatear = SesionInteractiva._dispatch_y_formatear
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


# --- F6.5-C: comandos cómodos /combate /turno /reacciones /ficha /estado ---

CAMP_COMANDOS = "campana_tyr"


class _CtxFakeComandos:
    """Objeto mínimo que reutiliza los métodos reales de `SesionInteractiva`
    sin construir la sesión completa (config/perfiles/LLM)."""

    _dispatch_y_formatear = SesionInteractiva._dispatch_y_formatear
    _combate_activo = SesionInteractiva._combate_activo
    comando_combate = SesionInteractiva.comando_combate
    comando_turno = SesionInteractiva.comando_turno
    comando_reacciones = SesionInteractiva.comando_reacciones
    comando_ficha = SesionInteractiva.comando_ficha
    comando_estado = SesionInteractiva.comando_estado

    def __init__(self, registro, combate, campaña_id, sesion=None):
        self.registro = registro
        self.combate = combate
        self.campaña_id = campaña_id
        self.sesion = sesion


def _ficha_dict(personaje_id="tyr", hp_actual=1, hp_max=12, ca=16):
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


def _entorno_comandos(tmp_path):
    raiz = tmp_path / "storage"
    gestor_combate = GestorCombateNarrativo(raiz)
    eventos = RegistroEventosEstado(raiz)
    gestor_estado = GestorEstado(raiz)
    registro = RegistroHerramientas()
    for tool in crear_tools_combate(gestor_combate, eventos, gestor_estado):
        registro.registrar(tool)
    for tool in crear_tools_ficha(gestor_estado):
        registro.registrar(tool)
    sesion = Sesion.crear(tmp_path / "sesiones", id="s-comandos")
    ctx = _CtxFakeComandos(registro, gestor_combate, CAMP_COMANDOS, sesion)
    return ctx, gestor_combate, gestor_estado


def _combate_activo_dict(**kwargs):
    base = {"id": "combate_aa6049b2", "campaña_id": CAMP_COMANDOS, "personaje_id": "tyr"}
    base.update(kwargs)
    return CombateNarrativo(**base)


def test_comando_combate_usa_combate_activo(tmp_path):
    ctx, gestor_combate, _ = _entorno_comandos(tmp_path)
    combate = _combate_activo_dict()
    gestor_combate.guardar(combate)
    gestor_combate.marcar_activo(combate)

    salida = ctx.comando_combate()
    assert "[comando] combate_estado -> ok=True" in salida
    assert "combate_aa6049b2" in salida


def test_comando_combate_sin_combate_activo(tmp_path):
    ctx, _, _ = _entorno_comandos(tmp_path)
    assert ctx.comando_combate() == "[comando] No hay combate activo detectado."


def test_comando_turno_usa_combate_activo(tmp_path):
    ctx, gestor_combate, _ = _entorno_comandos(tmp_path)
    combate = _combate_activo_dict(
        orden_iniciativa=[
            {"participante_id": "tyr", "nombre": "Tyr", "tipo": "personaje", "iniciativa": 15, "es_personaje": True},
            {"participante_id": "rata_1", "nombre": "Rata", "tipo": "enemigo", "iniciativa": 8},
        ],
    )
    gestor_combate.guardar(combate)
    gestor_combate.marcar_activo(combate)

    salida = ctx.comando_turno()
    assert "[comando] combate_turno_actual -> ok=True" in salida
    assert "tyr" in salida


def test_comando_turno_sin_combate_activo(tmp_path):
    ctx, _, _ = _entorno_comandos(tmp_path)
    assert ctx.comando_turno() == "[comando] No hay combate activo detectado."


def test_comando_reacciones_usa_combate_activo(tmp_path):
    ctx, gestor_combate, _ = _entorno_comandos(tmp_path)
    combate = _combate_activo_dict(
        propuestas_reaccion=[
            PropuestaReaccion(
                id="reaccion_f8b95457", combate_id="combate_aa6049b2", ronda=1,
                tipo="ataque_oportunidad", quien_reacciona_id="rata_1", objetivo_id="tyr",
            )
        ]
    )
    gestor_combate.guardar(combate)
    gestor_combate.marcar_activo(combate)

    salida = ctx.comando_reacciones()
    assert "[comando] combate_listar_reacciones -> ok=True" in salida
    assert "reaccion_f8b95457" in salida


def test_comando_reacciones_sin_combate_activo(tmp_path):
    ctx, _, _ = _entorno_comandos(tmp_path)
    assert ctx.comando_reacciones() == "[comando] No hay combate activo detectado."


def test_comando_ficha_usa_personaje_activo(tmp_path):
    ctx, gestor_combate, gestor_estado = _entorno_comandos(tmp_path)
    gestor_estado.guardar_ficha(CAMP_COMANDOS, Ficha.model_validate(_ficha_dict()))
    combate = _combate_activo_dict()
    gestor_combate.guardar(combate)
    gestor_combate.marcar_activo(combate)

    salida = ctx.comando_ficha()
    assert "[comando] ficha_leer -> ok=True" in salida
    assert "tyr" in salida


def test_comando_ficha_sin_personaje_activo(tmp_path):
    ctx, _, _ = _entorno_comandos(tmp_path)
    assert ctx.comando_ficha() == "[comando] No se conoce personaje activo. Usa /tool ficha_leer {...}"


def test_comando_estado_resumen_compacto(tmp_path):
    ctx, gestor_combate, gestor_estado = _entorno_comandos(tmp_path)
    gestor_estado.guardar_ficha(CAMP_COMANDOS, Ficha.model_validate(_ficha_dict(hp_actual=1, hp_max=12, ca=16)))
    combate = _combate_activo_dict(
        ronda=3,
        enemigos=[
            EnemigoCombate(id="rata_1", nombre="Rata 1", hp_max=5, hp_actual=0, ca=12, estado="derrotado"),
            EnemigoCombate(id="rata_2", nombre="Rata 2", hp_max=5, hp_actual=0, ca=12, estado="derrotado"),
        ],
    )
    gestor_combate.guardar(combate)
    gestor_combate.marcar_activo(combate)

    salida = ctx.comando_estado()
    assert salida.startswith("[estado]")
    assert "Campaña: campana_tyr" in salida
    assert "Tyr (tyr)" in salida and "HP 1/12" in salida and "CA 16" in salida
    assert "Combate: combate_aa6049b2" in salida
    assert "Ronda: 3" in salida
    assert "rata_1: derrotado, 0/5 HP" in salida
    assert "rata_2: derrotado, 0/5 HP" in salida
    assert "Reacciones pendientes: 0" in salida
    # Legible, no JSON bruto.
    assert '"ficha"' not in salida


def test_comando_estado_sin_combate_activo_no_rompe(tmp_path):
    ctx, _, _ = _entorno_comandos(tmp_path)
    salida = ctx.comando_estado()
    assert salida.startswith("[estado]")
    assert "Personaje: desconocido" in salida
    assert "sin combate activo detectado" in salida


def test_comandos_comodos_aparecen_en_ayuda():
    for cmd in ["/combate", "/turno", "/reacciones", "/ficha", "/estado"]:
        assert cmd in COMANDOS
        assert cmd in _texto_ayuda()


def test_comandos_comodos_no_llaman_al_llm(tmp_path):
    """Los comandos cómodos solo usan `registro`/`combate`/`sesion`: si
    alguno intentara llamar al LLM (self.cliente/self.agente), fallaría con
    AttributeError porque `_CtxFakeComandos` no tiene esos atributos."""
    ctx, gestor_combate, gestor_estado = _entorno_comandos(tmp_path)
    gestor_estado.guardar_ficha(CAMP_COMANDOS, Ficha.model_validate(_ficha_dict()))
    combate = _combate_activo_dict()
    gestor_combate.guardar(combate)
    gestor_combate.marcar_activo(combate)

    assert ctx.comando_combate()
    assert ctx.comando_turno()
    assert ctx.comando_reacciones()
    assert ctx.comando_ficha()
    assert ctx.comando_estado()


def test_repl_enruta_comandos_comodos_sin_tocar_procesar():
    llamadas_procesar = []
    ctx = SimpleNamespace(
        procesar=lambda t: llamadas_procesar.append(t) or "no debería llamarse",
        comando_combate=lambda: "[comando] combate ok",
        comando_turno=lambda: "[comando] turno ok",
        comando_reacciones=lambda: "[comando] reacciones ok",
        comando_ficha=lambda: "[comando] ficha ok",
        comando_estado=lambda: "[estado] ok",
    )
    code, salidas = _repl_con_inputs(
        ctx, ["/combate", "/turno", "/reacciones", "/ficha", "/estado", "/salir"]
    )

    assert code == 0
    assert llamadas_procesar == []
    assert "[comando] combate ok" in salidas
    assert "[comando] turno ok" in salidas
    assert "[comando] reacciones ok" in salidas
    assert "[comando] ficha ok" in salidas
    assert "[estado] ok" in salidas
