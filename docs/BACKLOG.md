# Backlog inicial

Cada issue: contexto → tareas → archivos → criterios de aceptación → tests → dependencias → prioridad.

---

## F1 — Esqueleto

### #F1-01 — Crear `pyproject.toml` + esqueleto instalable
- **Contexto.** Necesitamos un paquete instalable en `conda env rpg` para que todos los demás issues funcionen.
- **Tareas.** Definir metadata, deps mínimas (`pyyaml`, `requests`, `rich`, `pydantic`, `pytest`), entry point `dm-agent`.
- **Archivos.** `pyproject.toml`, `src/dm_agent/__init__.py`.
- **Aceptación.** `pip install -e .` exitoso; `dm-agent --version` imprime versión.
- **Tests.** `tests/test_smoke.py` importa el paquete.
- **Dep.** —
- **Prioridad.** P0.

### #F1-02 — Configs iniciales
- **Tareas.** Crear `config/{proyecto,modelos,perfiles}.json`.
- **Aceptación.** Los archivos validan con `json.load` y siguen esquema documentado.
- **Tests.** `tests/test_config.py`.
- **Dep.** #F1-01.
- **P.** P0.

### #F1-03 — `Herramienta` base + `RegistroHerramientas`
- **Tareas.** Implementar Protocol `Herramienta`, dataclass `ResultadoHerramienta`, registro con `register/dispatch/list_schemas`.
- **Archivos.** `src/dm_agent/herramientas/base.py`, `registro.py`.
- **Aceptación.** Registrar + dispatchar tool dummy.
- **Tests.** `tests/test_registro.py`.
- **Dep.** #F1-01.
- **P.** P0.

### #F1-04 — Tool `dados.tirar`
- **Tareas.** Portar `motor/dados.py` de dnd5e (`tirar`, `tirar_ventaja`, `tirar_desventaja`, semilla).
- **Archivos.** `src/dm_agent/herramientas/dados.py`.
- **Aceptación.** Mismas firmas y resultados que el original.
- **Tests.** `tests/test_dados.py` con semilla fija.
- **Dep.** #F1-03.
- **P.** P0.

### #F1-05 — `CargadorSkills` mínimo
- **Tareas.** Escanear `skills/**/SKILL.md`, parsear frontmatter YAML, devolver lista de `SkillMeta`.
- **Aceptación.** Detecta `skills/ejemplo-escena-social/SKILL.md` con todos sus campos.
- **Tests.** `tests/test_skills_loader.py`.
- **Dep.** #F1-01.
- **P.** P0.

### #F1-06 — `AGENTS.md` operacional
- **Tareas.** Escribir guía para agentes pequeños (entorno, rutas, prohibiciones, cómo añadir tool/skill).
- **Aceptación.** Lectura de 10 min basta para un agente nuevo.
- **Dep.** —
- **P.** P0.

### #F1-07 — `README.md`
- **Tareas.** Visión, instalación, primera ejecución, link a docs.
- **Dep.** —
- **P.** P0.

---

## F2 — Núcleo CLI jugable mínimo

### #F2-01 — Cliente LLM OpenAI-compatible (sync + streaming) — ✅ PARCIAL (F2.1)
- **Aceptación.** Soporta `chat/completions` con `tools`, parametrizable por perfil.
- **Estado.** Sync **hecho** (`src/dm_agent/llm/cliente.py`, `ClienteLLM`): carga de config, resolución de perfil/endpoint, `chat()` con/sin tools, parseo de `tool_calls` sin ejecutarlas, API key opcional vía env, errores tipados. **Streaming pendiente** (`stream=True` → `NotImplementedError`); se completará junto a F2.2.
- **Tests.** `tests/test_cliente_llm.py` con `httpx.MockTransport` (sin red). Smoke opcional: `scripts/check_llm_mock.py`.
- **P.** P0.

### #F2-02 — Bucle del agente — ✅ HECHO (F2.2)
- **Aceptación.** Conversación user↔LLM con system prompt.
- **Estado.** `src/dm_agent/nucleo/agente.py` (`AgenteDM`). Incluye round-trip de tool calls (solo `dados_tirar` ejecutable; tool desconocida → error controlado reinyectado) y protección `max_iter_turno`. System prompt mínimo en `src/dm_agent/prompts/system_dm_minimo.md`. Tests: `tests/test_agente_minimo.py`.
- **Dep.** #F2-01.
- **P.** P0.

### #F2-03 — Persistencia de sesión JSONL — ✅ HECHO (F2.2)
- **Estado.** `src/dm_agent/persistencia/sesion.py` (`Sesion`): JSONL append-only, crear/cargar/continuar/última, registros user/assistant/tool_call/tool_result. Tests: `tests/test_sesion_jsonl.py`.
- **P.** P0.

### #F2-04 — CLI REPL (`dm-agent`) — ✅ HECHO (F2.2)
- **Comandos.** `/ayuda /salir /guardar /continuar /nueva /debug`. Flags: `--perfil --nueva --continuar --debug`. Error claro (sin traceback) si el perfil/endpoint no es válido.
- **Estado.** `src/dm_agent/cli.py` + `src/dm_agent/nucleo/bucle.py`. Tests: `tests/test_cli.py`. *(`/cargar` y `--perfil` por sesión guardada quedan para más adelante.)*
- **P.** P0.

---

## F3 — Tools deterministas

