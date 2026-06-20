# Combate narrativo mínimo (F5.1, distancias revisadas en F5.1.1, iniciativa y turnos en F5.2)

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
turnos sí, desde F5.2; flanqueo/ataques de oportunidad/cobertura/áreas
siguen pendientes — ver [Pendiente (fases futuras)](#pendiente-fases-futuras)).

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

El daño/curación del personaje jugador **sigue pasando por `hp_xp.*`**
(F3.4): `combate.*` solo gestiona el HP de los enemigos simples dentro de la
escena. No hay XP automática al terminar un combate: usa
`hp_xp.otorgar_xp` aparte, manualmente.

## Memoria narrativa

En F5.1 los combates **no** se inyectan al contexto narrativo. Las
mutaciones registran eventos mecánicos auditables (`eventos.jsonl`); lo
narrativo (qué significó el combate para la historia) lo sigue capturando
quien llama a `narrativa.registrar` o el cierre de sesión/resumen, a mano.
F5.2 podrá integrar combate con memoria narrativa (p. ej. sugerir una entrada
de consecuencia al terminar).

## Implementado en F5.2

- **Iniciativa clásica**: `combate.tirar_iniciativa` (1d20 + mod_destreza,
  enemigos automáticos).
- **Turnos narrativos**: `combate.turno_actual` (consulta) y
  `combate.avanzar_turno` (avanza el índice, incrementa `ronda` al cerrar el
  ciclo).
- Eventos auditables `iniciativa_tirada` y `turno_avanzado`.

## Pendiente (fases futuras)

Documentado pero **no implementado como mecánica todavía** (D-COMBATE-04 y
ADR-0018):

- **Reacciones y ataques de oportunidad propuestos**: el agente podrá
  proponer una reacción o un ataque de oportunidad narrativo cuando la
  ficción lo justifique, pero **el jugador debe confirmarlos antes de
  aplicarlos** — no se aplican automáticamente.
- **Flanqueo narrativo**: ver ejemplo en
  [ADR-0018](../decisiones/0018-combate-dnd-narrativo.md).
- **Ventaja/desventaja narrativa**: aplicada cuando la ficción lo justifique,
  sin tabla de modificadores tácticos.
- **Sorpresa**: no implementada en F5.2.
- Integración con memoria narrativa al terminar combate (sugerir/registrar
  consecuencia).

## Limitaciones (F5.1 / F5.1.1 / F5.2)

- Sin grid, casillas, pies/pulgadas ni reglas de movimiento.
- Sin ataques completos (sin tirada de ataque/daño con CA todavía), sin IA
  táctica enemiga, sin economía de acciones completa.
- Sin reacciones ni ataques de oportunidad **mecánicos** (solo se proponen
  narrativamente y requieren confirmación del jugador en fases futuras).
- Sin flanqueo ni cobertura mecánicos, sin áreas de efecto.
- Sin sorpresa, salvaciones de muerte, resistencias, vulnerabilidades ni
  hechizos.
- Sin XP automática, balance automático ni bestiario completo.
- Sin RAG, memoria vectorial ni streaming.
- D17 (D&D 5.5 narrativo en solitario) guiará cualquier adaptación de reglas
  futura; este módulo no implementa reglas adaptadas automáticas más allá de
  la iniciativa y los turnos, solo el estado mínimo para sostenerlas a mano.
