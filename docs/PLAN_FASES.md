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
- **F5.1.1 — Alineación de combate D&D narrativo sin grid.** ✅ **Implementada** (commit `refactor: align combat distances with narrative D&D style`). Corrección de diseño, no de API: se conserva `combate.*` como nombre de tools (no se renombra a `conflicto.*`) y el vocabulario D&D (enemigo, ataque, daño, distancia). Las distancias abstractas pasan de `cerca`/`media`/`lejos`/`fuera_de_alcance` a cinco valores narrativos más cercanos al lenguaje de mesa: `cuerpo_a_cuerpo`/`corta`/`media`/`larga`/`fuera_de_alcance`. Documentado el principio: el combate es importante en D&D y se resuelve de forma conversacional, sin grid/casillas/medición exacta, reinterpretando narrativamente reglas como flanqueo o ataques de oportunidad en vez de eliminarlas. Deja preparada (solo documentación) la base de F5.2.
- **F5.2 — Iniciativa clásica y turnos narrativos.** ✅ **Implementada** (commit `feat: add initiative and narrative turns`). Iniciativa D&D real: `1d20 + mod_destreza` para el personaje, tirada automática para cada enemigo (D-COMBATE-01/02; [ADR-0018](decisiones/0018-combate-dnd-narrativo.md)). Nuevos esquemas `EntradaIniciativa` y campos `CombateNarrativo.{orden_iniciativa,indice_turno_actual,ronda}`, `EnemigoCombate.{mod_destreza,iniciativa}` (opcionales, sin migración necesaria). Tools `combate.{tirar_iniciativa,turno_actual,avanzar_turno}` con eventos `iniciativa_tirada`/`turno_avanzado`. Orden: mayor iniciativa primero, empate personaje > enemigo, empate entre enemigos estable por nombre/id. Tiradas vía el motor de dados existente (`herramientas/dados.py`), deterministas con `semilla` para tests. Reacciones/ataques de oportunidad/flanqueo narrativos quedan documentados (D-COMBATE-04: el agente los propone, el jugador confirma) pero **no implementados como mecánica**.
- **F5.3 — Ataques básicos contra CA y daño.** ✅ **Implementada** (commit `feat: add basic attack resolution`). `1d20 + modificador_ataque` contra CA, igual que D&D: natural 1 falla siempre, natural 20 impacta siempre (daño duplicado en dados, no modificador). Tools `combate.{atacar_enemigo,atacar_personaje}` con eventos `ataque_enemigo_resuelto`/`ataque_personaje_resuelto`. `combate.atacar_enemigo` reutiliza el umbral de estado de `combate.daño_enemigo`; `combate.atacar_personaje` aplica daño directamente sobre `Ficha` vía `GestorEstado` (deliberadamente sin llamar a `hp_xp.aplicar_daño`, para no duplicar evento — ver ADR-0018). Nuevo `ResultadoAtaque` (dataclass interno, no persistido). Ninguna de las dos tools avanza turno automáticamente: el avance sigue siendo explícito vía `combate.avanzar_turno`. `distancia` sigue siendo informativa, no bloquea ataques por alcance. Sin IA enemiga, sin selección automática de acciones.
- **F5.4 — Ventaja/desventaja y modificadores narrativos simples.** ✅ **Implementada** (commit `feat: add advantage and situational attack modifiers`). `modo_tirada` (`normal`/`ventaja`/`desventaja`) en `combate.{atacar_enemigo,atacar_personaje}`: ventaja/desventaja tiran 2d20 y eligen el mayor/menor; natural 1/20 se evalúa sobre la tirada elegida. `modificador_situacional` (-10..10) más `motivo_modificador` (texto narrativo) se suman al total junto con `modificador_ataque`. Sin campos nuevos, comportamiento idéntico a F5.3. Si ventaja y desventaja coinciden, se cancelan conceptualmente y quien llama pasa `modo_tirada="normal"` — la tool no acumula ni resuelve múltiples fuentes. `ResultadoAtaque` ampliado con `modo_tirada`/`tiradas_d20`/`modificador_situacional`/`motivo_modificador`; eventos `ataque_*_resuelto` incluyen los mismos campos nuevos.
- **F5.5 — Acciones de turno y propuestas de reacción.** ✅ **Implementada** (commit `feat: add turn actions and reaction proposals`). Nuevos esquemas `AccionTurno` (registro narrativo de qué hizo un participante, sin validar economía de acciones) y `PropuestaReaccion` (reacción/ataque de oportunidad propuesto, ciclo `pendiente`→`confirmada`/`rechazada`/`caducada`); campos `CombateNarrativo.{acciones_turno,propuestas_reaccion}` (default `[]`, sin migración). Tools `combate.{registrar_accion_turno,proponer_reaccion,resolver_reaccion,listar_reacciones}` con eventos `accion_turno_registrada`/`reaccion_propuesta`/`reaccion_resuelta`. **Ni proponer ni confirmar aplican el ataque/reacción**: aplicar de verdad exige llamar explícitamente a `combate.atacar_personaje`/`combate.atacar_enemigo` aparte (D-COMBATE-04, "el agente propone, el jugador confirma"). `registrar_accion_turno` avisa (no falla) si el participante no coincide con el turno actual. Sin motor completo de economía de acciones, sin flanqueo/ataques de oportunidad automáticos.
- **F5.6 — Prueba integrada manual de combate.** ✅ **Implementada** (commit `test: add integrated combat manual validation`). **No añade reglas ni mecánicas nuevas**: es validación/documentación. Guía manual `docs/PRUEBA_MANUAL_F5_COMBATE.md` (escena de prueba, prompts sugeridos, flujo esperado de tools, rutas en disco a verificar, criterios de aceptación, troubleshooting) y escena de referencia `docs/escenarios/mini_aventura_combate.md`. Test automatizado `tests/test_combate_integrado_f5.py` (sin red, sin LLM real, `tmp_path`) cubre extremo a extremo: ficha → iniciar combate → añadir enemigo → iniciativa → atacar con ventaja → registrar acción de turno → proponer reacción → confirmar (sin aplicar daño) → aplicar la reacción confirmada con una llamada explícita de ataque → avanzar turno → terminar combate → verificar los 10 eventos auditables principales.

