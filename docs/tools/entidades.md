# Tools `entidad.*` (F4.6)

> Módulo: `dm_agent.herramientas.entidades` · Fase: F4.6

## Propósito

Guardar y consultar **entidades narrativas estructuradas** por campaña: PNJ,
lugares, pistas, objetivos y frentes abiertos. Complementan la bitácora
(`narrativa.*`, F4.1): la bitácora dice **qué pasó**; estas tools dicen
**quién/qué existe y en qué estado está ahora**. Ver
[`../memoria/entidades.md`](../memoria/entidades.md). No registran eventos
mecánicos ni entradas narrativas.

## Tools

| Interno | API (LLM) | Modelo | Clave en `datos` |
|---|---|---|---|
| `entidad.guardar_pnj` | `entidad_guardar_pnj` | `PNJ` | `pnj` (objeto) |
| `entidad.listar_pnj` | `entidad_listar_pnj` | `PNJ` | `pnj` (lista) |
| `entidad.guardar_lugar` | `entidad_guardar_lugar` | `Lugar` | `lugar` (objeto) |
| `entidad.listar_lugares` | `entidad_listar_lugares` | `Lugar` | `lugares` (lista) |
| `entidad.guardar_pista` | `entidad_guardar_pista` | `Pista` | `pista` (objeto) |
| `entidad.listar_pistas` | `entidad_listar_pistas` | `Pista` | `pistas` (lista) |
| `entidad.guardar_objetivo` | `entidad_guardar_objetivo` | `Objetivo` | `objetivo` (objeto) |
| `entidad.listar_objetivos` | `entidad_listar_objetivos` | `Objetivo` | `objetivos` (lista) |
| `entidad.guardar_frente` | `entidad_guardar_frente` | `FrenteAbierto` | `frente` (objeto) |
| `entidad.listar_frentes` | `entidad_listar_frentes` | `FrenteAbierto` | `frentes` (lista) |

## `entidad_guardar_*`

Parámetros comunes (heredados de `EntidadBase`), todos en el nivel superior del
objeto de la tool:

```json
{
  "campaña_id": "campana_demo",
  "id": "pnj_mara",
  "nombre": "Mara",
  "descripcion": "Posadera de la Taberna del Ciervo Gris",
  "estado": "activa",
  "tags": ["taberna", "aliada"],
  "importancia": 4,
  "notas": "oculta algo sobre las ruinas"
}
```

Requeridos: `campaña_id`, `id`, `nombre`. El resto es opcional.

Campos extra por tipo:

- **PNJ**: `rol`, `actitud`, `ubicacion_id`, `relacion_con_personaje`.
- **Lugar**: `tipo`, `conectado_con` (array de strings).
- **Pista**: `origen`, `relacionada_con`, `resuelta` (boolean).
- **Objetivo**: `prioridad` (integer), `relacionado_con`.
- **FrenteAbierto**: `amenaza`, `reloj` (integer 0–6), `consecuencias`,
  `relacionado_con`.

Comportamiento: valida con el esquema pydantic correspondiente, **guarda por
`id`** (si ya existe una entidad con ese `id` en la campaña, la reemplaza) y
devuelve `{"ok": true, "datos": {"<clave>": {...entidad guardada...}}}`. Si la
validación falla (p. ej. `nombre` vacío, `importancia` fuera de [1,5], `reloj`
fuera de [0,6]), devuelve `{"ok": false, "errores": [...]}` sin tocar disco.

Ejemplo, `entidad_guardar_frente`:

```json
{"campaña_id": "campana_demo", "id": "frente_bruja", "nombre": "La bruja del medallón",
 "amenaza": "el medallón atrae a la bruja", "reloj": 2}
```

## `entidad_listar_*`

```json
{"campaña_id": "campana_demo"}
```

Único parámetro requerido: `campaña_id`. Devuelve
`{"ok": true, "datos": {"<clave_plural>": [...]}}` con las entidades de ese
tipo en la campaña, **ordenadas por `importancia` descendente y luego
`nombre`**. Si no hay ninguna (o el fichero no existe todavía), devuelve lista
vacía. No modifica nada.

## Errores

`campaña_id` vacío/faltante, `id`/`nombre` vacíos, `importancia` fuera de
[1,5], `reloj` fuera de [0,6], o cualquier campo no reconocido por el esquema
(`extra="forbid"`) → `ResultadoHerramienta(ok=False, errores=[...])`. Sin
tracebacks al LLM.

## Límites (F4.6)

- Sin extracción automática: nadie "detecta" entidades en la narración por su
  cuenta; hay que llamar a la tool explícitamente.
- Sin RAG, memoria vectorial ni recuperación por relevancia: ver
  [`../memoria/entidades.md`](../memoria/entidades.md).
- Sin relaciones validadas (los campos `relacionado_con` son texto libre, no
  referencias comprobadas contra otras entidades).
- Sin combate, reglas adaptadas ni streaming.
