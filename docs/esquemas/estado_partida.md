# Esquema: `EstadoPartida`

> Módulo: `dm_agent.esquemas.estado` · Fase: F3.1 · `version_schema = 1`

## Propósito

Capturar "dónde está" la partida en un momento dado: qué campaña y personaje
están activos, en qué fase de juego y escena, y en qué turno. Es el ancla mínima
del estado mecánico; el gestor que lo persiste y versiona llega en F3.2.

## Campos

| Campo | Tipo | Validación |
|---|---|---|
| `id` | str | no vacío |
| `campaña_id` | str | no vacío |
| `personaje_activo_id` | str \| None | opcional; si existe, no vacío |
| `fase_actual` | `FaseActual` | enum (ver abajo); por defecto `exploracion` |
| `escena_actual` | str | por defecto `""` |
| `turno` | int | ≥ 0 (por defecto 0) |
| `sesion_id` | str \| None | opcional |
| `version_schema` | int | `1` |

Se prohíben campos extra (`extra="forbid"`).

### `FaseActual` (enum)

`exploracion` · `social` · `combate` · `descanso` · `viaje` · `gestion`

## Ejemplo JSON

```json
{
  "id": "estado-1",
  "campaña_id": "camp-1",
  "personaje_activo_id": "pj-1",
  "fase_actual": "exploracion",
  "escena_actual": "Taberna del Dragón Verde",
  "turno": 0,
  "sesion_id": "sesion-20260619-101200",
  "version_schema": 1
}
```

## Qué NO cubre todavía

- No modela el mundo (localizaciones, PNJ, facciones, tiempo del mundo).
- No modela el combate (iniciativa, participantes, rondas): solo marca la fase.
- No gestiona persistencia ni transiciones de fase (eso es lógica de F3.2+).