**Archivos.** `esquemas/combate.py` + `estado/combate.py` + `herramientas/combate.py` ✅ F5.1 (distancias revisadas en F5.1.1, iniciativa/turnos en F5.2, ataques en F5.3, ventaja/desventaja en F5.4, acciones/reacciones en F5.5); `docs/PRUEBA_MANUAL_F5_COMBATE.md` + `docs/escenarios/mini_aventura_combate.md` ✅ F5.6 (sin cambios de código de reglas).

**Tests.** `tests/test_combate_narrativo.py`, `tests/test_tools_combate.py` ✅ F5.1 / F5.1.1 / F5.2 / F5.3 / F5.4 / F5.5; `tests/test_iniciativa_turnos.py` ✅ F5.2; `tests/test_ataques_combate.py` ✅ F5.3 / F5.4; `tests/test_reacciones_combate.py` ✅ F5.5; `tests/test_combate_integrado_f5.py` ✅ F5.6.

**Definición de hecho (F5.1 / F5.1.1 / F5.2 / F5.3 / F5.4 / F5.5 / F5.6).**
El agente ya puede gestionar combates narrativos mínimos con enemigos
simples y daño auditable, con vocabulario y distancias alineadas al estilo
D&D narrativo sin grid; ya puede **tirar iniciativa clásica y avanzar
turnos narrativos**; ya puede **resolver ataques básicos contra CA y
aplicar daño**, con **ventaja/desventaja y modificadores narrativos
simples**; ya puede **registrar acciones de turno y
proponer/rechazar/confirmar reacciones narrativas, sin aplicarlas
automáticamente**; y el proyecto ya tiene una **guía de prueba funcional
para jugar una escena corta de combate narrativo D&D sin grid**, validada
también con un test integrado sin red. Aún no implementa IA enemiga,
selección automática de acciones, motor completo de economía de acciones,
reacciones/ataques de oportunidad/flanqueo mecánicos automáticos,
cobertura mecánica, áreas de efecto, sorpresa, salvaciones de muerte,
resistencias, hechizos, balance automático ni XP automática.

*Pendiente (subfases futuras, sin numerar todavía).* Integración narrativa
de combate (sugerir/registrar consecuencia al terminar, sin automatizarlo
demasiado); aplicar de verdad una reacción confirmada de forma más fluida
(hoy requiere una llamada aparte explícita); flanqueo/cobertura calculados
automáticamente; IA enemiga simple; más adelante, condiciones, si el diseño
narrativo lo justifica.