### #F3-00 — Esquemas base (`Ficha`, `EstadoPartida`, `Evento`) — ✅ HECHO (F3.1)
- **Estado.** `src/dm_agent/esquemas/{ficha,estado,evento,comun}.py` (pydantic v2, `version_schema=1`, validaciones explícitas). Docs en `docs/esquemas/`. Tests: `tests/test_esquemas_f3.py`. Sin tools ni gestor de estado todavía.
### #F3-00b — GestorEstado JSON + snapshots — ✅ HECHO (F3.2)
- **Estado.** `src/dm_agent/estado/gestor.py` (`GestorEstado`): guardar/cargar `Ficha` y `EstadoPartida`, listar fichas, escritura atómica (tmp+replace), snapshots opcionales, errores tipados (`ErrorEstado{,NoEncontrado,Invalido}`). Docs: `docs/estado/gestor_estado.md`. Tests: `tests/test_gestor_estado.py`.
### #F3-01 — Tools `ficha.*` (sobre esquema `Ficha`) — ✅ HECHO (F3.3)
- **Estado.** `src/dm_agent/herramientas/ficha.py`: `ficha.{leer,guardar,validar,actualizar,listar}` (API `ficha_*`), apoyadas en `GestorEstado` + validación `Ficha`. Registradas en el agente vía `bucle._crear_registro`. Errores controlados (sin tracebacks al LLM). Docs: `docs/tools/ficha.md`. Tests: `tests/test_tools_ficha.py`. Sin HP/XP semántico ni edición profunda.
### #F3-02 — Tools `hp_xp.*` + eventos auditables — ✅ HECHO (F3.4)
- **Estado.** `src/dm_agent/herramientas/hp_xp.py`: `hp_xp.{aplicar_daño,aplicar_curacion,otorgar_xp,consultar_estado_vital}` (API `hp_xp_aplicar_dano`, …; ñ→n transliterada). Cargan/validan/guardan vía `GestorEstado`+`Ficha`; cada escritura registra `Evento` en `eventos.jsonl` (`src/dm_agent/estado/eventos.py`, `RegistroEventosEstado`). Registradas en el agente. Docs: `docs/tools/hp_xp.md`, `docs/estado/eventos.md`. Tests: `tests/test_tools_hp_xp.py`.
### #F3-02b — Unificación del modelo de `Evento` — ✅ HECHO (F3.5)
- **Estado.** Modelo canónico único `esquemas.evento.Evento`; `nucleo.eventos` lo re-exporta y el bus lo publica; `dados.tirar` migrado a `crear_evento` (`semilla` → `datos`). Cierra el bloque de estado mecánico mínimo (ficha + HP/XP + eventos). Tests: `tests/test_eventos_unificados.py`. Docs: `docs/estado/eventos.md`.
### #F3-03 — Tools `inventario.*` — ✅ HECHO (F3.6)
- **Estado.** `src/dm_agent/herramientas/inventario.py`: `inventario.{listar,añadir,quitar,equipar,desequipar}` (API `inventario_listar`/`inventario_anadir`/…; ñ→n). Sobre `Ficha.inventario`; validan/guardan vía `GestorEstado`+`Ficha`; cada mutación registra `Evento` (`objeto_añadido/quitado/equipado/desequipado`). Registradas en el agente. Docs: `docs/tools/inventario.md`. Tests: `tests/test_tools_inventario.py`. Sin peso/oro/slots/equipo complejo.
### #F3-04 — Tools `condiciones.*`
### #F3-05 — Bus de eventos como vía única de persistencia (subscriber) — parcial
- **Estado.** Bus runtime canónico disponible; aún no es la vía única (las tools persisten directo vía `RegistroEventosEstado`). Deuda menor.
### #F3-06 — Validador central de cambios de estado
- **P.** todas P1.

> Nota: F3.2 (GestorEstado JSON + snapshots) se intercala entre los esquemas y las tools.

---

## F4 — Memoria narrativa

