# Combate narrativo mínimo (F5.1, distancias en F5.1.1, iniciativa/turnos en F5.2, ataques en F5.3, ventaja/desventaja en F5.4)

> Módulos: `dm_agent.esquemas.combate` (`EnemigoCombate`, `EntradaIniciativa`,
> `CombateNarrativo`) · `dm_agent.estado.combate` (`GestorCombateNarrativo`) ·
> `dm_agent.herramientas.combate` (tools `combate.*`).
>
> Ver también [ADR-0018](../decisiones/0018-combate-dnd-narrativo.md) para el
> razonamiento completo de la iniciativa clásica y los turnos narrativos.

## El combate importa: vocabulario D&D, resolución narrativa

El combate es una parte importante de D&D y `dm-agent` **conserva su
vocabulario**: `combate`, `enemigo`, `iniciativa`, `turno`, `ataque`,
`reacción`, `flanqueo`, `ataque de oportunidad`, `ventaja`/`desventaja`. Lo
que cambia es cómo se **resuelve**: con teatro de la mente (D17) — distancias
relativas, posición narrativa y consecuencias — en vez de grid, casillas,
pies/pulgadas exactos, ataques de oportunidad mecánicos, cobertura
milimétrica, flanqueo geométrico, áreas de efecto medidas en
conos/líneas/radios, iniciativa compleja, economía completa de acciones,
reacciones mecánicas, salvaciones de muerte, resistencias/vulnerabilidades ni
hechizos. Ver también [ADR-0017](../decisiones/0017-dnd55-narrativo-solitario.md#combate-vocabulario-dd-resolución-narrativa).

Es una base mínima para sostener escenas de combate en teatro de la mente: el
DM (LLM) necesita recordar quién participa, quién está herido o caído, y
cuándo termina la escena, sin simular reglas tácticas de tablero (sin VTT
encubierto).

### Reglas tácticas adaptables (no eliminadas, reinterpretadas)

Reglas como flanqueo, ataques de oportunidad, cobertura, áreas o movimiento
no se eliminan necesariamente: se reinterpretan de forma narrativa cuando
aparecen en la ficción.

- **Flanqueo narrativo:** puede conceder ventaja si el enemigo está
  distraído, acorralado o presionado desde dos frentes, sin calcular
  casillas.
- **Ataque de oportunidad narrativo:** puede activarse si alguien abandona
  `cuerpo_a_cuerpo` de forma arriesgada sin cubrirse, sin contar casillas.
- **Cobertura narrativa:** puede dar ventaja/desventaja o modificar
  dificultad si la ficción lo justifica, sin geometría exacta.
- **Área de efecto narrativa:** puede afectar a un objetivo, varios cercanos
  o una zona, según la ficción, sin medir conos/radios.

Nada de esto está implementado como mecánica todavía (la iniciativa y los
turnos sí, desde F5.2; los ataques básicos contra CA, desde F5.3;
flanqueo/ataques de oportunidad/cobertura/áreas siguen pendientes — ver
[Pendiente (fases futuras)](#pendiente-fases-futuras)).

## Distancias relativas

En vez de coordenadas/casillas, cada enemigo tiene una `distancia` narrativa
opcional con cinco valores:

| Valor | Significado |
|---|---|
| `cuerpo_a_cuerpo` | Cuerpo a cuerpo, agarrado, encima, ya trabado. |
| `corta` | Se alcanza con un movimiento breve o acción inmediata. |
| `media` | Requiere acercarse, exponerse o usar proyectiles. |
| `larga` | Requiere maniobra, persecución, arma adecuada o escena de aproximación. |
| `fuera_de_alcance` | No participa inmediatamente o está fuera del foco actual. |

Es solo descriptiva; no hay reglas de movimiento ni alcance que se calculen a
partir de ella. (En F5.1 estos valores eran `cerca`/`media`/`lejos`; F5.1.1
los sustituye por los cinco anteriores para acercar el vocabulario al de D&D
sin introducir geometría.)

## Iniciativa clásica y turnos narrativos (F5.2)

La iniciativa **sí** es clásica de D&D (D-COMBATE-01): `1d20 + mod_destreza`,
tanto para el personaje como para cada enemigo. El DM Agent tira
automáticamente por los enemigos (D-COMBATE-02) — el jugador no necesita
introducir sus tiradas. No hay sorpresa todavía, ni dificultad global
heroica/gritty: la peligrosidad depende del encuentro o aventura concretos
(D-COMBATE-03).

Orden resultante:
- Mayor iniciativa primero (descendente).
- Empate entre personaje y enemigo: **gana el personaje**.
- Empate entre enemigos: orden estable por `nombre`, luego `id`.

Lo que sí cambia frente al tablero clásico: no hay grid ni casillas que
recorrer, así que "turno" no implica movimiento medido — es solo quién actúa
ahora en la narración. `ronda` cuenta ciclos completos del orden de
iniciativa; `indice_turno_actual` apunta a la entrada activa de
`orden_iniciativa`.

Las tiradas usan el motor de dados existente
(`dm_agent.herramientas.dados.tirar`, mismo que `dados.tirar`): en runtime son
aleatorias de verdad; con `semilla` (parámetro opcional de
`combate.tirar_iniciativa`) son reproducibles para tests/depuración.

## Ataques básicos contra CA (F5.3)

Un ataque se resuelve igual que en D&D: `1d20 + modificador_ataque` contra la
`ca` del objetivo.

- **Natural 1**: falla siempre (`pifia=true`), aunque el total alcanzara la CA.
- **Natural 20**: impacta siempre (`critico=true`), aunque el total no
  alcanzara la CA. El daño se duplica (dados, no modificador): `1d8+3` se
  convierte en `2d8+3`.
- Cualquier otro resultado: impacta si `total_ataque >= ca_objetivo`.

`combate.atacar_enemigo` resuelve un ataque del personaje (o, en teoría,
cualquier `atacante_id` narrativo) contra un enemigo del combate, aplicando
daño con la misma lógica de umbral que `combate.daño_enemigo`.
`combate.atacar_personaje` resuelve un ataque de un enemigo contra el
personaje jugador, usando `ficha.ca` como objetivo y aplicando el daño
directamente sobre `Ficha` vía `GestorEstado` — **deliberadamente sin llamar
a `hp_xp.aplicar_daño`**, para no registrar dos eventos de daño distintos
para la misma acción (ver [ADR-0018](../decisiones/0018-combate-dnd-narrativo.md)
para la decisión completa).

Ninguna de las dos tools avanza turno automáticamente: el avance sigue
siendo una llamada explícita a `combate.avanzar_turno`, decidida por el DM
(LLM), no un efecto secundario de atacar.

No hay todavía IA enemiga que decida cuándo o a quién atacar, ni selección
automática de acciones: quien decide que un enemigo ataca (y con qué
`modificador_ataque`/`dano`) es el DM (LLM) en cada llamada.

### Sobre la distancia y el alcance

La `distancia` de un enemigo (`cuerpo_a_cuerpo`/`corta`/`media`/`larga`/
`fuera_de_alcance`) **no bloquea** un ataque en F5.3: es solo información
narrativa para que el DM decida si el ataque tiene sentido en la ficción
(p. ej. una espada normalmente pide `cuerpo_a_cuerpo`; un arco puede
funcionar a `media`/`larga`). Validar el alcance de forma dura queda para
fases futuras, si llega a hacer falta.

## Ventaja/desventaja y modificadores situacionales (F5.4)

`combate.atacar_enemigo` y `combate.atacar_personaje` aceptan tres campos
opcionales nuevos:

| Campo | Default | Descripción |
|---|---|---|
| `modo_tirada` | `"normal"` | `normal` / `ventaja` / `desventaja`. |
| `modificador_situacional` | `0` | Entero -10..10, bonificador/penalizador narrativo. |
| `motivo_modificador` | `null` | Texto libre: por qué se aplica el modo/modificador. |

Sin pasar estos campos, el comportamiento es **idéntico a F5.3**.

Mecánica clásica de D&D:

```text
normal:      tirar 1d20
ventaja:     tirar 2d20, quedarse con el mayor
desventaja:  tirar 2d20, quedarse con el menor
```

`total_ataque = tirada_d20 (elegida) + modificador_ataque + modificador_situacional`.
Natural 1/20 se evalúa **sobre la tirada elegida** tras ventaja/desventaja:
una ventaja que saca `[1, 20]` es un crítico (se elige 20); una desventaja
que saca `[1, 20]` es una pifia (se elige 1).

**Cancelación conceptual**: si la ficción tiene ventaja y desventaja a la
vez, se cancelan y se tira normal — pero esa cancelación la decide quien
llama a la tool (el DM/LLM) eligiendo `modo_tirada="normal"`; la tool en sí
solo acepta **un modo final**, no acumula ni resuelve combinaciones de
múltiples ventajas/desventajas.

`motivo_modificador` debe ser **narrativo**: por qué existe la ventaja,
desventaja o modificador situacional en la ficción (p. ej. "la rata está
distraída por el fuego", "Tyr ataca desde terreno elevado"), no un cálculo
de reglas. El DM (LLM) puede **proponer** ventaja/desventaja a partir de la
escena, pero quien confirma si aplica de verdad es el jugador — coherente
con D-COMBATE-04 (propuesta, no automatismo).

No hay todavía **acumulación compleja** (varias fuentes de ventaja, varios
modificadores situacionales con prioridades distintas, etc.): solo un modo
final y un modificador situacional por ataque. Flanqueo, cobertura y
condiciones siguen **sin calcularse automáticamente** — si conceden
ventaja/desventaja, es el DM quien lo decide y lo pasa explícitamente en
`modo_tirada`/`modificador_situacional`.

## Esquemas

### `EnemigoCombate`

```text
id, nombre, hp_max (>0), hp_actual (0..hp_max), ca (>0),
estado (no vacío, default "activo"), descripcion, distancia (opcional),
tags[], mod_destreza (opcional, -10..10), iniciativa (opcional, entero),
version_schema (=1)
```

Estados sugeridos (texto libre, sin enum forzado): `activo`, `herido`,
`critico`, `caido`, `huido`, `derrotado`. `combate.daño_enemigo` los calcula
automáticamente a partir del HP; nada impide guardar otros valores a mano si
hiciera falta (p. ej. `huido`) mediante una futura tool de edición — no
existe en F5.1. `mod_destreza`/`iniciativa` son opcionales y `None` por
defecto: los enemigos creados antes de F5.2 no necesitan migrarse; al tirar
iniciativa, un enemigo sin `mod_destreza` usa `0`.

### `EntradaIniciativa` (F5.2)

```text
participante_id, nombre, tipo ("personaje" | "enemigo"), iniciativa (entero),
es_personaje (bool, default False)
```

Una entrada del `orden_iniciativa` de un combate. El personaje jugador
aparece aquí como un participante más de la iniciativa, aunque su HP sigue
viviendo en `Ficha`/`hp_xp.*`, no en `CombateNarrativo`.

### `CombateNarrativo`

```text
id, campaña_id, sesion_id (opcional), personaje_id,
estado (no vacío, default "activo"), turno (>=0, default 0),
descripcion_escena, enemigos[EnemigoCombate],
orden_iniciativa[EntradaIniciativa] (default []),
indice_turno_actual (>=0, default 0), ronda (>=1, default 1),
notas, version_schema (=1)
```

Estados sugeridos: `preparando`, `activo`, `terminado`, `cancelado`. En F5.1
`combate.iniciar` crea el combate **ya en estado `activo`** directamente (no
hay una tool separada para la fase `preparando`); `preparando`/`cancelado`
quedan como estados válidos del esquema para uso futuro o manual.

`orden_iniciativa` está vacío hasta que se llama a `combate.tirar_iniciativa`;
`combate.turno_actual`/`combate.avanzar_turno` fallan con error controlado si
todavía no se ha tirado. El campo `turno` (F5.1, contador simple) sigue
existiendo pero no se usa para nada en F5.2: `ronda` e `indice_turno_actual`
son los campos vivos del ciclo de iniciativa.

### `ResultadoAtaque` (F5.3, ampliado en F5.4, no persistido)

```text
atacante_id, objetivo_id, modo_tirada, tiradas_d20, tirada_d20,
modificador_ataque, modificador_situacional, total_ataque, ca_objetivo,
impacta, critico, pifia, dano, tipo_dano, motivo, motivo_modificador
```

`tiradas_d20` es la lista de tiradas brutas (1 elemento en modo `normal`, 2
en `ventaja`/`desventaja`); `tirada_d20` es la elegida tras aplicar
ventaja/desventaja. Vive solo en `dm_agent.herramientas.combate` (como
`dataclass`, igual que `ResultadoTirada` en `herramientas/dados.py`): no es
un campo de `CombateNarrativo`. El resultado de un ataque se vuelca al
evento auditable y a la respuesta de la tool; no hace falta guardar un
historial de ataques dentro del combate.

## Persistencia

```text
storage/
└── campañas/
    └── <campaña_id>/
        └── combates/
            ├── <combate_id>.json
            └── activo.json
```

Cada combate es un fichero JSON propio (escritura atómica, igual que
`GestorEstado`). **Decisión de diseño**: `activo.json` no guarda el combate
completo, solo una referencia `{"combate_id": "..."}`. Así cada mutación
escribe un único fichero (`<combate_id>.json`); `activo.json` nunca puede
quedar desincronizado con el contenido real. Solo puede haber una referencia
activa por campaña: escribirla reemplaza la anterior, lo que garantiza **un
único combate activo por campaña**.

## API

```python
GestorCombateNarrativo(raiz_storage)
  .guardar(combate) -> CombateNarrativo
  .cargar(campaña_id, combate_id) -> CombateNarrativo        # ErrorCombateNoEncontrado si no existe
  .listar(campaña_id) -> list[CombateNarrativo]
  .marcar_activo(combate) -> None
  .limpiar_activo(campaña_id) -> None
  .cargar_activo(campaña_id) -> CombateNarrativo | None
```

## Tools

Ver [`../tools/combate.md`](../tools/combate.md) para el detalle de
parámetros, eventos y ejemplos.

## Daño al personaje jugador

El daño/curación del personaje jugador fuera de un ataque resuelto **sigue
pasando por `hp_xp.*`** (F3.4). Dentro de un ataque resuelto
(`combate.atacar_personaje`), el daño se aplica directamente sobre `Ficha`
vía `GestorEstado`, sin pasar por `hp_xp.aplicar_daño` (ver
[Ataques básicos contra CA](#ataques-básicos-contra-ca-f53) y
[ADR-0018](../decisiones/0018-combate-dnd-narrativo.md)). No hay XP
automática al terminar un combate: usa `hp_xp.otorgar_xp` aparte,
manualmente.

## Memoria narrativa

En F5.1 los combates **no** se inyectan al contexto narrativo. Las
mutaciones registran eventos mecánicos auditables (`eventos.jsonl`); lo
narrativo (qué significó el combate para la historia) lo sigue capturando
quien llama a `narrativa.registrar` o el cierre de sesión/resumen, a mano.
F5.2 podrá integrar combate con memoria narrativa (p. ej. sugerir una entrada
de consecuencia al terminar).

## Implementado

- **F5.2 — Iniciativa clásica**: `combate.tirar_iniciativa` (1d20 +
  mod_destreza, enemigos automáticos).
- **F5.2 — Turnos narrativos**: `combate.turno_actual` (consulta) y
  `combate.avanzar_turno` (avanza el índice, incrementa `ronda` al cerrar el
  ciclo).
- **F5.3 — Ataques básicos contra CA**: `combate.atacar_enemigo` y
  `combate.atacar_personaje` (1d20 + modificador contra CA; natural 1/20;
  daño duplicado en crítico).
- **F5.4 — Ventaja/desventaja y modificadores situacionales**: `modo_tirada`
  (normal/ventaja/desventaja) y `modificador_situacional` en las mismas dos
  tools, con `motivo_modificador` narrativo.
- Eventos auditables `iniciativa_tirada`, `turno_avanzado`,
  `ataque_enemigo_resuelto`, `ataque_personaje_resuelto` (estos dos últimos
  incluyen `modo_tirada`/`tiradas_d20`/`modificador_situacional` desde F5.4).

## Pendiente (fases futuras)

Documentado pero **no implementado como mecánica todavía** (D-COMBATE-04 y
ADR-0018):

- **Reacciones y ataques de oportunidad propuestos**: el agente podrá
  proponer una reacción o un ataque de oportunidad narrativo cuando la
  ficción lo justifique, pero **el jugador debe confirmarlos antes de
  aplicarlos** — no se aplican automáticamente.
- **Flanqueo y cobertura mecánicos/automáticos**: hoy solo conceden
  ventaja/desventaja si el DM los detecta en la ficción y los pasa
  explícitamente vía `modo_tirada`; no hay cálculo automático a partir de
  posición o distancia.
- **Acumulación compleja de ventaja/desventaja**: varias fuentes
  simultáneas, prioridades entre modificadores situacionales, etc. — F5.4
  solo acepta un modo final y un modificador por ataque.
- **IA enemiga / selección automática de acciones**: el DM (LLM) sigue
  decidiendo manualmente cuándo y a quién ataca cada enemigo.
- **Validación dura de alcance por `distancia`**: la distancia sigue siendo
  solo informativa, no bloquea ataques.
- **Sorpresa**: no implementada.
- Integración con memoria narrativa al terminar combate (sugerir/registrar
  consecuencia).

## Limitaciones (F5.1 / F5.1.1 / F5.2 / F5.3 / F5.4)

- Sin grid, casillas, pies/pulgadas ni reglas de movimiento; `distancia` no
  bloquea ataques por alcance.
- Sin IA enemiga ni selección automática de acciones; sin economía de
  acciones completa.
- Sin reacciones ni ataques de oportunidad **mecánicos** (solo se proponen
  narrativamente y requieren confirmación del jugador en fases futuras).
- Sin flanqueo ni cobertura **automáticos**: conceden ventaja/desventaja
  solo si el DM los detecta y los indica explícitamente.
- Sin acumulación de múltiples ventajas/desventajas ni prioridades entre
  modificadores: un `modo_tirada` final y un `modificador_situacional` por
  ataque.
- Sin condiciones completas, áreas de efecto, salvaciones, sin sorpresa,
  resistencias, vulnerabilidades ni hechizos.
- Sin XP automática, balance automático ni bestiario completo.
- Sin RAG, memoria vectorial ni streaming.
- D17 (D&D 5.5 narrativo en solitario) guiará cualquier adaptación de reglas
  futura; este módulo no implementa reglas adaptadas automáticas más allá de
  la iniciativa, los turnos, los ataques básicos y la ventaja/desventaja,
  solo el estado mínimo para sostener el resto a mano.