---

## F6.1 — Disciplina de uso de tools y refuerzo del prompt (robustez del agente)

> No es parte de la "Fase 6" de creación de mundo (más abajo): es una
> corrección de robustez del agente, descubierta durante la prueba manual de
> F5.6 con un endpoint real (vLLM, perfil `rapido`).

**Objetivo.** ✅ **Implementada** (commit `fix: enforce tool use discipline`).
Durante la prueba manual real, el modelo respondió a veces con un bloque de
texto tipo `[{"name": "ficha_leer", "arguments": {...}}]` simulando una tool
call sin ejecutarla de verdad — y siguió haciéndolo incluso después de que el
usuario le pidiera explícitamente no hacerlo. F6.1 corrige esto en dos
frentes: el system prompt y un detector con reintento en el agent loop. **No
añade mecánicas de combate ni reglas nuevas.**

- **Prompt** (`src/dm_agent/prompts/system_dm_minimo.md`, también actualizado
  para reflejar que ficha/HP/inventario/combate/memoria narrativa **sí**
  existen ya — el texto original de F2.2 decía lo contrario): nueva sección
  "REGLA ABSOLUTA SOBRE HERRAMIENTAS" (prohíbe explícitamente escribir tool
  calls como texto/JSON; exige decir "No puedo ejecutar esa herramienta en
  este turno" si no puede usarla; prohíbe afirmar "he leído/guardado/
  tirado/atacado/dañado/avanzado turno/cerrado sesión" sin tool real),
  "ESTADO MECÁNICO" (lista cerrada de qué cambios requieren tool real),
  regla de campaña/personaje por defecto (no inventar `campaña_id`/
  `personaje_id`), y regla de no duplicar combates (`combate_estado` antes de
  `combate_iniciar` si puede haber uno activo).
- **Detector + reintento** (`src/dm_agent/nucleo/agente.py`):
  `_contiene_tool_call_simulada` reconoce el patrón `"name"`+`"arguments"`
  típico de una tool call simulada en texto **sin parsearlo ni ejecutarlo**
  (sería peligroso). Cuando la respuesta no trae `tool_calls` reales pero
  contiene ese patrón, `AgenteDM.responder` reintenta **una sola vez** por
  turno con un mensaje correctivo; en `--debug` siempre imprime un aviso. Si
  el modelo insiste tras el reintento, se devuelve tal cual (no hay bucle).

---

## F6.1.1 — Detección de tool calls simuladas en XML/pseudo-call

> Igual que F6.1: no es parte de "Fase 6" de creación de mundo. Corrección de
> robustez descubierta en una segunda prueba manual real: el detector de
> F6.1 avisó correctamente sobre JSON simulado, pero el modelo volvió a
> simular una tool call con otro formato (`<call:name="...">`).

**Objetivo.** ✅ **Implementada** (commit `fix: detect xml-style simulated
tool calls`). Amplía `_contiene_tool_call_simulada` para reconocer también
pseudo-calls en XML (`<call:name="...">`, `<call:param="...">`, `</call:>`)
y etiquetas tipo `<tool_call>`/`<tool>`, sin cambiar la política: solo
detectar, avisar en `--debug` y reintentar una vez por turno (nunca parsear
ni ejecutar el contenido simulado). El mensaje correctivo ahora nombra
explícitamente ambos formatos prohibidos (JSON y XML/pseudo-call), y el
system prompt incluye ambos ejemplos prohibidos. **No añade mecánicas de
combate ni reglas nuevas.**

---

## F6.2 — Filtrado contextual de tools y diagnóstico de tool-calling

> Igual que F6.1/F6.1.1: no es parte de "Fase 6" de creación de mundo.
> Corrección de robustez descubierta en una tercera prueba manual real: tras
> F6.1.1, `ficha_leer`/`combate_estado`/`combate_tirar_iniciativa` ya
> funcionaban como tool calls reales, pero `combate_atacar_enemigo` seguía
> fallando como pseudo-call `<tool_call>` incluso pidiéndoselo explícitamente
> al modelo. Diagnóstico: no es la tool en sí, es disciplina de tool-calling
> del modelo local degradándose con muchas tools/schemas complejos a la vez.

**Objetivo.** ✅ **Implementada** (commit `fix: filter tools by turn
context`). Para mejorar la probabilidad de tool calls reales, `dm-agent` ya
no ofrece siempre las ~45 tools disponibles: filtra el conjunto expuesto al
LLM según la intención del mensaje del turno. **No añade mecánicas de
combate ni reglas nuevas; no toca esquemas de combate, lógica de ataque,
daño, iniciativa, memoria narrativa, RAG ni streaming.**

- **Selector contextual** (`src/dm_agent/nucleo/seleccion_tools.py`, nuevo):
  `seleccionar_tools_para_turno(mensaje_usuario, historial=None,
  estado_opcional=None)` reconoce por palabra clave (sin acentos, sin LLM,
  determinista) siete categorías — ficha, inventario, combate general,
  ataque, iniciativa/turno, reacción, memoria/sesión — y devuelve el
  conjunto de nombres API de tools relevante. Las categorías específicas de
  combate (ataque/iniciativa/reacción) son subconjuntos pequeños que tienen
  prioridad sobre el conjunto completo de las 14 tools de combate: si
  alguna coincide, no se cae al conjunto general aunque también coincidan
  palabras genéricas de combate. Si no se reconoce ninguna categoría,
  devuelve `None` (fallback seguro: ofrecer todas las tools, el
  comportamiento anterior a F6.2).
- **Aplicación en el agent loop** (`src/dm_agent/nucleo/agente.py`):
  `AgenteDM._tools_para_turno` filtra `RegistroHerramientas.
  esquemas_disponibles()` con ese conjunto antes de cada turno (estable
  durante todo el turno, no por iteración). En `--debug` siempre imprime
  `[debug] tools expuestas: ...` con los nombres reales que se enviaron al
  LLM, para poder diagnosticar si un modelo sigue simulando tool calls
  porque ve demasiadas, o porque falta una en la lista filtrada.
- **No se cambia la política de F6.1/F6.1.1**: el detector de tool calls
  simuladas y el reintento corrector siguen igual; el filtrado de tools es
  una capa independiente para reducir la *probabilidad* de que el modelo
  necesite simular nada, no un sustituto de la disciplina existente.

---

## F6.3 — Robustez contra tool calls duplicadas, respuestas vacías y tool explícita no ejecutada

> Igual que F6.1/F6.1.1/F6.2: no es parte de "Fase 6" de creación de mundo.
> Tres fallos de robustez observados ya con tool calls reales funcionando
> (F6.2): el modelo repitió `combate_proponer_reaccion` dos veces con los
> mismos argumentos (dos reacciones pendientes duplicadas); después, al
> pedirle confirmar una reacción con `combate_resolver_reaccion`, el modelo
> devolvió un turno sin texto y sin tool call, dejando la reacción pendiente
> sin resolver y sin ningún error visible.

**Objetivo.** ✅ **Implementada** (commit `fix: harden agent tool execution
loop`). Tres defensas en `AgenteDM`, todas dentro del agent loop, ninguna
toca mecánica de juego:

- **(A) Deduplicación de tool calls idénticas en el mismo turno**
  (`src/dm_agent/nucleo/agente.py`): dentro de `responder()`, un conjunto
  `tool_calls_ejecutadas` (clave `(nombre_api, argumentos_json con
  sort_keys)`) persiste mientras dura el turno (across iteraciones del
  bucle `max_iter_turno`, se reinicia en cada llamada a `responder()`). Si
  el modelo repite exactamente la misma tool+argumentos, la segunda vez no
  se llama `dispatch_api`: se le devuelve un resultado sintético
  ("ya se ejecutó con estos mismos argumentos en este turno") y en
  `--debug` se imprime `[debug] tool duplicada ignorada: ...`. Argumentos
  distintos, o la misma llamada en un turno posterior, se ejecutan con
  normalidad.
- **(B) Respuesta vacía sin tool calls**: si la respuesta final no tiene
  texto útil (`content` vacío/solo espacios) y tampoco hubo tool calls en
  ese paso, se devuelve un mensaje seguro pidiendo reformular en vez de un
  turno en blanco; en `--debug`, `[debug] respuesta vacía del modelo sin
  tool calls`.
- **(C) Tool explícita mencionada pero no ejecutada**: si el mensaje del
  usuario nombra por su nombre API alguna de las tools expuestas en el turno
  (`_tools_para_turno`) y, al llegar a una respuesta sin tool calls, esa
  tool todavía no se ejecutó de verdad, se dispara **un único** reintento
  corrector (mensaje explícito pidiendo llamar la tool real, prohibiendo
  JSON/XML). Si tras el reintento sigue sin ejecutarla, la respuesta final
  es "No se ha podido ejecutar la herramienta solicitada: ..." — nunca se
  inventa que se ejecutó.
- **Prioridad de chequeos** (en este orden, dentro de la rama "sin tool
  calls"): primero F6.1/F6.1.1 (pseudo-call simulada → su propio reintento,
  sin parsear/ejecutar nada); solo si no hay pseudo-call, (C) tool explícita
  no ejecutada; solo si tampoco aplica (C), (B) respuesta vacía. Esto
  garantiza que F6.3 nunca reemplaza ni debilita la disciplina anti-pseudo-
  call de F6.1/F6.1.1.

---

## F6.4 — Comando manual `/tool` (depuración/recuperación sin LLM)

> Igual que F6.1-F6.3: no es parte de "Fase 6" de creación de mundo. Incluso
> con F6.3 detectando correctamente "el usuario pidió una tool explícita y
> el modelo no la llamó" y reintentando, hay modelos locales que **siguen**
> sin emitir la tool call real tras el reintento, pese a instrucciones
> explícitas con todos los argumentos. Hace falta una vía de recuperación
> que no dependa de que el modelo coopere.

**Objetivo.** ✅ **Implementada** (commit `feat: add manual tool command`).
Comando `/tool <nombre_tool_api> <json_argumentos>` en el REPL: ejecuta una
tool real **directamente**, sin pasar por el LLM. **No añade mecánicas de
combate ni reglas nuevas; no toca esquemas de combate, lógica de ataque,
daño, iniciativa, inventario, ficha ni memoria narrativa.**

- **Parser testeable** (`src/dm_agent/nucleo/bucle.py`):
  `parsear_comando_tool(linea) -> (nombre_api, argumentos)` separa el nombre
  de la tool del JSON de argumentos y valida que decodifique a un objeto;
  lanza `ErrorComandoTool` (mensaje legible) si falta algo o el JSON es
  inválido — nunca rompe el REPL.
- **Ejecución** (`SesionInteractiva.ejecutar_tool_manual`): resuelve el
  nombre API contra `RegistroHerramientas` (error controlado si no existe) y
  llama `dispatch_api` de verdad — los cambios se persisten igual que una
  tool llamada por el LLM. El resultado se muestra formateado:
  `[tool] <nombre> -> ok=<bool>` + JSON con indentación.
  Se registra como `tool_call`/`tool_result` en `Sesion` (mismo rastro de
  auditoría que deja el LLM), pero **no** como turno `user`/`assistant`: no
  entra en el historial conversacional que `AgenteDM` reinyecta al LLM.
- **REPL** (`repl()` en `bucle.py`): nueva entrada en `COMANDOS` (aparece en
  `/ayuda`); las líneas que empiezan por `/tool` se enrutan a
  `ctx.ejecutar_tool_manual(...)` antes del catch-all de "comando
  desconocido", sin pasar por `ctx.procesar()` (el camino que sí llama al
  LLM).
