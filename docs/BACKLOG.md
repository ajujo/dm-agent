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

### #F5-01 — Combate narrativo mínimo — ✅ HECHO (F5.1)
- **Estado.** Esquemas `EnemigoCombate`/`CombateNarrativo` (`esquemas/combate.py`). `GestorCombateNarrativo` (`estado/combate.py`): un JSON por combate (`combates/<combate_id>.json`) + referencia de combate activo por campaña (`combates/activo.json`, solo el `combate_id`, nunca el combate completo). Tools `combate.{iniciar,estado,añadir_enemigo,daño_enemigo,terminar}` (`herramientas/combate.py`), con eventos auditables (`combate_iniciado`, `enemigo_añadido`, `daño_enemigo`, `combate_terminado`) vía `RegistroEventosEstado`. Distancias narrativas abstractas (`cerca`/`media`/`lejos`/`fuera_de_alcance`); sin grid/casillas. El daño al personaje jugador sigue pasando por `hp_xp.aplicar_daño`; sin XP automática. Docs: `docs/estado/combate.md`, `docs/tools/combate.md`. Tests: `tests/test_combate_narrativo.py`, `tests/test_tools_combate.py`.
- **Decisión técnica.** `combate.iniciar` crea el combate ya en estado `activo` directamente (sin paso `preparando` expuesto vía tool en F5.1); `activo.json` guarda solo una referencia por simplicidad y para evitar desincronización con el contenido real del combate.
- **Pendiente:** integración con memoria narrativa (sugerir/registrar consecuencia al terminar combate); iniciativa/turnos más ricos, condiciones, ataques con tirada real si el diseño narrativo lo justifica más adelante.
- **P.** P1.
### #F5-02 — Integración narrativa de combate (sugerir/registrar consecuencia al terminar)
### #F5-03 — Skill `dirigir-combate`
### #F5-04 — Reglas básicas más ricas (ataque con tirada, condiciones) — solo si D17 lo justifica
### #F5-05 — Fixtures: enemigos low-level reutilizables
- **P.** P1.

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
