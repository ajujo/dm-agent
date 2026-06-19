# Esquema: `Evento`

> Módulo: `dm_agent.esquemas.evento` · Fase: F3.1 · `version_schema = 1`

## Propósito

Registro inmutable y serializable de "algo que pasó", pensado para **auditoría**:
cada cambio mecánico futuro (HP, XP, inventario, condiciones…) emitirá un evento.
En F3.1 solo se define el esquema y un helper de construcción; el log JSONL
auditable por cada cambio de estado es F3.5.

## Relación con `nucleo.eventos.Evento`

Existe otro `Evento` en `dm_agent.nucleo.eventos`: un dataclass ligero que las
herramientas ya usan en tiempo de ejecución (p. ej. la tool de dados). Este
`Evento` (pydantic) es el modelo **persistible/auditable**. Se mantienen
separados a propósito hasta unificarlos en F3.5.

## Campos

| Campo | Tipo | Validación |
|---|---|---|
| `id` | str | no vacío |
| `timestamp` | str | ISO-8601 UTC; por defecto `datetime.now(UTC).isoformat()` |
| `tipo` | str | no vacío |
| `actor` | str \| None | opcional |
| `objetivo` | str \| None | opcional |
| `tool` | str \| None | opcional |
| `datos` | dict | por defecto `{}` |
| `motivo` | str \| None | opcional |
| `version_schema` | int | `1` |

Se prohíben campos extra (`extra="forbid"`).

## Helper

```python
from dm_agent.esquemas import crear_evento

ev = crear_evento("hp_aplicado", actor="motor", objetivo="pj-1", datos={"delta": -5})
# genera `id` (uuid4 hex) y `timestamp` automáticamente
```

## Ejemplo JSON

```json
{
  "id": "9f1c2e7b8a4d4f0e9c3b1a2d3e4f5a6b",
  "timestamp": "2026-06-19T10:12:00.123456+00:00",
  "tipo": "hp_aplicado",
  "actor": "motor",
  "objetivo": "pj-1",
  "tool": "hp_xp_aplicar_dano",
  "datos": {"delta": -5, "hp_resultante": 19},
  "motivo": "ataque de goblin",
  "version_schema": 1
}
```

## Qué NO cubre todavía

- No se emite ni se persiste automáticamente: no hay aún log auditable (F3.5).
- No está unificado con el `Evento` dataclass del núcleo.
- No define un catálogo cerrado de `tipo` (es texto libre por ahora).