- **No interactúa con F6.1/F6.1.1/F6.3**: `/tool` solo se dispara cuando el
  usuario escribe `/tool` explícitamente; nunca parsea ni ejecuta texto que
  el modelo haya escrito (JSON/XML simulado sigue sin ejecutarse jamás).

**Archivos.** `src/dm_agent/prompts/system_dm_minimo.md`,
`src/dm_agent/nucleo/agente.py`.

**Tests.** `tests/test_tool_discipline.py` (prompt + detector + reintento
único, sin red ni LLM real).

**Definición de hecho.** El prompt prohíbe explícitamente tool calls
simuladas en JSON y exige tool real para cualquier cambio de estado
mecánico; el agent loop detecta el patrón y reintenta una vez antes de
rendirse. No corrige el modelo si este ignora la instrucción tras el
reintento — eso es comportamiento del modelo, no algo que `dm-agent` pueda
forzar desde el cliente.

---

## F6.5 — Consolidación de ergonomía y robustez de combate

> Igual que F6.1-F6.4: no es parte de "Fase 6" de creación de mundo. Tras
> una prueba manual de combate completa de extremo a extremo (`tyr` vs.
> `rata_1`/`rata_2`, terminada con éxito vía `/tool combate_terminar`),
> aparecieron varias fricciones reales a la vez: placeholders inventados
> (`campaña_actual`, `combate_actual`, "Tyr" en vez de `tyr`), `/tool`
> incómodo para operaciones frecuentes, `combate_avanzar_turno` sin saltar
> enemigos derrotados, ninguna señal de "ya no queda ningún enemigo en
> pie", y una corrección manual de una acción narrativa mal registrada.

