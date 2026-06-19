# Plan de implementación por fases

> Política: ninguna fase se da por terminada sin **tests pasando** y documentación actualizada. Prohibido saltar fases.

---

## Fase 0 — Análisis (HECHO)

**Objetivo.** Documentar Hermes y dnd5e-framework, decidir qué se reutiliza.

**Entregables.**
- `docs/ANALISIS_HERMES.md` ✓
- `docs/ANALISIS_DND5E.md` ✓
- `docs/ARQUITECTURA.md` (visión general) ✓
- `docs/PLAN_FASES.md` (este archivo) ✓
- `docs/BACKLOG.md` ✓
- `docs/RIESGOS.md`, `docs/DECISIONES_ABIERTAS.md`, `docs/MODELOS_LOCALES.md` ✓

**Definición de hecho.** Documentos revisados y comprometidos.

---

## Fase 1 — Esqueleto del proyecto

**Objetivo.** Repo navegable con estructura final, instalable en `conda env rpg`, con test de humo.

**Archivos a crear.**
- `pyproject.toml`, `README.md`, `AGENTS.md`, `.gitignore`, `.editorconfig`, `Makefile`.
- `config/proyecto.json`, `config/modelos.json`, `config/perfiles.json`.
- `src/dm_agent/__init__.py`, `__main__.py`, `cli.py`.
- `src/dm_agent/nucleo/{__init__,agente,bucle,contexto,eventos,logger}.py` (stubs).
- `src/dm_agent/herramientas/{__init__,base,registro,dados}.py` (dados es real).
- `src/dm_agent/skills/{__init__,cargador,router}.py` (cargador funcional mínimo).
- `src/dm_agent/{memoria,estado,llm,esquemas,reglas,rag,narrativa}/__init__.py` con stubs.
- `tests/{conftest.py,test_smoke.py,test_dados.py,test_registro.py,test_skills_loader.py}`.
- `skills/ejemplo-escena-social/SKILL.md`.

**Tests.**
- `test_smoke`: importa el paquete.
- `test_dados`: tirada determinista con semilla.
- `test_registro`: registrar y dispatchar tool.
- `test_skills_loader`: descubre la skill de ejemplo y parsea frontmatter.

**Definición de hecho.** `conda activate rpg && pip install -e . && pytest` pasa al 100%.

**Riesgos.** Mezclar conda/pip; documentado en AGENTS.md.

---

## Fase 2 — Núcleo CLI jugable mínimo

**Objetivo.** `dm-agent` arranca, conecta a un endpoint OpenAI-compatible, mantiene una sesión con guardado.

Subfases:
- **F2.1 — Cliente LLM OpenAI-compatible.** ✅ **Implementada** (commit `feat: add OpenAI-compatible LLM client`).
- **F2.2 — Agent loop mínimo + REPL + sesión JSONL.** ✅ **Implementada** (commit `feat: add minimal DM agent loop and REPL`).
- **F2.3 — Validación manual.** ✅ Procedimiento documentado en [`PRUEBA_MANUAL_F2.md`](./PRUEBA_MANUAL_F2.md) (sin código nuevo).

**Archivos.**
- `src/dm_agent/llm/cliente.py` (cliente OpenAI-compatible). ✅ F2.1 — no-streaming; `stream=True` lanza `NotImplementedError`.
- `src/dm_agent/nucleo/agente.py` (`AgenteDM`: loop con tool round-trip y `max_iter_turno`). ✅ F2.2.
- `src/dm_agent/nucleo/bucle.py` (REPL + cableado del agente). ✅ F2.2.
- `src/dm_agent/cli.py` (REPL con `/ayuda`, `/salir`, `/guardar`, `/continuar`, `/nueva`, `/debug`). ✅ F2.2.
- `src/dm_agent/persistencia/sesion.py` (JSONL append-only). ✅ F2.2.
- `src/dm_agent/prompts/system_dm_minimo.md` (system prompt mínimo de DM). ✅ F2.2.

**Tests.**
- `test_cliente_llm.py` mock del endpoint (`httpx.MockTransport`). ✅ F2.1.
- `test_sesion_jsonl.py`, `test_agente_minimo.py`, `test_cli.py`. ✅ F2.2.

**Definición de hecho.** Sesión interactiva real contra un vLLM/LM Studio local; transcripción persistente. ✅ Alcanzada en lo esencial: chat CLI por turnos con dados reales y sesión JSONL. *Pendiente para fases siguientes: ficha/combate/estado, memoria avanzada, RAG y streaming.*

---

## Fase 3 — Tools deterministas: dados, ficha, estado

**Objetivo.** Tool-calling real. Estado mecánico modificable solo vía tools, con validación.

Subfases:
- **F3.1 — Esquemas base (`Ficha`, `EstadoPartida`, `Evento`).** ✅ **Implementada** (commit `feat: add core state schemas`). Solo modelos pydantic v2 + validaciones + docs + tests; sin tools, sin gestor de estado.
- **F3.2 — GestorEstado JSON + snapshots.** ✅ **Implementada** (commit `feat: add JSON state manager`). Persistencia JSON de `Ficha`/`EstadoPartida` con escritura atómica y snapshots opcionales. Sin tools todavía.
- **F3.3 — Tools `ficha.*`.** ⏳ Pendiente.
- **F3.4 — Tools `hp_xp.*`.** ⏳ Pendiente.
- **F3.5 — Eventos JSONL auditables por cambio.** ⏳ Pendiente. **Incluye unificar los dos `Evento`** (el dataclass de `nucleo.eventos` y el pydantic de `esquemas.evento`).

