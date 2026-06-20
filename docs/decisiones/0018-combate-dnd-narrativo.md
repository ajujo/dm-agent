# ADR-0018 — Combate D&D narrativo: iniciativa, turnos, ataques, ventaja/desventaja y reacciones propuestas sin grid

- **Estado:** Aceptada (F5.1.1 / F5.2 / F5.3 / F5.4 / F5.5, 2026-06-20)
- **Implementación:** `combate.tirar_iniciativa`, `combate.turno_actual`,
  `combate.avanzar_turno` (F5.2); `combate.atacar_enemigo`,
  `combate.atacar_personaje` (F5.3, ventaja/desventaja y modificador
  situacional añadidos en F5.4); `combate.registrar_accion_turno`,
  `combate.proponer_reaccion`, `combate.resolver_reaccion`,
  `combate.listar_reacciones` (F5.5) — ver
  [`../estado/combate.md`](../estado/combate.md) y
  [`../tools/combate.md`](../tools/combate.md). Complementa
  [ADR-0017](0017-dnd55-narrativo-solitario.md), que fija el principio general
  de D&D 5.5 narrativo en solitario / teatro de la mente.

## Contexto

F5.1 introdujo combate narrativo mínimo (enemigos simples, daño, distancias
relativas). F5.1.1 alineó el vocabulario con D&D sin introducir grid. La
pregunta abierta era: ¿cómo dar estructura D&D real al combate —iniciativa,
turnos— sin caer en simulación táctica de tablero (VTT encubierto)?

## Decisión

> El combate **importa** y **se resuelve con vocabulario D&D** (iniciativa,
> turno, ronda, ataque, reacción, flanqueo, ventaja/desventaja), pero la
> resolución es **narrativa/conversacional**: sin grid, sin casillas, sin
> medición exacta.

### D-COMBATE-01 — Iniciativa clásica

La iniciativa usa `1d20 + mod_destreza`, igual que D&D. No es un orden
narrativo inventado: es una tirada real, con su aleatoriedad real.

### D-COMBATE-02 — Tiradas de enemigos automáticas

El DM Agent tira automáticamente por los enemigos (iniciativa, y en el
futuro ataques). El jugador no necesita introducir las tiradas de los
enemigos; solo resuelve las propias cuando aplique.

### D-COMBATE-03 — Dificultad por encuentro, no por modo global

No hay un modo heroico/gritty global que ajuste toda la campaña. La
peligrosidad de un combate depende del encuentro y de la aventura concretos,
decidida por el DM (LLM) caso a caso, no por un parámetro de configuración.

### D-COMBATE-04 — Reacciones y ataques de oportunidad: propuesta, no automatismo

El agente puede **proponer** una reacción o un ataque de oportunidad
narrativo cuando la ficción lo justifique (p. ej. alguien abandona
`cuerpo_a_cuerpo` de forma arriesgada y sin cubrirse), pero **el jugador
debe confirmarlo antes de que se aplique**. Desde F5.5 existe la tool para
proponer y resolver (`combate.proponer_reaccion`/`combate.resolver_reaccion`),
pero ni proponer ni confirmar **aplican nada**: no hay aplicación
automática de mecánica de reacciones en ninguna fase actual.

## Turnos narrativos, no turnos de tablero

`ronda` e `indice_turno_actual` (en `CombateNarrativo`) llevan la cuenta de
quién actúa y cuántos ciclos han pasado, pero "turno" no implica movimiento
medido en casillas/pies: es solo el orden de quién narra su acción ahora.
`combate.avanzar_turno` es una decisión explícita del DM (LLM), no un reloj
automático.

## Reglas tácticas adaptables (no eliminadas, reinterpretadas)

Reglas como flanqueo, ataques de oportunidad, cobertura, áreas de efecto o
movimiento no se eliminan: se reinterpretan de forma narrativa cuando
aparecen en la ficción, en vez de calcularse geométricamente.

