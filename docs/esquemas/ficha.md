# Esquema: `Ficha`

> Módulo: `dm_agent.esquemas.ficha` · Fase: F3.1 · `version_schema = 1`

## Propósito

Representar el estado mecánico mínimo de un personaje jugador: identidad,
nivel/clase/raza, atributos, puntos de golpe, CA, competencia, XP, condiciones e
inventario simple. Es el modelo de datos sobre el que operarán las tools de
ficha y HP/XP en fases posteriores (F3.3+).

## Modelos

### `Atributos`
Las seis características. Cada una **entre 1 y 30**.

| Campo | Tipo | Validación |
|---|---|---|
| `fuerza` | int | 1–30 |
| `destreza` | int | 1–30 |
| `constitucion` | int | 1–30 |
| `inteligencia` | int | 1–30 |
| `sabiduria` | int | 1–30 |
| `carisma` | int | 1–30 |

### `ObjetoInventario`
Entrada de inventario simple.

| Campo | Tipo | Validación |
|---|---|---|
| `id` | str | no vacío |
| `nombre` | str | no vacío |
| `cantidad` | int | ≥ 1 |
| `descripcion` | str \| None | opcional |
| `equipado` | bool | por defecto `false` |

### `Ficha`

| Campo | Tipo | Validación |
|---|---|---|
| `id` | str | no vacío |
| `nombre` | str | no vacío |
| `clase` | str | no vacío |
| `nivel` | int | 1–20 |
| `raza` | str | no vacío |
| `trasfondo` | str | por defecto `""` |
| `atributos` | `Atributos` | — |
| `hp_max` | int | > 0 |
| `hp_actual` | int | 0 ≤ hp_actual ≤ hp_max |
| `ca` | int | > 0 |
| `bonificador_competencia` | int | ≥ 2 (explícito, **no** se calcula) |
| `xp` | int | ≥ 0 (por defecto 0) |
| `condiciones` | list[str] | por defecto `[]` |
| `inventario` | list[`ObjetoInventario`] | por defecto `[]` |
| `notas` | str | por defecto `""` |
| `version_schema` | int | `1` |

Se prohíben campos extra (`extra="forbid"`).

## Ejemplo JSON

```json
{
  "id": "pj-1",
  "nombre": "Aelar",
  "clase": "Pícaro",
  "nivel": 3,
  "raza": "Elfo",
  "trasfondo": "Criminal",
  "atributos": {"fuerza": 10, "destreza": 16, "constitucion": 12,
                "inteligencia": 8, "sabiduria": 13, "carisma": 11},
  "hp_max": 24,
  "hp_actual": 24,
  "ca": 15,
  "bonificador_competencia": 2,
  "xp": 900,
  "condiciones": [],
  "inventario": [{"id": "obj-1", "nombre": "Daga", "cantidad": 2,
                  "descripcion": null, "equipado": true}],
  "notas": "",
  "version_schema": 1
}
```

## Qué NO cubre todavía

- No calcula nada automáticamente (ni el bonificador de competencia ni
  modificadores de atributo).
- No hay conjuros, rasgos, dotes, multiclase ni progresión.
- El inventario es plano: sin peso, valor, slots ni equipo estructurado.
- No hay tools que lean/modifiquen la ficha (F3.3) ni gestor de estado (F3.2).