**Objetivo.** ✅ **Implementada** (commit `fix: improve combat repl
ergonomics`). Cinco mejoras de ergonomía/robustez, ninguna mecánica de D&D
nueva. **No se tocó** resolución de ataque, daño, tiradas, crítico/pifia,
inventario, ficha, memoria narrativa, RAG ni streaming.

- **(A) Trim de comandos REPL**: ya estaba resuelto desde F6.4.1
  (`entrada.strip()` antes de comparar contra cualquier comando); F6.5 lo
  reconfirma con tests explícitos para `/tool`, `/ayuda` y `/salir` con
  espacios iniciales.
- **(B) Contexto operativo activo** (`src/dm_agent/nucleo/
  contexto_operativo.py`, nuevo): `construir_bloque_contexto_operativo`
  deriva `campaña_id`/`personaje_id`/`combate_id`/`estado`/`ronda`/`turno
  actual` reales de `GestorCombateNarrativo.cargar_activo` (sin LLM, sin
  inventar nada) y los formatea en un bloque "CONTEXTO OPERATIVO ACTUAL"
  con una prohibición explícita de placeholders. `AgenteDM` lo inyecta como
  el **último** mensaje `system` antes del historial (después de la
  memoria narrativa, F4.3, para que pese más), y lo añade también al
  reintento corrector de F6.3 cuando el usuario pide una tool explícita no
  ejecutada. Si no hay combate activo, el bloque lo dice explícitamente
  ("sin combate activo detectado") y no falla.