- **Flanqueo narrativo:** puede conceder ventaja si el enemigo está
  distraído, acorralado o presionado desde dos frentes, sin calcular
  casillas.
- **Ataque de oportunidad narrativo:** puede activarse si alguien abandona
  `cuerpo_a_cuerpo` de forma arriesgada y sin cubrirse, sin contar casillas.
  Sujeto a D-COMBATE-04: se propone, el jugador confirma.
- **Cobertura narrativa:** puede dar ventaja/desventaja o modificar la
  dificultad si la ficción lo justifica, sin geometría exacta.
- **Área de efecto narrativa:** puede afectar a un objetivo, a varios
  cercanos o a una zona, según la ficción, sin medir conos/radios.

## Ataques básicos contra CA (F5.3)

`1d20 + modificador_ataque` contra la `ca` del objetivo, exactamente como en
D&D: natural 1 falla siempre, natural 20 impacta siempre. No hay todavía IA
enemiga ni selección automática de acciones — el DM (LLM) decide cuándo,
quién y con qué modificador/daño ataca cada enemigo; las tools solo
resuelven el ataque que se les pide.

### Críticos: duplicar dados, no el modificador

Un natural 20 duplica el número de dados de daño (no el modificador
estático): `1d8+3` se convierte en `2d8+3`. Resultó limpio de implementar
(transformar la expresión con una regex antes de tirar, reutilizando el
mismo motor de dados) y es la regla estándar de D&D, así que se hizo en
F5.3 en vez de posponerlo. No hay otras reglas de crítico (rangos de
amenaza ampliados, daño extra por rasgo de clase, etc.) — eso queda para
fases futuras si hace falta.

### Daño al personaje: un solo evento, no dos

`combate.atacar_personaje` aplica el daño directamente sobre `Ficha` (vía
`GestorEstado`) y registra **solo** `ataque_personaje_resuelto`, en vez de
delegar en `hp_xp.aplicar_daño`. Hacerlo así evita registrar dos eventos
distintos (`ataque_personaje_resuelto` + `daño_aplicado`) para la misma
acción narrativa, lo que sería ruido auditable incoherente: un ataque es un
solo hecho de juego, no dos. El daño al personaje **fuera** de un ataque
resuelto (curación, daño narrado a mano, etc.) sigue pasando por
`hp_xp.*` sin cambios.

### Distancia informativa, no bloqueante

La `distancia` del enemigo no se usa para validar si un ataque es legal en
F5.3: es solo una señal narrativa para que el DM decida si el ataque tiene
sentido en la ficción (una espada normalmente pide `cuerpo_a_cuerpo`; un
arco puede funcionar a `media`/`larga`). Introducir una validación dura de
alcance queda documentado como posible trabajo futuro, no como deuda
urgente.

### Atacar no avanza turno

`combate.atacar_enemigo`/`combate.atacar_personaje` no llaman a
`combate.avanzar_turno`: el avance de turno sigue siendo una decisión
explícita del DM (LLM), igual que en F5.2. Acoplar "atacar" con "avanzar
turno" habría asumido una economía de acciones rígida (una acción = un
ataque = fin de turno) que F5.3 deliberadamente no impone.

## Ventaja/desventaja y modificadores narrativos simples (F5.4)

Mecánica clásica de D&D, sin acumulación: `modo_tirada` (`normal`/`ventaja`/
`desventaja`) decide si se tira 1d20 o 2d20 (quedándose con el mayor/menor);
`modificador_situacional` (-10..10) suma o resta al total junto con
`modificador_ataque`. Natural 1/20 se evalúa **sobre la tirada elegida**: en
ventaja, `[1, 20]` es un crítico (se elige 20); en desventaja, `[1, 20]` es
una pifia (se elige 1).

### Cancelación es responsabilidad de quien llama, no de la tool