**Archivos.** `esquemas/{ficha,estado,evento,comun}.py` ✅ F3.1; `estado/gestor.py` ✅ F3.2; `herramientas/{ficha,hp_xp,inventario,condiciones}.py`, `nucleo/eventos.py` (real), `nucleo/logger.py` (append-only) ⏳.

**Tests.** `tests/test_esquemas_f3.py` ✅ F3.1; `tests/test_gestor_estado.py` ✅ F3.2. Cobertura por tool (mínimo 1 happy path + 2 errores cada una) ⏳.

**Definición de hecho.** El LLM ya no puede tocar HP/XP/inventario directamente; cada cambio deja Evento. *(No alcanzada aún: F3.1 aporta esquemas, F3.2 aporta persistencia; faltan las tools.)*

> **Reglas adaptadas (D17).** Documentación en `docs/REGLAS_ADAPTADAS.md` + [ADR-0017](./decisiones/0017-dnd55-narrativo-solitario.md): D&D 5.5 adaptado a juego narrativo en solitario. La implementación (motor de adaptación, tools de aprobación de reglas caseras) se planificará en una fase de reglas posterior; **no** forma parte de F3.

---

## Fase 4 — Memoria narrativa y resúmenes

**Objetivo.** Bitácora narrativa append-only + resúmenes de escena/sesión inyectables.

**Archivos.** `memoria/{tipos,almacen}.py`, `narrativa/{director,bitacora}.py`, `herramientas/sesion.py`.

**Tests.** Resumen reproducible con prompt fijo y mock LLM; bitácora no se pierde.

**Definición de hecho.** Tras cerrar y reabrir, una partida puede continuar con contexto coherente.

---

## Fase 5 — Combate funcional

**Objetivo.** Iniciativa, turnos, HP, CA, ataques, daño, condiciones básicas.

**Archivos.** `herramientas/combate.py` (real), `estado/combate.py`, `reglas/combate.py`, fixtures monstruos básicos.

**Tests.** Encuentro 1 PJ vs 2 goblins; iniciativa reproducible; condiciones aplicadas/retiradas; eventos correctos.

**Definición de hecho.** Una sesión completa de combate puede jugarse end-to-end.

---

## Fase 6 — Creación de mundo, campaña, aventura

**Objetivo.** Skills `crear-mundo`, `crear-campana`, `crear-aventura`. Migración de `config/tonos/` desde dnd5e.

**Archivos.** `skills/crear-mundo/`, `skills/crear-campana/`, `skills/crear-aventura/`, `herramientas/{mundo,escena,campaña}.py`.

**Tests.** Generación reproducible con seeds; YAML validados por schema.

**Definición de hecho.** Se puede generar una campaña pequeña con 1 aventura y dirigirla en F4+F5.

---

## Fase 7 — RAG anti-spoiler

**Objetivo.** Importar aventuras (PDF/MD), chunking, índice, filtros de visibilidad.

**Archivos.** `rag/{ingesta,chunker,indice,filtros}.py`, `herramientas/rag.py`.

**Tests.** Ingesta PDF→chunks; un chunk marcado `oculto` no aparece en perspectiva jugador; sí en perspectiva DM; auditoría de redacciones.

**Definición de hecho.** Dirigir una aventura importada sin revelar zonas no descubiertas.

---

## Fase 8 — Sistema completo de skills

**Objetivo.** Router de intención, progressive disclosure, todas las skills v1 declaradas.

**Archivos.** `skills/router.py` (real), todas las skills `skills/*/SKILL.md` listas.

**Tests.** Router elige skill correcta para 30 entradas etiquetadas (regresión).

**Definición de hecho.** Cualquier escena se cubre con una skill explícita.

---

## Fase 9 — Integración con múltiples endpoints locales

**Objetivo.** Probar vLLM, vMLX, llama.cpp, LM Studio, Open WebUI con perfiles.

**Archivos.** `llm/cliente.py` afinado, `docs/MODELOS_LOCALES.md` ampliado.

**Tests.** Cada endpoint smoke-test (skippable si no hay servidor).

**Definición de hecho.** Cambio de perfil cambia modelo/endpoint sin reiniciar.

---

## Fase 10 — Interfaz cómoda

**Objetivo.** CLI rica (Rich/Textual), comandos, historial, modo debug, exportación de campaña.

**Tests.** Snapshot de renderizado clave.

**Definición de hecho.** Comparable en comodidad a `cli_aventura.py` del proyecto antiguo pero modular.

---

## Fase 11 — Evaluación, tests, hardening

**Objetivo.** Tests de integración, anti-spoiler, recuperación, fixtures completos.

**Definición de hecho.** Cobertura mínima del 70 % en `nucleo/`, `herramientas/`, `rag/filtros.py` al 100 %.

---

## Fase 12 — Proyección avanzada (diseño, no implementación)

Documentar en `docs/FUTURO/`:
- Multijugador local.
- Subagentes especializados (Narrador, Árbitro, Diseñador, Guardián continuidad).
- Generación de mapas e imágenes.
- Voz (STT/TTS).
- Compatibilidad con otros sistemas (PbtA, FATE, Cypher…).
- SQLite + Qdrant/Chroma.
- Modo servidor LAN.
- Modo "DM assistant" para partidas humanas.
- Modo "autor de campaña" (no es director, solo crea).

Sin código todavía; sólo decisiones y trade-offs.