- **(C) Comandos cómodos del REPL** (`SesionInteractiva` en `bucle.py`):
  `/combate`, `/turno`, `/reacciones`, `/ficha`, `/estado` — mismo
  mecanismo que `/tool` (`dispatch_api` directo, sin LLM), pero resolviendo
  `campaña_id`/`combate_id`/`personaje_id` solos a partir del combate
  activo, sin que el usuario tenga que escribir JSON. `/estado` es un
  resumen compacto y legible (ficha, combate, ronda, enemigos, reacciones
  pendientes), no JSON bruto. Todos muestran error controlado
  (`[comando] No hay combate activo detectado.` / `[comando] No se conoce
  personaje activo...`) si falta el dato; ninguno llama al LLM.
- **(D) `combate_avanzar_turno` salta enemigos derrotados**
  (`src/dm_agent/herramientas/combate.py`): nunca deja como turno actual a
  un enemigo con `estado == "derrotado"` o `hp_actual <= 0` — sigue
  avanzando hasta el siguiente participante activo (los personajes nunca se
  saltan). El resultado incluye `enemigos_derrotados_saltados` (ids
  saltados en esa llamada) y `todos_los_enemigos_derrotados`/
  `deberia_terminar_combate`.
- **(E) Señal `todos_los_enemigos_derrotados` en `combate_atacar_enemigo`**:
  mismos dos campos que en (D), añadidos cuando el ataque deja a todos los
  enemigos del combate derrotados. **Decisión: solo señaliza, no termina el
  combate automáticamente** — sigue haciendo falta un `combate_terminar`
  explícito (D-COMBATE-04), preferencia explícita del encargo sobre
  cerrar solo "si es sencillo y seguro".
- **(F) Recomendación de registro narrativo coherente** (documentación, sin
  código nuevo): registrar la acción narrativa después de ver el resultado
  real de la tool (`impacta`/`critico`/`pifia`/`dano`), no antes; si se
  comete un error, registrar una acción nueva de tipo `correccion` en vez
  de editar la anterior (no hay edición de acciones todavía). Sin comando
  `/corregir`: explícitamente no necesario en esta fase.

