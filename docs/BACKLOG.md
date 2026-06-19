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
### #F3-01 — Tools `ficha.*` (sobre esquema `Ficha`)  ⏳ F3.3
### #F3-02 — Tools `hp_xp.*` (sobre `Ficha`/`EstadoPartida`)  ⏳ F3.4
### #F3-03 — Tools `inventario.*`
### #F3-04 — Tools `condiciones.*`
### #F3-05 — Bus de eventos + logger append-only JSONL  ⏳ F3.5
### #F3-06 — Validador central de cambios de estado
- **P.** todas P1.

> Nota: F3.2 (GestorEstado JSON + snapshots) se intercala entre los esquemas y las tools.

---

## F4 — Memoria narrativa

### #F4-01 — Esquemas de memoria tipada
### #F4-02 — Bitácora narrativa append-only Markdown
### #F4-03 — Skill `resumir-sesion`
### #F4-04 — Skill `preparar-siguiente`
- **P.** P1.

---

## F5 — Combate

### #F5-01 — Estado de combate + iniciativa
### #F5-02 — Tools `combate.*`
### #F5-03 — Skill `dirigir-combate`
### #F5-04 — Reglas básicas (ataque, daño, condiciones)
### #F5-05 — Fixtures: 4 enemigos low-level
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
