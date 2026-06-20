# ADR-0018 — Combate D&D narrativo: iniciativa clásica y turnos sin grid

- **Estado:** Aceptada (F5.1.1 / F5.2, 2026-06-20)
- **Implementación:** `combate.tirar_iniciativa`, `combate.turno_actual`,
  `combate.avanzar_turno` (F5.2) — ver
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
- `combate.*` sigue siendo la API canónica: no se introduce `conflicto.*` ni
  ningún otro vocabulario alternativo.

## No implementado a propósito (F5.2)

No se crean en esta fase: ataques completos con tirada contra CA, IA táctica
enemiga, mecánica de reacciones/ataques de oportunidad/flanqueo/cobertura,
áreas de efecto, hechizos, sorpresa, XP automática, grid/casillas, RAG,
memoria vectorial ni streaming. Solo queda la arquitectura y la
documentación preparadas para fases futuras.