D&D dice que ventaja y desventaja simultáneas se cancelan y se tira normal.
F5.4 no implementa esa lógica de cancelación dentro de la tool: el campo
`modo_tirada` acepta **un solo valor final**, así que si el DM detecta
ventaja y desventaja a la vez, simplemente pasa `modo_tirada="normal"` él
mismo. Decidimos no construir un sistema de acumulación de fuentes de
ventaja/desventaja en esta fase — sería complejidad táctica (rastrear
cuántas fuentes, de dónde, con qué prioridad) que no aporta nada al estilo
narrativo sin grid y que F5.1.1 explícitamente quiere evitar.

### Total real, no mockeado: rediseño del helper de tirada

F5.3 tenía `_tirar_ataque_d20(mod, semilla) -> (natural, total)`, que
calculaba el total internamente. Para soportar ventaja/desventaja (que
necesita decidir *cuál* de dos tiradas se usa antes de poder calcular el
total) se sustituyó por `_tirar_tiradas_ataque(modo_tirada, semilla) ->
list[int]`, que solo tira dados brutos; el total
(`tirada_elegida + modificador_ataque + modificador_situacional`) se calcula
después, fuera del helper de dados. Esto rompe la compatibilidad de mocking
de los tests de F5.3 (que mockeaban `_tirar_ataque_d20` con un total
arbitrario); se actualizaron para mockear `_tirar_tiradas_ataque` con la(s)
tirada(s) bruta(s) y dejar que el total salga del cálculo real.

### `motivo_modificador` es narrativo, no mecánico

El campo existe para que quede auditado *por qué* hubo ventaja/desventaja o
modificador situacional ("la rata está distraída por el fuego"), no para
codificar una regla. El DM (LLM) puede proponer ventaja/desventaja a partir
de la escena, pero la decisión de si aplica de verdad la confirma el
jugador antes de que la tool se llame con ese `modo_tirada` — mismo
principio que D-COMBATE-04 para reacciones/ataques de oportunidad.

## Acciones de turno y propuestas de reacción (F5.5)

Dos piezas mínimas, sin motor completo de economía de acciones:

### `AccionTurno` registra, no arbitra

`combate.registrar_accion_turno` solo anota qué hizo un participante; no
valida si "le quedaba acción", "acción adicional" o "reacción" disponible.
`tipo` es texto libre (no `Literal`), igual que `EnemigoCombate.estado`:
construir un árbitro de economía de acciones es explícitamente fuera de
alcance ("no sobrevalides todavía"). Si `turno_participante_id` no coincide
con el turno actual, la tool **avisa** (`aviso` en la respuesta) en vez de
fallar — registrar fuera de turno puede ser legítimo (anotaciones a
posteriori, jugadores narrando en paralelo, etc.), así que bloquear habría
sido más perjudicial que útil.

### `PropuestaReaccion` nunca se auto-aplica

`combate.proponer_reaccion` crea la propuesta; `combate.resolver_reaccion`
la mueve a `confirmada`/`rechazada`/`caducada`. **Ninguna de las dos tira
dados ni toca HP.** Esto es deliberado y es el núcleo de D-COMBATE-04: si
"confirmar" aplicara el ataque automáticamente, estaríamos construyendo el
automatismo que estas fases evitan explícitamente. Aplicar de verdad una
reacción confirmada exige una llamada aparte, explícita, del DM (LLM) a
`combate.atacar_personaje`/`combate.atacar_enemigo` — el flujo completo
(detectar → proponer → confirmar → **aplicar**) tiene cuatro pasos, y F5.5
solo cubre los tres primeros como tools.

### `estado` sí es un enum cerrado; `tipo` no

A diferencia de `AccionTurno.tipo` (texto libre), `PropuestaReaccion.estado`
es un `Literal` (`pendiente`/`confirmada`/`rechazada`/`aplicada`/`caducada`)
porque `combate.resolver_reaccion` depende de esos valores exactos para
decidir su comportamiento — no es vocabulario narrativo sugerido, es estado
de máquina. `PropuestaReaccion.tipo` sí queda libre por la misma razón que
en `AccionTurno`: es solo contexto narrativo de qué clase de reacción es.