### #F4-01 — Esquema de memoria + bitácora narrativa append-only — ✅ HECHO (F4.1)
- **Estado.** `esquemas/narrativa.py` (`EntradaNarrativa`), `memoria/narrativa.py` (`GestorMemoriaNarrativa`: JSONL + `bitacora.md` append-only), tools `narrativa.{registrar,reciente}` (`herramientas/narrativa.py`), registradas en el agente. Docs: `docs/memoria/narrativa.md`, `docs/tools/narrativa.md`. Tests: `tests/test_memoria_narrativa.py`, `tests/test_tools_narrativa.py`.
### #F4-02 — Resumen de escena/sesión con LLM — ✅ HECHO (F4.2)
- **Estado.** `memoria/resumen.py` (`ResumidorNarrativo`: `resumir_texto`/`resumir_entradas`), tools `resumen.{entradas,texto}` (`herramientas/resumen.py`), prompt fijo `prompts/resumen_narrativo.md`. Guardan `EntradaNarrativa(tipo="resumen", importancia=5, origen="resumen")`. Registradas en el agente. Docs: `docs/memoria/resumenes.md`, `docs/tools/resumen.md`. Tests con mock LLM: `tests/test_resumen_memoria.py`, `tests/test_tools_resumen.py`. Sin inyección automática (F4.3).
### #F4-03 — Inyección de memoria narrativa en contexto del agente — ✅ HECHO (F4.3)
- **Estado.** `memoria/contexto.py` (`ConstructorContextoMemoria.construir_bloque_memoria`): último resumen + N entradas recientes no-resumen → bloque Markdown compacto. `AgenteDM` lo inyecta como 2º mensaje `system` (antes del historial/usuario, sin sustituir el base) cuando hay constructor + campaña. Config `memoria` (`inyectar_narrativa`/`limite_entradas_contexto`/`incluir_resumenes`) y `campaña_activa` en `proyecto.json` (defaults seguros; campaña por defecto `campana_demo`). Docs: `docs/memoria/contexto.md`. Tests: `tests/test_contexto_memoria.py`, `tests/test_agente_memoria.py`. No es RAG ni memoria vectorial.
### #F4-04 — Cierre y preparación de sesión — ✅ HECHO (F4.4)
- **Estado.** `memoria/cierre_sesion.py` (`CierreSesionNarrativa.cerrar_sesion`): genera resumen de cierre + preparación de próxima sesión y guarda dos entradas (`resumen` + `siguiente_sesion`) con mismo `campaña_id`/`sesion_id`. Prompt `prompts/cierre_sesion.md` (parseo por encabezados + degradación documentada). Tools `sesion.{cerrar,cerrar_texto}` (`herramientas/sesion.py`); `Sesion.texto_para_resumen()`. Comando REPL `/cerrar`. Docs: `docs/memoria/cierre_sesion.md`, `docs/tools/sesion.md`. Tests: `tests/test_cierre_sesion.py`, `tests/test_tools_sesion.py`.
- **Pendiente:** cierre automático al salir; selector de campaña.
- **P.** P1.
### #F4-05 — Prueba integrada de campaña + guía manual — ✅ HECHO (F4.5)
- **Estado.** Validación extremo a extremo del bucle de continuidad, sin funcionalidad nueva. Test con mock LLM `tests/test_campaña_integrada_f4.py`: ficha → escena narrativa → `inventario.añadir` + `hp_xp.aplicar_daño` → cierre (`resumen` + `siguiente_sesion`) → `AgenteDM` con memoria inyectada antes del mensaje de usuario; todo bajo `tmp_path`, sin red ni `storage/` real. Guía manual real `docs/PRUEBA_MANUAL_F4.md` (endpoint vLLM, ficha vía APIs del proyecto, REPL, escena, memoria, inventario, HP/XP, `/cerrar`, `--continuar`, criterios de aceptación y troubleshooting). Ajuste menor en `memoria/contexto.py`: las entradas recientes inyectan título **y** contenido (antes solo título), para que el punto de arranque de `siguiente_sesion` llegue al modelo.
- **Resultado.** El proyecto tiene una **campaña persistente básica validada** (test integrado mock + guía manual), pero **aún no** tiene combate, RAG, memoria vectorial ni reglas adaptadas.
- **P.** P1.
### #F4-06 — Entidades narrativas estructuradas mínimas — ✅ HECHO (F4.6)
- **Estado.** Esquemas `PNJ`/`Lugar`/`Pista`/`Objetivo`/`FrenteAbierto` (`esquemas/entidades.py`, heredan de `EntidadBase`: `id`/`nombre`/`descripcion`/`estado`/`tags`/`importancia`/`notas`/`version_schema`). `GestorEntidadesNarrativas` (`memoria/entidades.py`): un JSON por tipo y campaña (`entidades/{pnj,lugares,pistas,objetivos,frentes}.json`), escritura atómica, guardar por `id` reemplaza, listar ordena por importancia descendente y luego nombre. Tools `entidad.{guardar,listar}_{pnj,lugar(es),pista(s),objetivo(s),frente(s)}` (`herramientas/entidades.py`), registradas en el agente. `ConstructorContextoMemoria` (F4.3) amplía con `gestor_entidades`/`limite_entidades` opcionales: inyecta `## Entidades importantes` tras la bitácora reciente, solo si hay entidades. Config `memoria.{inyectar_entidades,limite_entidades_contexto}` en `proyecto.json` (defaults seguros). Docs: `docs/memoria/entidades.md`, `docs/tools/entidades.md`. Tests: `tests/test_entidades_narrativas.py`, `tests/test_tools_entidades.py`, `tests/test_contexto_entidades.py`.
- **Decisión técnica.** `RegistroHerramientas.dispatch` tenía su primer parámetro llamado `nombre`, lo que colisionaba con tools que aceptan un argumento `nombre` (las de entidades, primera vez que ocurre). Renombrado a `nombre_herramienta` (siempre se llama posicionalmente, sin impacto en callers existentes).
- **Pendiente:** extracción automática de entidades desde la narración (LLM); relaciones validadas entre entidades; facciones/mapas/quest engine.
- **P.** P1.

---

## F5 — Combate