**Archivos.** `src/dm_agent/nucleo/contexto_operativo.py` (nuevo),
`src/dm_agent/nucleo/agente.py`, `src/dm_agent/nucleo/bucle.py`,
`src/dm_agent/herramientas/combate.py`.

**Tests.** `tests/test_contexto_operativo.py` (nuevo),
`tests/test_agent_tool_robustness.py` (ampliado, contexto en el reintento),
`tests/test_cli.py` (ampliado, comandos cómodos + trim),
`tests/test_iniciativa_turnos.py` (ampliado, salto de enemigos derrotados),
`tests/test_ataques_combate.py` (ampliado, señal todos derrotados).

---

## F6.5.1 — `system` único: el chat template de vLLM+Qwen3 rechaza más de uno

> Igual que F6.1-F6.5: no es parte de "Fase 6" de creación de mundo.
> Corrección de un bug crítico encontrado en una prueba manual real con
> `dm-agent --perfil rapido --nueva --debug`: vLLM rechazaba la petición
> entera con HTTP 400 (`ValueError: System message must be at the
> beginning.`), bloqueando *todo* turno de lenguaje natural con contexto
> operativo (F6.5-B) o memoria narrativa (F4.3) activos. Reproducido de
> forma aislada contra el endpoint real: el chat template de este modelo
> rechaza **más de un mensaje `system` en la petición, incluso si todos van
> al principio** — no es (solo) un problema de orden, sino de cardinalidad.

**Objetivo.** ✅ **Implementada** (commit `fix: keep system messages before
chat history`). Ningún mensaje `system` puede ir después del primer mensaje
no-`system`, y como ese chat template tampoco tolera varios `system`
consecutivos, `system_prompt` + bloque de memoria narrativa + bloque de
contexto operativo se fusionan en **un único** mensaje `system` inicial.
**No se tocó** ninguna mecánica de combate, tiradas, daño, ficha, inventario
ni memoria narrativa: solo el ensamblado de `messages` para el LLM.

- **`construir_mensajes_llm`** (nueva función en `src/dm_agent/nucleo/
  agente.py`): punto centralizado de construcción de `messages`. Recibe
  `system_prompt`, `bloque_memoria`, `bloque_contexto` y el historial
  user/assistant ya traducido, y devuelve siempre `[un único mensaje
  system, *historial]`. `AgenteDM._messages_base` delega en ella en vez de
  añadir varios mensajes `system` sueltos.
- **`_assert_system_al_principio`**: invariante centralizado (`assert`) que
  recorre los `messages` construidos y falla si encuentra un `system`
  después del primer mensaje no-`system`. Se ejecuta dentro de
  `construir_mensajes_llm`, así que cualquier regresión futura que vuelva a
  intentar inyectar un `system` tardío se detecta inmediatamente, no solo
  en producción contra el LLM real.
- El reintento corrector de tool explícita no ejecutada (F6.3-C/F6.5-B)
  sigue incluyendo los IDs reales activos, pero como texto dentro de un
  mensaje `user` sintético (igual que antes) — nunca como mensaje `system`
  adicional, así que no rompe el invariante.
- El bloque "CONTEXTO OPERATIVO ACTUAL" (F6.5-B) sigue inyectándose en cada
  turno con los mismos datos e idéntica prohibición de placeholders
  (`campaña_actual`, `combate_actual`, `personaje_actual`); solo cambia que
  ahora vive dentro del único mensaje `system`, no en uno propio.

**Archivos.** `src/dm_agent/nucleo/agente.py`.

**Tests.** `tests/test_orden_mensajes_llm.py` (nuevo: contexto operativo
presente, todos los `system` antes del primer `user`, ningún `system` tras
`user`/`assistant`/`tool`, el reprompt de tool explícita respeta el orden,
placeholders siguen prohibidos), `tests/test_agente_memoria.py` y
`tests/test_campaña_integrada_f4.py` (ajustados: ya no esperan dos mensajes
`system` separados, sino uno fusionado).

---

## F6.5.2c — Avisos no bloqueantes al atacar fuera del flujo normal