### `ronda`/`turno_participante_id` se derivan, no se piden

`combate.proponer_reaccion` no exige `ronda` ni `turno_participante_id` en
la entrada: se rellenan automáticamente desde
`CombateNarrativo.ronda`/`orden_iniciativa[indice_turno_actual]` si ya se
tiró iniciativa (si no, `turno_participante_id` queda `None`). Pedírselos
al llamador habría sido redundante con datos que el combate ya tiene.

## Consecuencias

- `EnemigoCombate` gana `mod_destreza` e `iniciativa` opcionales (default
  `None`/tratado como `0`); enemigos creados antes de F5.2 no necesitan
  migrarse.
- `CombateNarrativo` gana `orden_iniciativa` (`EntradaIniciativa[]`),
  `indice_turno_actual` y `ronda`. El personaje jugador aparece como
  participante de iniciativa aunque su HP sigue gestionándose en
  `Ficha`/`hp_xp.*`.
- Las tiradas reutilizan el motor de dados existente
  (`dm_agent.herramientas.dados.tirar`); deterministas con `semilla` para
  tests, aleatorias de verdad en runtime sin ella.
- `ResultadoAtaque` (F5.3, ampliado en F5.4 con `modo_tirada`/`tiradas_d20`/
  `modificador_situacional`/`motivo_modificador`) es un `dataclass` interno
  de `herramientas/combate.py`, no un campo persistido de
  `CombateNarrativo`: se vuelca a evento auditable y a la respuesta de la
  tool, no se guarda un historial de ataques.
- `combate.*` sigue siendo la API canónica: no se introduce `conflicto.*` ni
  ningún otro vocabulario alternativo.
- Sin los campos nuevos de F5.4 (`modo_tirada`, `modificador_situacional`,
  `motivo_modificador`), el comportamiento de `combate.atacar_enemigo`/
  `combate.atacar_personaje` es idéntico a F5.3 — los tres tienen default
  (`"normal"`, `0`, `null`) que reproducen exactamente la mecánica anterior.
- `CombateNarrativo` gana `acciones_turno` (`AccionTurno[]`) y
  `propuestas_reaccion` (`PropuestaReaccion[]`), ambos con default `[]`:
  combates creados antes de F5.5 no necesitan migrarse.

## No implementado a propósito

**F5.2:** ataques completos con tirada contra CA, IA táctica enemiga,
mecánica de reacciones/ataques de oportunidad/flanqueo/cobertura, áreas de
efecto, hechizos, sorpresa, XP automática, grid/casillas, RAG, memoria
vectorial ni streaming.

**F5.3:** IA enemiga / selección automática de acciones, acciones/reacciones
completas, ataques de oportunidad mecánicos, flanqueo mecánico,
ventaja/desventaja, cobertura mecánica, hechizos, áreas de efecto,
resistencias/vulnerabilidades, salvaciones, XP automática, grid/casillas,
RAG, memoria vectorial ni streaming.

**F5.4:** flanqueo mecánico automático, ataques de oportunidad mecánicos,
cobertura mecánica, condiciones completas, hechizos, áreas de efecto,
salvaciones, IA enemiga, acciones/reacciones completas, acumulación
compleja de múltiples ventajas/desventajas, XP automática, grid/casillas,
RAG, memoria vectorial ni streaming.

**F5.5:** motor completo de acción/acción adicional/reacción/movimiento,
cálculo automático de flanqueo, ataques de oportunidad automáticos,
reacciones automáticas (confirmar una propuesta **no** la aplica), cobertura
mecánica, condiciones completas, hechizos, áreas, salvaciones, IA enemiga
completa, XP automática, grid/casillas, RAG, memoria vectorial ni streaming.
Solo queda la arquitectura y la documentación preparadas para fases
futuras.
