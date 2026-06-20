# ADR-0018 — Combate D&D narrativo: iniciativa, turnos y ataques básicos sin grid

- **Estado:** Aceptada (F5.1.1 / F5.2 / F5.3, 2026-06-20)
- **Implementación:** `combate.tirar_iniciativa`, `combate.turno_actual`,
  `combate.avanzar_turno` (F5.2); `combate.atacar_enemigo`,
  `combate.atacar_personaje` (F5.3) — ver
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
debe confirmarlo antes de que se aplique**. No hay aplicación automática de
mecánica de reacciones en ninguna fase actual.

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
- `ResultadoAtaque` (F5.3) es un `dataclass` interno de
  `herramientas/combate.py`, no un campo persistido de `CombateNarrativo`:
  se vuelca a evento auditable y a la respuesta de la tool, no se guarda un
  historial de ataques.
- `combate.*` sigue siendo la API canónica: no se introduce `conflicto.*` ni
  ningún otro vocabulario alternativo.

## No implementado a propósito

**F5.2:** ataques completos con tirada contra CA, IA táctica enemiga,
mecánica de reacciones/ataques de oportunidad/flanqueo/cobertura, áreas de
efecto, hechizos, sorpresa, XP automática, grid/casillas, RAG, memoria
vectorial ni streaming.

**F5.3:** IA enemiga / selección automática de acciones, acciones/reacciones
completas, ataques de oportunidad mecánicos, flanqueo mecánico,
ventaja/desventaja, cobertura mecánica, hechizos, áreas de efecto,
resistencias/vulnerabilidades, salvaciones, XP automática, grid/casillas,
RAG, memoria vectorial ni streaming. Solo queda la arquitectura y la
documentación preparadas para fases futuras (F5.4: ventaja/desventaja y
críticos más ricos).
