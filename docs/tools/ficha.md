# Tools `ficha.*` (F3.3)

> Módulo: `dm_agent.herramientas.ficha` · Fase: F3.3

## Propósito

Permitir al agente **leer, validar, crear/guardar, actualizar y listar** fichas
de personaje sin que el LLM toque los datos directamente. Toda modificación pasa
por validación con el esquema `Ficha` (pydantic) y se persiste con
`GestorEstado`. Coherente con [D17](../decisiones/0017-dnd55-narrativo-solitario.md):
esto es persistencia de ficha para juego **narrativo en solitario**, **no** un
motor de HP/XP, combate ni reglas.

## Tools disponibles

| Interno | API (LLM) | Persiste | Resumen |
|---|---|---|---|
| `ficha.leer` | `ficha_leer` | no | Lee una ficha existente. |
| `ficha.guardar` | `ficha_guardar` | sí | Valida y guarda una ficha completa (crea o sobrescribe). |
| `ficha.validar` | `ficha_validar` | no | Valida una ficha contra el esquema. |
| `ficha.actualizar` | `ficha_actualizar` | sí | Cambios de primer nivel + validación + guardado. |
| `ficha.listar` | `ficha_listar` | no | Lista ids de personaje con ficha. |

Los schemas enviados al LLM usan los **nombres API** (`ficha_leer`, …); el
despacho interno (`dispatch_api`) los resuelve a `ficha.*`.

## Inputs / outputs

### `ficha_leer`
```json
// in
{"campaña_id": "campana_demo", "personaje_id": "pj_tyr"}
// out ok
{"ok": true, "ficha": { "...": "..." }}
```
Errores controlados: campaña no existe · ficha no existe · ficha inválida.

### `ficha_guardar`
```json
// in
{"campaña_id": "campana_demo", "ficha": { "...": "..." }}
// out ok
{"ok": true, "personaje_id": "pj_tyr", "ruta_relativa": "campañas/campana_demo/fichas/pj_tyr.json"}
```
Valida con `Ficha`; si no valida, `ok:false` + `errores`. No se exponen rutas
absolutas.

### `ficha_validar`
```json
// in
{"ficha": { "...": "..." }}
// out ok / ko
{"ok": true, "ficha": { "...": "..." }}
{"ok": false, "errores": ["hp_actual: ..."]}
```
No persiste nada.

### `ficha_actualizar`
```json
// in
{"campaña_id": "campana_demo", "personaje_id": "pj_tyr",
 "cambios": {"notas": "Encontró una llave oxidada"}}
// out ok
{"ok": true, "ficha": { "...": "..." }}
```
Solo **cambios de primer nivel**. Campos permitidos: `nombre`, `clase`, `nivel`,
`raza`, `trasfondo`, `atributos` (reemplazo **entero**), `hp_max`, `hp_actual`,
`ca`, `bonificador_competencia`, `xp`, `condiciones`, `inventario`, `notas`.
**No** se permite cambiar `id` ni `version_schema`; un campo desconocido o no
permitido devuelve error. El resultado se revalida con `Ficha` antes de guardar;
si no valida (p. ej. `hp_actual > hp_max`), no se persiste nada.

No hay edición profunda tipo JSON Patch ni cambios parciales de `atributos`
(p. ej. `atributos.fuerza`) en F3.3.

### `ficha_listar`
```json
// in
{"campaña_id": "campana_demo"}
// out ok
{"ok": true, "personajes": ["pj_kaelen", "pj_tyr"]}
```
Error controlado: campaña no existe.

## Errores

Las tools devuelven el contrato estándar `ResultadoHerramienta`
(`ok`, `datos`, `errores`). Los errores de `GestorEstado`
(`ErrorEstadoNoEncontrado`, `ErrorEstadoInvalido`) y de validación pydantic se
convierten a `ok:false` + `errores` legibles; **nunca** se propaga un traceback
al LLM.

## `ficha.actualizar` vs `hp_xp.*`

`ficha.actualizar` es una herramienta **genérica/administrativa** (crear/corregir
datos de ficha). Desde F3.4, los cambios **mecánicos** de juego —daño, curación,
XP— deben hacerse con las tools [`hp_xp.*`](./hp_xp.md), que además registran un
evento auditable. Aunque `ficha.actualizar` técnicamente aún permite tocar
`hp_actual`/`hp_max`/`xp`, no es la vía correcta cuando el agente dirige la
partida.

## Limitaciones (F3.3)

- No hay HP/XP **semántico** (daño, curación, otorgar XP, subida de nivel): eso
  es F3.4. `ficha_actualizar` solo escribe valores ya validados por el esquema.
- No hay combate, inventario complejo, reglas adaptadas, motor de hechizos, RAG
  ni memoria avanzada.
- El raíz de `storage` se toma de `config/proyecto.json → rutas.storage`.
