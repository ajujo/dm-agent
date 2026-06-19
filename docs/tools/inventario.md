# Tools `inventario.*` (F3.6)

> Módulo: `dm_agent.herramientas.inventario` · Fase: F3.6

## Propósito

Gestionar un **inventario simple** sobre `Ficha.inventario` (lista de
`ObjetoInventario`). Toda mutación pasa por validación con `Ficha`, se guarda de
forma atómica con `GestorEstado` y registra un `Evento` auditable. Desde F3.6,
los cambios semánticos de inventario deben hacerse con estas tools, no con
`ficha.actualizar` (genérica/administrativa).

Coherente con [D17](../decisiones/0017-dnd55-narrativo-solitario.md): inventario
narrativo (llaves, pociones, pistas, armas…), sin simulador táctico.

## Tools

| Interno | API (LLM) | Persiste | Evento |
|---|---|---|---|
| `inventario.listar` | `inventario_listar` | no | — |
| `inventario.añadir` | `inventario_anadir` | sí | `objeto_añadido` |
| `inventario.quitar` | `inventario_quitar` | sí | `objeto_quitado` |
| `inventario.equipar` | `inventario_equipar` | sí | `objeto_equipado` |
| `inventario.desequipar` | `inventario_desequipar` | sí | `objeto_desequipado` |

> El nombre interno usa español (`añadir`); el nombre API translitera a ASCII
> (`ñ→n`) por compatibilidad OpenAI: `inventario_anadir`.

## `ObjetoInventario`

```text
id (no vacío) · nombre (no vacío) · cantidad (>= 1) · descripcion (opcional) · equipado (bool)
```

## Inputs / outputs

Todas devuelven, en éxito, el inventario completo actualizado:

```json
{"ok": true, "personaje_id": "pj_tyr", "inventario": [ {ObjetoInventario...} ]}
```

### `inventario_listar`
```json
{"campaña_id":"campana_demo","personaje_id":"pj_tyr"}
```
No modifica ni registra evento.

### `inventario_anadir`
```json
{"campaña_id":"…","personaje_id":"pj_tyr",
 "objeto":{"id":"obj_llave","nombre":"Llave oxidada","cantidad":1,
           "descripcion":"…","equipado":false}, "motivo":"…"}
```
Valida el objeto. Si ya existe uno con el mismo `id`: **suma cantidades** (conserva
nombre; actualiza `descripcion` solo si la nueva no está vacía; conserva `equipado`).

### `inventario_quitar`
```json
{"campaña_id":"…","personaje_id":"pj_tyr","objeto_id":"obj_llave","cantidad":1,"motivo":"…"}
```
`cantidad` entero > 0. Si < actual: resta. Si == actual: elimina el objeto. Si >
actual: **error controlado** (no modifica).

### `inventario_equipar` / `inventario_desequipar`
```json
{"campaña_id":"…","personaje_id":"pj_tyr","objeto_id":"obj_espada","motivo":"…"}
```
Marca `equipado=true`/`false`. Error controlado si el objeto no existe. Sin slots,
exclusividad, dos manos ni armaduras incompatibles.

## Eventos registrados

`objeto_añadido`, `objeto_quitado`, `objeto_equipado`, `objeto_desequipado` en
`storage/campañas/<campaña_id>/eventos.jsonl`. `datos` incluye `personaje_id`,
`objeto_id`, `nombre`, `motivo` (si se da), y `cantidad`/`cantidad_antes`/
`cantidad_despues` cuando aplica (añadir/quitar). `inventario.listar` **no**
registra evento.

## Errores

Entrada inválida, objeto inválido, ficha/campaña inexistente, objeto inexistente,
cantidad ≤ 0 o quitar más de lo disponible → `ResultadoHerramienta(ok=False,
errores=[...])`. Nunca se propaga un traceback al LLM.

## Límites (F3.6)

- **No hay peso/carga.**
- **No hay oro/economía.**
- **No hay slots ni equipo complejo** (equipar es solo un flag booleano; sin
  exclusividad, dos manos ni compatibilidad de armadura).
- No hay rareza, attunement ni propiedades de armas/armaduras.
- Sin combate, reglas adaptadas, hechizos, RAG ni memoria avanzada.

Esto es la base para **exploración, recompensas/loot y combate** futuros. D17
permitirá adaptar carga, economía y loot a un estilo narrativo más adelante.
