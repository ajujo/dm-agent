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
- **F3.3 — Tools `ficha.*`.** ✅ **Implementada** (commit `feat: add character sheet tools`). `ficha.{leer,guardar,validar,actualizar,listar}` sobre `GestorEstado`, disponibles para el agente. Sin HP/XP semántico.
- **F3.4 — Tools `hp_xp.*` + eventos auditables JSONL.** ✅ **Implementada** (commit `feat: add HP and XP tools`). `hp_xp.{aplicar_daño,aplicar_curacion,otorgar_xp,consultar_estado_vital}` sobre `GestorEstado`+`Ficha`; cada cambio deja `Evento` en `eventos.jsonl`. Sin combate, muerte ni subida de nivel.
- **F3.5 — Normalizar/unificar eventos.** ✅ **Implementada** (commit `refactor: unify event model`). Modelo canónico único `esquemas.evento.Evento`; `nucleo.eventos` lo re-exporta y el bus lo publica; dados migrado a `crear_evento`. Cierra el bloque de estado mecánico mínimo (ficha + HP/XP + eventos auditables).
- **F3.6 — Tools `inventario.*` (inventario simple).** ✅ **Implementada** (commit `feat: add simple inventory tools`). `inventario.{listar,añadir,quitar,equipar,desequipar}` sobre `Ficha.inventario` con eventos auditables. Sin peso/carga, oro/economía, slots ni equipo complejo.

**Archivos.** `esquemas/{ficha,estado,evento,comun}.py` ✅ F3.1; `estado/gestor.py` ✅ F3.2; `herramientas/ficha.py` ✅ F3.3; `herramientas/hp_xp.py` + `estado/eventos.py` ✅ F3.4; `nucleo/eventos.py` (unificado) ✅ F3.5; `herramientas/inventario.py` ✅ F3.6; `herramientas/condiciones.py` ⏳.

**Tests.** `tests/test_esquemas_f3.py` ✅ F3.1; `tests/test_gestor_estado.py` ✅ F3.2; `tests/test_tools_ficha.py` ✅ F3.3; `tests/test_tools_hp_xp.py` ✅ F3.4; `tests/test_eventos_unificados.py` ✅ F3.5; `tests/test_tools_inventario.py` ✅ F3.6.

**Definición de hecho.** El LLM ya no toca HP/XP/inventario directamente; cada cambio deja un `Evento` auditable con modelo unificado. ✅ Para ficha + HP/XP + inventario simple. *Condiciones, economía y combate quedan fuera de este bloque.*

> **Reglas adaptadas (D17).** Documentación en `docs/REGLAS_ADAPTADAS.md` + [ADR-0017](./decisiones/0017-dnd55-narrativo-solitario.md): D&D 5.5 adaptado a juego narrativo en solitario. La implementación (motor de adaptación, tools de aprobación de reglas caseras) se planificará en una fase de reglas posterior; **no** forma parte de F3.

---

## Fase 4 — Memoria narrativa y resúmenes

**Objetivo.** Bitácora narrativa append-only + resúmenes de escena/sesión inyectables.

Subfases:
- **F4.1 — Bitácora narrativa + memoria narrativa básica.** ✅ **Implementada** (commit `feat: add narrative memory log`). `EntradaNarrativa`, `GestorMemoriaNarrativa` (JSONL + Markdown append-only) y tools `narrativa.{registrar,reciente}`. Sin resumen LLM ni inyección automática.
- **F4.2 — Resumen de escena/sesión con LLM.** ✅ **Implementada** (commit `feat: add narrative summarization tools`). `ResumidorNarrativo` + tools `resumen.{entradas,texto}` + prompt fijo `resumen_narrativo.md`; guardan `EntradaNarrativa(tipo="resumen")`. Sin inyección automática.
- **F4.3 — Inyección de memoria narrativa en el contexto del agente.** ✅ **Implementada** (commit `feat: inject narrative memory into agent context`). `ConstructorContextoMemoria` + inyección como 2º mensaje `system` en `AgenteDM`; config `memoria` + `campaña_activa` en `proyecto.json`. Sin RAG ni entidades estructuradas.
- **F4.4 — Cierre y preparación de sesión.** ✅ **Implementada** (commit `feat: add session closing flow`). `CierreSesionNarrativa` + tools `sesion.{cerrar,cerrar_texto}` + prompt `cierre_sesion.md` + comando REPL `/cerrar`. Genera resumen de cierre + preparación de la próxima sesión (entradas `resumen` y `siguiente_sesion`, enlazadas por `campaña_id`/`sesion_id`).
- **F4.5 — Prueba integrada de campaña + guía manual.** ✅ **Implementada** (commit `test: add integrated campaign flow`). No añade funcionalidad: valida extremo a extremo el bucle de continuidad. Test integrado con mock LLM (`tests/test_campaña_integrada_f4.py`): ficha → escena → inventario + HP/XP → cierre (`resumen` + `siguiente_sesion`) → continuar con memoria inyectada antes del mensaje de usuario. Guía manual real `docs/PRUEBA_MANUAL_F4.md`. Ajuste menor en `memoria/contexto.py` para que el contenido (no solo el título) de las entradas recientes llegue al modelo.
- **F4.6 — Entidades narrativas estructuradas mínimas.** ✅ **Implementada** (commit `feat: add structured narrative entities`). Esquemas `PNJ`/`Lugar`/`Pista`/`Objetivo`/`FrenteAbierto` (`esquemas/entidades.py`), `GestorEntidadesNarrativas` (un JSON por tipo y campaña, guardado por `id` con escritura atómica) y tools `entidad.{guardar,listar}_*`. `ConstructorContextoMemoria` inyecta una sección `## Entidades importantes` (PNJ, lugares, pistas, objetivos, frentes) si existen, después de la bitácora reciente. Sin extracción automática con LLM, sin RAG, sin relaciones validadas.

