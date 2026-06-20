# Combate narrativo mínimo (F5.1, distancias revisadas en F5.1.1)

> Módulos: `dm_agent.esquemas.combate` (`EnemigoCombate`, `CombateNarrativo`) ·
> `dm_agent.estado.combate` (`GestorCombateNarrativo`) ·
> `dm_agent.herramientas.combate` (tools `combate.*`).

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

Nada de esto está implementado como mecánica en F5.1.1: solo se deja la
arquitectura y la documentación preparadas (ver
[Pendiente (F5.2)](#pendiente-f52)).

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

## Esquemas

### `EnemigoCombate`

```text
id, nombre, hp_max (>0), hp_actual (0..hp_max), ca (>0),
estado (no vacío, default "activo"), descripcion, distancia (opcional),
tags[], version_schema (=1)
```

Estados sugeridos (texto libre, sin enum forzado): `activo`, `herido`,
`critico`, `caido`, `huido`, `derrotado`. `combate.daño_enemigo` los calcula
automáticamente a partir del HP; nada impide guardar otros valores a mano si
hiciera falta (p. ej. `huido`) mediante una futura tool de edición — no
existe en F5.1.

### `CombateNarrativo`

```text
id, campaña_id, sesion_id (opcional), personaje_id,
estado (no vacío, default "activo"), turno (>=0, default 0),
descripcion_escena, enemigos[EnemigoCombate], notas, version_schema (=1)
```

Estados sugeridos: `preparando`, `activo`, `terminado`, `cancelado`. En F5.1
`combate.iniciar` crea el combate **ya en estado `activo`** directamente (no
hay una tool separada para la fase `preparando`); `preparando`/`cancelado`
quedan como estados válidos del esquema para uso futuro o manual.

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

## Pendiente (F5.2)

F5.1.1 solo deja arquitectura y documentación preparadas; nada de esto está
implementado todavía:

- **Iniciativa narrativa**: un orden de actuación ligero, sin tirada de
  iniciativa mecánica exhaustiva ni tablero de turnos.
- **Turnos**: usar `CombateNarrativo.turno` como algo más que un contador
  simple (hoy no hay orden de turnos calculado).
- **Reacciones narrativas**: respuestas fuera de turno justificadas por la
  ficción, no por una economía de acciones formal.
- **Ataques de oportunidad narrativos**: ver ejemplo más arriba.
- **Flanqueo narrativo**: ver ejemplo más arriba.
- **Ventaja/desventaja narrativa**: aplicada cuando la ficción lo justifique,
  sin tabla de modificadores tácticos.

## Limitaciones (F5.1 / F5.1.1)

- Sin grid, casillas, pies/pulgadas ni reglas de movimiento.
- Sin iniciativa compleja: `turno` es un contador simple, no hay orden de
  turnos calculado.
- Sin economía de acciones, reacciones, ataques de oportunidad, cobertura,
  flanqueo ni áreas de efecto.
- Sin salvaciones de muerte, resistencias, vulnerabilidades ni hechizos.
- Sin XP automática, balance automático, IA táctica enemiga ni bestiario.
- Sin RAG, memoria vectorial ni streaming.
- D17 (D&D 5.5 narrativo en solitario) guiará cualquier adaptación de reglas
  futura; este módulo no implementa reglas adaptadas automáticas, solo el
  estado mínimo para sostenerlas a mano.