> Igual que F6.5.1-F6.5.2b: no es parte de "Fase 6" de creación de mundo.
> Corrección de fricción detectada durante pruebas manuales: el modelo
> atacaba sin tirar iniciativa, fuera de turno, o contra enemigos ya
> derrotados, sin que el agente pudiera advertirle de la anomalía.

**Objetivo.** ✅ **Implementada** — Añadir `"avisos": []` al resultado de
`combate_atacar_enemigo` y `combate_atacar_personaje` con advertencias
no bloqueantes cuando el ataque ocurre fuera del flujo normal de combate:
(1) sin iniciativa tirada, (2) fuera del turno actual, (3) contra enemigo
ya derrotado, (4) cuando todos los enemigos están derrotados. **Decisión:
los avisos no bloquean el ataque** — el LLM narra, las herramientas
señalizan, el jugador decide.

**Archivos.** `src/dm_agent/herramientas/combate.py` (ampliado).

**Tests.** `tests/test_ataques_combate.py` (ampliado, 8 tests nuevos).

---

### Nota: resolución de `tipo_dano` (D-COMBATE-08, diferido)

Durante pruebas A/B se observó que distintos backends/modelos generan variantes
de `tipo_dano` inconsistentes (`corte`, `punzante`, `puñalante`, `perforante`,
`cortante`). **Decisión: diferido** hasta que exista un sistema de inventario,
equipo, armas y ataques de criaturas con datos estructurados. La regla futura
es que el tipo de daño se derive del arma equipada, ataque definido o ficha de
criatura; el valor propuesto por el LLM será solo *fallback*. Ver
[DECISIONES_ABIERTAS.md](DECISIONES_ABIERTAS.md) § D-COMBATE-08 y
[BACKLOG.md](BACKLOG.md) #F5-12.

---

## F6.5.3a — Coherencia narrativa y avisos tras tools de combate

> Igual que F6.5.1-F6.5.2c: no es parte de "Fase 6" de creación de mundo.
> Corrección de coherencia narrativa detectada durante pruebas manuales:
> el modelo declaraba el combate terminado sin llamar `combate_terminar`,
> ignoraba los `avisos` que las herramientas devolvían, y en ocasiones
> devolvía una respuesta vacía tras ejecutar una tool correctamente.

**Objetivo.** ✅ **Implementada** — Cuatro mejoras de coherencia narrativa,
ninguna toca mecánica de combate:

- **(A) Prompt: no declarar combate terminado sin tool**
  (`src/dm_agent/prompts/system_dm_minimo.md`): nueva sección que prohíbe
  decir "el combate ha terminado" si `combate.estado` sigue siendo
  `"activo"`. Permite decir "todos los enemigos están derrotados" y exige
  llamar a `combate_terminar` para cerrar formalmente.
- **(B) Prompt: mencionar avisos en la narración**
  (`src/dm_agent/prompts/system_dm_minimo.md`): nueva sección que obliga
  a integrar los `avisos` del resultado de una tool en la narración, sin
  ocultarlos ni exagerarlos.
- **(C) Avisos simétricos en `combate_atacar_personaje`**
  (`src/dm_agent/herramientas/combate.py`): añade `"avisos": []` con las
  mismas comprobaciones que `combate_atacar_enemigo` (sin iniciativa, fuera
  de turno), para que los ataques enemigos también generen advertencias
  narrativas. El atacante es el enemigo (`enemigo_id`), por lo que el
  chequeo de turno compara contra `enemigo_id`.
- **(D) Fallback enriquecido tras tool ejecutada**
  (`src/dm_agent/nucleo/agente.py`): si el modelo devuelve una respuesta
  vacía tras ejecutar una tool con éxito, el mensaje fallback nombra la
  tool que se ejecutó para que el usuario sepa que la acción mecánica
  ocurrió aunque la narración esté vacía.

**Archivos.** `src/dm_agent/prompts/system_dm_minimo.md` (ampliado),
`src/dm_agent/herramientas/combate.py` (ampliado),
`src/dm_agent/nucleo/agente.py` (ampliado).

**Tests.** `tests/test_agent_tool_robustness.py` (6 tests nuevos: prompt
combat termination, prompt avisos mention, fallback enriquecido con tool,
fallback original sin tool), `tests/test_ataques_combate.py` (4 tests
nuevos: avisos en `atacar_personaje`).

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