**Archivos.** `esquemas/narrativa.py` + `memoria/narrativa.py` + `herramientas/narrativa.py` ✅ F4.1; `memoria/resumen.py` + `herramientas/resumen.py` + `prompts/resumen_narrativo.md` ✅ F4.2; `memoria/contexto.py` + integración en `nucleo/agente.py` ✅ F4.3; `memoria/cierre_sesion.py` + `herramientas/sesion.py` + `prompts/cierre_sesion.md` + `/cerrar` ✅ F4.4; `tests/test_campaña_integrada_f4.py` + `docs/PRUEBA_MANUAL_F4.md` ✅ F4.5; `esquemas/entidades.py` + `memoria/entidades.py` + `herramientas/entidades.py` + ampliación de `memoria/contexto.py` ✅ F4.6.

**Tests.** F4.1 + F4.2 + `tests/test_contexto_memoria.py`, `tests/test_agente_memoria.py` ✅ F4.3; `tests/test_cierre_sesion.py`, `tests/test_tools_sesion.py` ✅ F4.4; `tests/test_campaña_integrada_f4.py` ✅ F4.5; `tests/test_entidades_narrativas.py`, `tests/test_tools_entidades.py`, `tests/test_contexto_entidades.py` ✅ F4.6.

**Definición de hecho.** Tras cerrar y reabrir, una partida puede continuar con contexto coherente. ✅ La memoria narrativa reciente se inyecta automáticamente (F4.3), el cierre de sesión (F4.4) deja resumen + punto de arranque que se recuperan en la próxima, F4.5 lo valida con test integrado mock + guía manual, y F4.6 añade entidades narrativas estructuradas (PNJ, lugares, pistas, objetivos, frentes abiertos) consultables y, si existen, inyectadas al contexto. El agente ya puede guardar y consultar PNJ, lugares, pistas, objetivos y frentes abiertos como entidades narrativas estructuradas, e inyectar las más relevantes al contexto. El proyecto tiene una **campaña persistente básica con memoria narrativa + memoria estructurada**, pero **aún no** tiene combate, RAG, memoria vectorial ni reglas adaptadas. *Pendiente: cierre automático al salir y selector de campaña.*

---

## Fase 5 — Combate funcional

**Objetivo.** Sostener escenas de combate, primero en versión narrativa mínima
y más adelante (subfases posteriores) con más profundidad táctica si procede,
siempre coherente con D17 (D&D 5.5 narrativo en solitario / teatro de la
mente).

Subfases:
- **F5.1 — Combate narrativo mínimo.** ✅ **Implementada** (commit `feat: add minimal narrative combat`). Esquemas `EnemigoCombate`/`CombateNarrativo` (`esquemas/combate.py`), `GestorCombateNarrativo` (un JSON por combate + referencia de combate activo por campaña) y tools `combate.{iniciar,estado,añadir_enemigo,daño_enemigo,terminar}` con eventos auditables (`combate_iniciado`, `enemigo_añadido`, `daño_enemigo`, `combate_terminado`). El daño al personaje jugador sigue pasando por `hp_xp.aplicar_daño`; no hay XP automática. Sin inyección de combate al contexto narrativo todavía.
- **F5.1.1 — Alineación de combate D&D narrativo sin grid.** ✅ **Implementada** (commit `refactor: align combat distances with narrative D&D style`). Corrección de diseño, no de API: se conserva `combate.*` como nombre de tools (no se renombra a `conflicto.*`) y el vocabulario D&D (enemigo, ataque, daño, distancia). Las distancias abstractas pasan de `cerca`/`media`/`lejos`/`fuera_de_alcance` a cinco valores narrativos más cercanos al lenguaje de mesa: `cuerpo_a_cuerpo`/`corta`/`media`/`larga`/`fuera_de_alcance`. Documentado el principio: el combate es importante en D&D y se resuelve de forma conversacional, sin grid/casillas/medición exacta, reinterpretando narrativamente reglas como flanqueo o ataques de oportunidad en vez de eliminarlas. Deja preparada (solo documentación) la base de F5.2: iniciativa narrativa, turnos, reacciones, ataques de oportunidad narrativos, flanqueo narrativo, ventaja/desventaja narrativa.

**Archivos.** `esquemas/combate.py` + `estado/combate.py` + `herramientas/combate.py` ✅ F5.1 (distancias revisadas en F5.1.1).

**Tests.** `tests/test_combate_narrativo.py`, `tests/test_tools_combate.py` ✅ F5.1 / F5.1.1.

**Definición de hecho (F5.1 / F5.1.1).** El agente ya puede gestionar combates
narrativos mínimos con enemigos simples y daño auditable, con vocabulario y
distancias alineadas al estilo D&D narrativo sin grid, pero aún no
implementa el combate táctico completo de D&D (iniciativa real, grid,
economía de acciones, reacciones mecánicas, salvaciones de muerte,
resistencias, hechizos, balance automático ni IA táctica enemiga).

*Pendiente (subfases futuras, sin numerar todavía).* F5.2 — integración
narrativa de combate: iniciativa narrativa, turnos, reacciones, ataques de
oportunidad narrativos, flanqueo narrativo, ventaja/desventaja narrativa, y
sugerir/registrar consecuencia narrativa al terminar un combate, sin
automatizarlo demasiado. Más adelante: condiciones, ataques con tirada real,
si el diseño narrativo lo justifica.

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
