# Tools `hp_xp.*` (F3.4)

> Módulo: `dm_agent.herramientas.hp_xp` · Fase: F3.4

## Propósito

Modificar de forma determinista y **auditable** los puntos de golpe y la
experiencia de un personaje. Desde F3.4, cualquier cambio semántico de daño,
curación o XP debe pasar por estas tools (no por `ficha.actualizar`, que es
genérica/administrativa). Cada cambio exitoso carga la ficha con `GestorEstado`,
modifica solo el campo permitido, **revalida con `Ficha`**, guarda de forma
atómica y **registra un evento** en `eventos.jsonl` (ver
[`../estado/eventos.md`](../estado/eventos.md)).

Coherente con [D17](../decisiones/0017-dnd55-narrativo-solitario.md): lógica
simple, compatible con teatro de la mente.

## Tools

| Interno | API (LLM) | Persiste | Evento |
|---|---|---|---|
| `hp_xp.aplicar_daño` | `hp_xp_aplicar_dano` | sí | `daño_aplicado` |
| `hp_xp.aplicar_curacion` | `hp_xp_aplicar_curacion` | sí | `curacion_aplicada` |
| `hp_xp.otorgar_xp` | `hp_xp_otorgar_xp` | sí | `xp_otorgada` |
| `hp_xp.consultar_estado_vital` | `hp_xp_consultar_estado_vital` | no | — |

> El nombre interno usa español (`daño`); el nombre API translitera diacríticos a
> ASCII (`ñ→n`) por compatibilidad OpenAI: `hp_xp_aplicar_dano`.

## Inputs / outputs

### `hp_xp_aplicar_daño`
```json
// in
{"campaña_id":"campana_demo","personaje_id":"pj_tyr","cantidad":7,
 "tipo_daño":"cortante","motivo":"ataque de goblin"}
// out
{"ok":true,"personaje_id":"pj_tyr","hp_antes":18,"hp_despues":11,
 "hp_max":20,"estado_vital":"herido"}
```
`cantidad` entero > 0. `hp_actual` baja hasta un mínimo de 0. No aplica
resistencia/vulnerabilidad/inmunidad ni salvaciones.

### `hp_xp_aplicar_curacion`
```json
// in
{"campaña_id":"campana_demo","personaje_id":"pj_tyr","cantidad":5,"motivo":"poción menor"}
// out
{"ok":true,"personaje_id":"pj_tyr","hp_antes":6,"hp_despues":11,
 "hp_max":20,"estado_vital":"herido"}
```
`cantidad` entero > 0. `hp_actual` sube hasta un máximo de `hp_max`. Sin curación
con dados, estabilización ni condiciones.

### `hp_xp_otorgar_xp`
```json
// in
{"campaña_id":"campana_demo","personaje_id":"pj_tyr","cantidad":50,"motivo":"encuentro social"}
// out
{"ok":true,"personaje_id":"pj_tyr","xp_antes":100,"xp_despues":150,"subida_nivel_pendiente":null}
```
`cantidad` entero > 0. Suma a `ficha.xp`. **No** calcula subida de nivel
(`subida_nivel_pendiente` es informativo y siempre `null` por ahora).

### `hp_xp_consultar_estado_vital`
```json
// in
{"campaña_id":"campana_demo","personaje_id":"pj_tyr"}
// out
{"ok":true,"personaje_id":"pj_tyr","hp_actual":11,"hp_max":20,
 "porcentaje_hp":55.0,"estado_vital":"herido"}
```
No modifica ni registra evento.

## `estado_vital`

```text
caido    -> hp_actual == 0
critico  -> 0 < hp_actual <= 25% de hp_max
herido   -> 25% < hp_actual < hp_max
sano     -> hp_actual == hp_max
```

No existen `muerto`, `inconsciente` ni salvaciones contra muerte: D&D 5.5
narrativo en solitario los adaptará más adelante (D17).

## Errores

Entrada inválida, cantidad ≤ 0, campaña/ficha inexistente, JSON/esquema inválido
→ `ResultadoHerramienta(ok=False, errores=[...])`. Nunca se propaga un traceback
al LLM.

## Límites (F3.4)

- **No hay combate**, iniciativa ni ataques (esto es la base de mecánica para
  F5 — combate).
- **No hay muerte ni salvaciones** contra muerte.
- **No hay subida de nivel automática**.
- No hay inventario complejo, reglas adaptadas, hechizos, RAG ni memoria avanzada.