### #F5-01 — Combate narrativo mínimo — ✅ HECHO (F5.1, distancias revisadas en F5.1.1)
- **Estado.** Esquemas `EnemigoCombate`/`CombateNarrativo` (`esquemas/combate.py`). `GestorCombateNarrativo` (`estado/combate.py`): un JSON por combate (`combates/<combate_id>.json`) + referencia de combate activo por campaña (`combates/activo.json`, solo el `combate_id`, nunca el combate completo). Tools `combate.{iniciar,estado,añadir_enemigo,daño_enemigo,terminar}` (`herramientas/combate.py`), con eventos auditables (`combate_iniciado`, `enemigo_añadido`, `daño_enemigo`, `combate_terminado`) vía `RegistroEventosEstado`. Distancias narrativas (`cuerpo_a_cuerpo`/`corta`/`media`/`larga`/`fuera_de_alcance`, revisadas en F5.1.1 desde `cerca`/`media`/`lejos`/`fuera_de_alcance` para acercarse al vocabulario D&D); sin grid/casillas. El daño al personaje jugador sigue pasando por `hp_xp.aplicar_daño`; sin XP automática. Docs: `docs/estado/combate.md`, `docs/tools/combate.md`, [ADR-0017](../decisiones/0017-dnd55-narrativo-solitario.md). Tests: `tests/test_combate_narrativo.py`, `tests/test_tools_combate.py`.
- **Decisión técnica.** `combate.iniciar` crea el combate ya en estado `activo` directamente (sin paso `preparando` expuesto vía tool en F5.1); `activo.json` guarda solo una referencia por simplicidad y para evitar desincronización con el contenido real del combate. F5.1.1 fue deliberadamente **no** un rename a `conflicto.*`/`participante`: se conserva `combate.*`/`EnemigoCombate` y el vocabulario D&D; solo cambian los valores de `distancia`.
- **Pendiente:** integración con memoria narrativa (sugerir/registrar consecuencia al terminar combate, #F5-07); reacciones/ataques de oportunidad narrativos, flanqueo narrativo (#F5-05, ya hecho como propuesta; cálculo automático sigue en #F5-09).
- **P.** P1.
### #F5-02 — Iniciativa clásica y turnos narrativos — ✅ HECHO (F5.2)
- **Estado.** `1d20 + mod_destreza` para personaje y enemigos (tirada de enemigos automática, D-COMBATE-01/02). Esquema `EntradaIniciativa` y campos `CombateNarrativo.{orden_iniciativa,indice_turno_actual,ronda}`, `EnemigoCombate.{mod_destreza,iniciativa}` (opcionales, sin migración). Tools `combate.{tirar_iniciativa,turno_actual,avanzar_turno}` con eventos `iniciativa_tirada`/`turno_avanzado`. Orden: mayor iniciativa primero, empate personaje > enemigo, empate entre enemigos estable por nombre/id. Reutiliza el motor de dados existente (`herramientas/dados.py`); determinista con `semilla` para tests. Docs: `docs/estado/combate.md`, `docs/tools/combate.md`, [ADR-0018](../decisiones/0018-combate-dnd-narrativo.md). Tests: `tests/test_iniciativa_turnos.py`, ampliación de `tests/test_tools_combate.py`/`tests/test_combate_narrativo.py`.
- **Decisión técnica.** No hay modo heroico/gritty global (D-COMBATE-03): la dificultad depende del encuentro/aventura. Reacciones/ataques de oportunidad quedan como propuesta + confirmación del jugador (D-COMBATE-04), no como mecánica automática — ningún automatismo se implementó en F5.2.
- **Pendiente:** ataques completos con tirada contra CA (#F5-03, ya hecho); propuesta/confirmación de reacciones (#F5-05, ya hecho); aplicar de verdad flanqueo narrativo calculado automáticamente (#F5-09); sorpresa.
- **P.** P1.
### #F5-03 — Ataques básicos contra CA y daño — ✅ HECHO (F5.3)
- **Estado.** `1d20 + modificador_ataque` contra CA: natural 1 falla siempre, natural 20 impacta siempre (daño duplicado en dados, no modificador). Tools `combate.{atacar_enemigo,atacar_personaje}` con eventos `ataque_enemigo_resuelto`/`ataque_personaje_resuelto`. `combate.atacar_enemigo` reutiliza el umbral de estado de `combate.daño_enemigo`; `combate.atacar_personaje` aplica daño directamente sobre `Ficha` vía `GestorEstado`. Nuevo `ResultadoAtaque` (dataclass interno en `herramientas/combate.py`, no persistido). Ninguna de las dos tools avanza turno; `distancia` sigue siendo informativa, no bloquea ataques. Docs: `docs/estado/combate.md`, `docs/tools/combate.md`, [ADR-0018](../decisiones/0018-combate-dnd-narrativo.md). Tests: `tests/test_ataques_combate.py`, ampliación de `tests/test_tools_combate.py`.
- **Decisión técnica.** `combate.atacar_personaje` registra **solo** `ataque_personaje_resuelto` (no llama a `hp_xp.aplicar_daño`) para no duplicar el evento de daño de un mismo ataque. Críticos duplican dados (no modificador) porque resultó limpio de implementar con una transformación de la expresión vía regex antes de tirar. Atacar no avanza turno: sigue siendo decisión explícita del DM vía `combate.avanzar_turno`.
- **Pendiente:** IA enemiga / selección automática de acciones; ventaja/desventaja (#F5-04, ya hecho); reacciones/ataques de oportunidad propuestos (#F5-05, ya hecho)/flanqueo mecánico automático (#F5-09); cobertura, áreas de efecto, resistencias/vulnerabilidades, salvaciones, hechizos.
- **P.** P1.
### #F5-04 — Ventaja/desventaja y modificadores narrativos simples — ✅ HECHO (F5.4)
- **Estado.** `modo_tirada` (`normal`/`ventaja`/`desventaja`) en `combate.{atacar_enemigo,atacar_personaje}`: ventaja/desventaja tiran 2d20 y eligen mayor/menor; natural 1/20 se evalúa sobre la tirada elegida. `modificador_situacional` (-10..10) + `motivo_modificador` (narrativo) se suman al total junto con `modificador_ataque`. Sin estos campos, comportamiento idéntico a F5.3. `ResultadoAtaque` ampliado con `modo_tirada`/`tiradas_d20`/`modificador_situacional`/`motivo_modificador`; eventos `ataque_*_resuelto` incluyen los mismos campos. Docs: `docs/estado/combate.md`, `docs/tools/combate.md`, [ADR-0018](../decisiones/0018-combate-dnd-narrativo.md). Tests: ampliación de `tests/test_ataques_combate.py`/`tests/test_tools_combate.py`.
- **Decisión técnica.** La cancelación de ventaja+desventaja simultáneas es responsabilidad de quien llama a la tool (pasa `modo_tirada="normal"`), no lógica interna: F5.4 no acumula múltiples fuentes de ventaja/desventaja. El helper de dados de F5.3 (`_tirar_ataque_d20`, devolvía natural+total ya calculado) se sustituyó por `_tirar_tiradas_ataque` (solo tiradas brutas) porque ventaja/desventaja necesita decidir qué tirada usar antes de calcular el total; esto rompió el mocking de los tests de F5.3, que se actualizaron para mockear el nuevo helper.
- **Pendiente:** críticos más ricos (rangos de amenaza ampliados, daño extra por clase, #F5-10); acumulación de múltiples ventajas/desventajas si llega a hacer falta; flanqueo/cobertura que conceda ventaja/desventaja automáticamente (#F5-09).
- **P.** P1.
### #F5-05 — Acciones de turno y propuestas de reacción — ✅ HECHO (F5.5)
- **Estado.** Esquemas `AccionTurno` (registro narrativo de qué hizo un participante, `tipo` texto libre, sin validar economía de acciones) y `PropuestaReaccion` (reacción/ataque de oportunidad propuesto; `estado` cerrado `pendiente`/`confirmada`/`rechazada`/`aplicada`/`caducada`). Campos `CombateNarrativo.{acciones_turno,propuestas_reaccion}` (default `[]`, sin migración). Tools `combate.{registrar_accion_turno,proponer_reaccion,resolver_reaccion,listar_reacciones}` con eventos `accion_turno_registrada`/`reaccion_propuesta`/`reaccion_resuelta`. Docs: `docs/estado/combate.md`, `docs/tools/combate.md`, [ADR-0018](../decisiones/0018-combate-dnd-narrativo.md). Tests: `tests/test_reacciones_combate.py`, ampliación de `tests/test_combate_narrativo.py`/`tests/test_tools_combate.py`.
- **Decisión técnica.** Ni `proponer_reaccion` ni `resolver_reaccion` tiran dados ni aplican daño: confirmar solo cambia el `estado` de la propuesta; aplicarla de verdad exige una llamada aparte y explícita a `combate.atacar_personaje`/`combate.atacar_enemigo` (D-COMBATE-04). `registrar_accion_turno` avisa (`aviso`, no error) si el participante no coincide con el turno actual, en vez de fallar — puede ser legítimo registrar fuera de turno. `ronda`/`turno_participante_id` de la propuesta se derivan del combate, no se piden al llamador.
- **Pendiente:** flujo más fluido para aplicar una reacción ya confirmada (hoy son dos llamadas separadas); flanqueo/cobertura calculados automáticamente en vez de propuestos a mano (#F5-09).
- **P.** P1.
### #F5-06 — Prueba integrada manual de combate — ✅ HECHO (F5.6)
- **Estado.** No añade reglas ni mecánicas: validación/documentación. Guía `docs/PRUEBA_MANUAL_F5_COMBATE.md` (escena de prueba con dos ratas, prompts sugeridos para el REPL, flujo esperado de tools, rutas en disco a verificar, 13 criterios de aceptación, troubleshooting). Escena de referencia `docs/escenarios/mini_aventura_combate.md`. Test `tests/test_combate_integrado_f5.py` (sin red, sin LLM real, `tmp_path`): ficha → combate → enemigo → iniciativa → ataque con ventaja → acción de turno → propuesta de reacción → confirmación (sin daño) → aplicación explícita de la reacción confirmada → avanzar turno → terminar combate → 10 eventos auditables verificados.
- **Decisión técnica.** El test integrado mockea `_tirar_d20`/`_tirar_tiradas_ataque`/`_tirar_dano` (mismos puntos de extensión que F5.2–F5.4) en vez de fijar semillas, evitando fragilidad por aleatoriedad real. La escena de referencia vive en `docs/escenarios/` (nuevo subdirectorio, mismo patrón que `docs/estado/`/`docs/tools/`/`docs/memoria/`) en vez de `examples/` en la raíz, por coherencia con la estructura existente del proyecto.
- **P.** P1.
### #F5-07 — Integración narrativa de combate (sugerir/registrar consecuencia al terminar, sin automatizarlo demasiado)
### #F5-08 — Skill `dirigir-combate`
### #F5-09 — Reglas básicas más ricas (condiciones, salvaciones, flanqueo/cobertura automáticos) — solo si D17 lo justifica
### #F5-10 — Críticos más ricos (rangos de amenaza ampliados, daño extra por rasgo de clase)
### #F5-11 — Fixtures: enemigos low-level reutilizables
- **P.** P1.

---

## F6.1 — Disciplina de uso de tools y refuerzo del prompt

> No es parte de "F6 — Creación de mundo" (más abajo): es una corrección de
> robustez descubierta en la prueba manual de F5.6 contra un endpoint real.

### #F6.1-01 — Prohibir tool calls simuladas en texto + reintento — ✅ HECHO (F6.1)
- **Estado.** Durante la prueba manual real (vLLM, perfil `rapido`), el modelo respondió con bloques `[{"name": "ficha_leer", "arguments": {...}}]` en vez de llamar la tool real, incluso tras pedírselo explícitamente. Corregido en dos frentes: `src/dm_agent/prompts/system_dm_minimo.md` (nueva "REGLA ABSOLUTA SOBRE HERRAMIENTAS", "ESTADO MECÁNICO" con lista cerrada de qué requiere tool real, regla de campaña/personaje por defecto, regla de no duplicar combates; también se corrigió el texto obsoleto de F2.2 que decía "no hay ficha/combate/inventario" — ya existen) y `src/dm_agent/nucleo/agente.py` (`_contiene_tool_call_simulada` detecta el patrón `"name"`+`"arguments"` en texto sin parsearlo ni ejecutarlo; `AgenteDM.responder` reintenta una sola vez por turno con mensaje correctivo). Tests: `tests/test_tool_discipline.py`.
- **Decisión técnica.** Se prefirió Opción 2 (reintento automático, limitado a una vez por turno) sobre solo advertencia de debug, porque es sencilla y testeable sin red. El detector deliberadamente no parsea ni ejecuta el JSON simulado (sería peligroso: ejecutar argumentos arbitrarios escritos como texto narrativo). El mensaje correctivo se envía como turno `user` sintético, sin persistirse en `Sesion` (igual que el round-trip de tool_calls reales, que tampoco se persiste entre turnos).
- **Pendiente:** si el modelo ignora el reintento y sigue escribiendo JSON simulado, no hay corrección adicional — es un límite de qué tan bien el modelo sigue instrucciones, no algo que el cliente pueda forzar. No se intentó normalizar/parsear el JSON simulado como fallback de ejecución (riesgo de seguridad, descartado explícitamente).
- **P.** P0 (bloqueaba el uso real del agente en pruebas manuales).

### #F6.1.1-01 — Detectar tool calls simuladas en XML/pseudo-call — ✅ HECHO (F6.1.1)
- **Estado.** En una segunda prueba manual real, el detector de F6.1 avisó correctamente sobre JSON simulado, pero el modelo volvió a simular una tool call con otro formato: `<call:name="ficha_leer"><call:param="campaña_id">campana_tyr</call:param><call:param="personaje_id">tyr</call:param></call:>`. Corregido ampliando `_contiene_tool_call_simulada` (`src/dm_agent/nucleo/agente.py`) para reconocer también `<call:name=...>`, `<call:param=...>`, `</call:>`, `<tool_call>` y `<tool>`, sin parsear ni ejecutar ese contenido. El mensaje correctivo (`_MENSAJE_CORRECTIVO_TOOL_SIMULADA`) ahora nombra explícitamente ambos formatos prohibidos (JSON y XML/pseudo-call). El system prompt (`src/dm_agent/prompts/system_dm_minimo.md`) incluye ambos ejemplos prohibidos. Tests ampliados en `tests/test_tool_discipline.py`.
- **Decisión técnica.** Misma política que F6.1: detectar y reintentar una vez por turno, nunca parsear/ejecutar el contenido simulado. Se mantuvo el límite de un único reintento automático por turno (no se añadió un segundo nivel de reintento ni una lista extensible de formatos "por si acaso" — solo los formatos observados realmente en pruebas manuales).
- **P.** P0 (mismo bloqueo que F6.1, otro formato de texto simulado).

## F6.2 — Filtrado contextual de tools y diagnóstico de tool-calling

> Igual que F6.1/F6.1.1: no es parte de "F6 — Creación de mundo" (más abajo).

### #F6.2-01 — Selector contextual de tools por turno — ✅ HECHO (F6.2)
- **Estado.** Tras F6.1.1, una tercera prueba manual real mostró `ficha_leer`/`combate_estado`/`combate_tirar_iniciativa` funcionando como tool calls reales, pero `combate_atacar_enemigo` seguía fallando como pseudo-call `<tool_call>` incluso pidiéndoselo explícitamente. Diagnóstico: disciplina de tool-calling del modelo local degradándose con muchas tools/schemas a la vez (no un problema de la tool en sí). Corregido con `src/dm_agent/nucleo/seleccion_tools.py` (nuevo): `seleccionar_tools_para_turno` reconoce por palabra clave siete categorías (ficha, inventario, combate general, ataque, iniciativa/turno, reacción, memoria/sesión) y devuelve solo las tools relevantes; `None` si no hay intención clara (fallback: todas las tools, igual que antes de F6.2). `AgenteDM._tools_para_turno` (`src/dm_agent/nucleo/agente.py`) aplica el filtro antes de cada turno y, en `--debug`, imprime `[debug] tools expuestas: ...`. Tests: `tests/test_tool_selection.py`.
- **Decisión técnica.** Las categorías de combate específicas (ataque/iniciativa/reacción) tienen prioridad sobre el conjunto completo de las 14 tools de combate, aunque también coincidan palabras genéricas de combate en el mismo mensaje (p. ej. "ataca a la rata" coincide con "ataque" y con "combate"/"enemigo", pero solo expone las 5 tools de ataque). La detección ignora acentos (normaliza con NFKD) para no depender de que el modelo o el usuario los escriban bien. No se cambia la política de F6.1/F6.1.1: el filtrado de tools es una capa independiente para reducir la necesidad de simular nada, no un sustituto del detector+reintento existente.
- **Pendiente:** las palabras clave son las observadas en pruebas manuales reales; si aparece un mensaje claro que no dispara ninguna categoría (y por tanto cae al fallback de "todas las tools"), se añade la palabra que falte en `seleccion_tools.py` en vez de rediseñar el mecanismo.
- **P.** P0 (bloqueaba `combate_atacar_enemigo` en pruebas manuales reales pese a F6.1.1).

## F6.3 — Robustez contra tool calls duplicadas, respuestas vacías y tool explícita no ejecutada

> Igual que F6.1/F6.1.1/F6.2: no es parte de "F6 — Creación de mundo" (más abajo).

### #F6.3-01 — Deduplicar tool calls idénticas en el mismo turno — ✅ HECHO (F6.3)
- **Estado.** Con tool calls reales ya funcionando (F6.2), una prueba manual real mostró al modelo llamando `combate_proponer_reaccion` dos veces con los mismos argumentos en el mismo turno, dejando dos reacciones pendientes duplicadas (hubo que caducar una a mano). Corregido en `AgenteDM.responder` (`src/dm_agent/nucleo/agente.py`): un conjunto `tool_calls_ejecutadas` con clave `(nombre_api, argumentos_json normalizado con sort_keys)` persiste durante el turno; la segunda llamada idéntica no se despacha de verdad, se responde con un resultado sintético de "ya se ejecutó" y se imprime `[debug] tool duplicada ignorada: ...`. Argumentos distintos o el mismo par tool+argumentos en un turno posterior se ejecutan con normalidad (el conjunto se reinicia en cada `responder()`).
- **P.** P0 (corrompía el estado del combate con reacciones pendientes duplicadas).

### #F6.3-02 — Mensaje seguro ante respuesta vacía sin tool calls — ✅ HECHO (F6.3)
- **Estado.** Tras confirmar una reacción con `combate_resolver_reaccion`, el modelo devolvió un turno sin texto y sin tool call; no hubo error visible y la reacción quedó pendiente sin que el usuario supiera que el turno no había hecho nada. Corregido: si la respuesta final no tiene texto útil y no hubo tool calls en ese paso, `AgenteDM.responder` devuelve un mensaje seguro pidiendo reformular, e imprime `[debug] respuesta vacía del modelo sin tool calls`.
- **P.** P0 (turno silenciosamente vacío, sin ninguna señal de que algo falló).

### #F6.3-03 — Reintento si el usuario pide una tool explícita y no se ejecuta — ✅ HECHO (F6.3)
- **Estado.** El mismo caso de `combate_resolver_reaccion` no ejecutada (ver #F6.3-02) es además un caso de "el usuario nombró la tool por su nombre API y no se llamó de verdad". `_tool_mencionada_no_ejecutada` (`src/dm_agent/nucleo/agente.py`) detecta esto comparando el mensaje del usuario contra los nombres de las tools expuestas en el turno (`_tools_para_turno`, F6.2) y los nombres de tools ya ejecutadas de verdad. Si hay una mención sin ejecutar, dispara un único reintento corrector; si tras el reintento sigue sin ejecutarla, la respuesta final es "No se ha podido ejecutar la herramienta solicitada: ..." (nunca se afirma que se ejecutó). Esta comprobación tiene prioridad sobre #F6.3-02 pero **no** sobre F6.1/F6.1.1 (si hay una pseudo-call JSON/XML, manda esa disciplina primero, sin parsear/ejecutar nada).
- **Decisión técnica (común a las tres).** Ninguna de las tres defensas cambia mecánica de juego ni toca esquemas de combate/ataque/daño/iniciativa/inventario/ficha/memoria narrativa: viven enteramente en el agent loop (`AgenteDM.responder`). Tests: `tests/test_agent_tool_robustness.py`.
- **P.** P0 (mismo incidente real que #F6.3-02).

## F6.4 — Comando manual `/tool` (depuración/recuperación sin LLM)

> Igual que F6.1-F6.3: no es parte de "F6 — Creación de mundo" (más abajo).

### #F6.4-01 — Comando `/tool` para ejecutar tools reales sin pasar por el LLM — ✅ HECHO (F6.4)
- **Estado.** Incluso con F6.3 detectando "tool explícita mencionada pero no ejecutada" y reintentando una vez, hubo un caso real (`combate_listar_reacciones` con todos los argumentos en el mensaje) donde el modelo seguía sin emitir la tool call real tras el reintento. Corregido añadiendo un comando manual al REPL: `/tool <nombre_tool_api> <json_argumentos>` (`src/dm_agent/nucleo/bucle.py`) ejecuta `RegistroHerramientas.dispatch_api` directamente — `parsear_comando_tool` separa nombre/JSON y valida (error controlado, nunca rompe el REPL si el JSON es inválido o la tool no existe); `SesionInteractiva.ejecutar_tool_manual` resuelve y despacha, persiste los cambios igual que una tool real del LLM, y registra `tool_call`/`tool_result` en `Sesion` para auditoría — pero **sin** registrar un turno `user`/`assistant`, así que no entra en el historial conversacional que se reinyecta al LLM. Aparece en `/ayuda`. Tests: `tests/test_cli.py`.
- **Decisión técnica.** `/tool` es estrictamente un comando manual disparado por el usuario; no tiene ninguna relación con la detección de pseudo-calls (F6.1/F6.1.1) ni con el reintento de F6.3 — nunca parsea ni ejecuta texto que haya escrito el modelo, solo lo que el usuario escribe explícitamente tras `/tool`.
- **P.** P1 (mejora de robustez/recuperación; no bloqueaba el uso del agente, pero limitaba la prueba manual cuando un modelo concreto se resistía a una tool).

## F6.5 — Consolidación de ergonomía y robustez de combate

> Igual que F6.1-F6.4: no es parte de "F6 — Creación de mundo" (más abajo). Cierra una prueba manual de combate completa de extremo a extremo (`tyr` vs. `rata_1`/`rata_2`, terminada con `/tool combate_terminar`) que reveló varias fricciones reales a la vez.

### #F6.5-01 — Contexto operativo activo (prohibición de placeholders) — ✅ HECHO (F6.5)
- **Estado.** El modelo usaba placeholders incorrectos (`campaña_actual`, `combate_actual`, "Tyr" en vez de `tyr`) en lugar de los IDs reales, aunque ya estaban disponibles sin preguntar. Corregido con `src/dm_agent/nucleo/contexto_operativo.py` (nuevo): `construir_bloque_contexto_operativo` deriva los IDs reales (`campaña_id`/`personaje_id`/`combate_id`/`estado`/`ronda`/`turno actual`) de `GestorCombateNarrativo.cargar_activo`, sin LLM. `AgenteDM` lo inyecta como el último mensaje `system` antes del historial (después de la memoria narrativa, para que pese más) y lo añade también al reintento corrector de F6.3. Si no hay combate activo, lo dice explícitamente sin fallar. Tests: `tests/test_contexto_operativo.py`, `tests/test_agent_tool_robustness.py`.
- **P.** P0 (el modelo no podía operar de forma fiable sin los IDs reales).

### #F6.5-02 — Comandos cómodos `/combate` `/turno` `/reacciones` `/ficha` `/estado` — ✅ HECHO (F6.5)
- **Estado.** `/tool` (F6.4) es potente pero incómodo para operaciones frecuentes (JSON largo a mano). Añadidos cinco atajos en `SesionInteractiva` (`src/dm_agent/nucleo/bucle.py`) que reutilizan el mismo mecanismo (`dispatch_api` directo, sin LLM) pero resuelven los IDs solos a partir del combate activo. `/estado` es un resumen compacto y legible (no JSON bruto). Todos muestran error controlado si falta combate/personaje activo; ninguno llama al LLM. Aparecen en `/ayuda`. Tests: `tests/test_cli.py`.
- **P.** P1 (ergonomía; no bloqueaba el uso, pero hacía la prueba manual tediosa).

### #F6.5-03 — `combate_avanzar_turno` salta enemigos derrotados — ✅ HECHO (F6.5)
- **Estado.** El avance de turno dejaba como turno activo a enemigos ya derrotados. Corregido en `_ToolAvanzarTurno.ejecutar` (`src/dm_agent/herramientas/combate.py`): salta participantes `enemigo` con `estado == "derrotado"` o `hp_actual <= 0` (nunca personajes), acotado a `len(orden_iniciativa)` iteraciones para no bucle-infinito. El resultado incluye `enemigos_derrotados_saltados` y `todos_los_enemigos_derrotados`/`deberia_terminar_combate`. Tests: `tests/test_iniciativa_turnos.py`.
- **P.** P1 (no bloqueaba, pero obligaba a avances de turno manuales repetidos sobre enemigos ya derrotados).

### #F6.5-04 — Señal `todos_los_enemigos_derrotados` al atacar — ✅ HECHO (F6.5)
- **Estado.** Nada avisaba de que un ataque había dejado a todos los enemigos derrotados. `combate_atacar_enemigo` añade `todos_los_enemigos_derrotados`/`deberia_terminar_combate` (mismos campos que #F6.5-03) cuando corresponde. **Decisión: solo señaliza, no termina el combate automáticamente** (preferencia explícita del encargo: D-COMBATE-04 ya exige confirmación explícita del jugador/DM para terminar combate). Tests: `tests/test_ataques_combate.py`.
- **P.** P2 (conveniencia; el combate se podía terminar manualmente sin esta señal, como ya ocurrió en la prueba real).

### #F6.5-05 — Recomendación: registrar la acción narrativa tras ver el resultado real — ✅ HECHO (F6.5, documentación)
- **Estado.** Se registró una acción narrativa como "falló" antes de comprobar `impacta` en el resultado real (una rata hizo crítico); hubo que corregir a mano. No se implementó edición de acciones ni un comando `/corregir` (explícitamente no necesario en esta fase): se documentó la recomendación en `docs/PRUEBA_MANUAL_F5_COMBATE.md` (sección 11) — registrar después de ver el resultado real, no antes; si se comete un error, registrar una acción nueva de tipo `correccion` en vez de editar la anterior.
- **Pendiente:** edición/corrección estructurada de `AccionTurno` (tipo `correccion` como convención documentada, no como campo validado) y comando `/corregir`, si en el futuro la fricción lo justifica.
- **P.** P2.

### #F6.5-06 — Avisos no bloqueantes al atacar fuera del flujo normal — ✅ HECHO (F6.5.2c)
- **Estado.** El modelo atacaba sin tirar iniciativa, fuera de turno, o contra enemigos ya derrotados, sin que el agente pudiera advertirle de la anomalía. `combate_atacar_enemigo` y `combate_atacar_personaje` añaden `"avisos": []` al resultado con cuatro comprobaciones: (1) sin iniciativa tirada, (2) fuera del turno actual, (3) contra enemigo ya derrotado, (4) todos los enemigos derrotados. **Decisión: los avisos no bloquean el ataque** — el LLM narra, las herramientas señalizan, el jugador decide. Tests: `tests/test_ataques_combate.py`.
- **P.** P2 (ergonomía; no bloqueaba el combate, pero dejaba al modelo operar sin feedback sobre el flujo de turnos).

### #F6.5-07 — Coherencia narrativa tras tools de combate — ✅ HECHO (F6.5.3a)
- **Estado.** El modelo declaraba el combate terminado sin llamar `combate_terminar`, ignoraba los `avisos` de las herramientas, y devolvía respuestas vacías tras ejecutar tools correctamente. Corregido en tres frentes: (A) system prompt prohíbe declarar combate terminado si `estado == "activo"`, (B) system prompt obliga a mencionar `avisos` en la narración, (C) `combate_atacar_personaje` añade `"avisos": []` simétrico con `combate_atacar_enemigo`, (D) fallback enriquecido tras tool ejecutada nombra la tool en el mensaje. Tests: `tests/test_agent_tool_robustness.py`, `tests/test_ataques_combate.py`.
- **P.** P2 (coherencia narrativa; no bloqueaba el combate, pero dejaba al modelo narrar inconsistencias mecánicas).

---

## F6 — Creación de mundo / campaña / aventura

### #F6-01 — Migrar `config/tonos/` desde dnd5e
### #F6-02 — Skill `crear-mundo`
### #F6-03 — Skill `crear-campana`
### #F6-04 — Skill `crear-aventura`
### #F6-05 — Tools `mundo.*`, `escena.*`, `campaña.*`
- **P.** P2.

---

## F7 — RAG anti-spoiler

### #F7-01 — Ingesta PDF → MD (pluggable)
### #F7-02 — Chunker semántico + metadatos
### #F7-03 — Índice léxico (FTS)
### #F7-04 — Índice vectorial (FAISS o Chroma local)
### #F7-05 — Filtros de visibilidad / spoiler
### #F7-06 — Skill `importar-aventura`
### #F7-07 — Skill `rag-anti-spoiler` (consulta segura)
- **P.** P2.

---

## F8 — Skills completas

### #F8-01 — Router de intención determinista (regex + vocabulario)
### #F8-02 — Router de intención con fallback LLM
### #F8-03 — Skills sociales / exploración / viaje / descanso
### #F8-04 — Skills de gestión (PNJ, faccion, localizacion, mision)
### #F8-05 — Skill `arbitrar-regla-ambigua`
### #F8-06 — Skill `improvisar-contenido`
### #F8-07 — Skill `mantener-continuidad`
- **P.** P2.

---

## F9 — Endpoints locales

### #F9-01 — Adaptador vLLM
### #F9-02 — Adaptador vMLX
### #F9-03 — Adaptador llama.cpp server
### #F9-04 — Adaptador LM Studio
### #F9-05 — Adaptador Open WebUI
### #F9-06 — Selector de perfil en runtime
- **P.** P2.

---

## F10 — Interfaz cómoda

### #F10-01 — Rich/Textual TUI
### #F10-02 — Exportar campaña a Markdown
### #F10-03 — Modo debug verbose
- **P.** P3.

---

## F11 — Hardening

### #F11-01 — Cobertura `nucleo/` ≥ 70 %
### #F11-02 — Tests anti-spoiler exhaustivos
### #F11-03 — Tests de recuperación tras corrupción
### #F11-04 — Documentación final
- **P.** P3.

---

## F12 — Diseño avanzado (sin código)

Issues placeholder para futuras conversaciones.
