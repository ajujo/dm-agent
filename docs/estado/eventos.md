# Eventos auditables del estado (F3.4)

> Módulo: `dm_agent.estado.eventos` · Fase: F3.4

## Propósito

Registro **append-only** de eventos por campaña, para auditar cada cambio
mecánico. En F3.4 lo usan las tools `hp_xp.*` para dejar constancia de daño,
curación y XP.

## Estructura

```text
storage/
└── campañas/
    └── <campaña_id>/
        └── eventos.jsonl
```

Cada línea es un `dm_agent.esquemas.evento.Evento` (pydantic) serializado con
`model_dump_json()`. JSONL = una línea por evento, nunca se reescribe lo anterior.

## API

```python
RegistroEventosEstado(raiz_storage)
  .ruta_eventos(campaña_id) -> Path
  .registrar(campaña_id, evento) -> Path   # append
  .listar(campaña_id) -> list[Evento]      # [] si no existe
```

## Eventos que emite F3.4

| Tool | `tipo` | `datos` |
|---|---|---|
| `hp_xp.aplicar_daño` | `daño_aplicado` | `cantidad, hp_antes, hp_despues, tipo_daño, motivo` |
| `hp_xp.aplicar_curacion` | `curacion_aplicada` | `cantidad, hp_antes, hp_despues, motivo` |
| `hp_xp.otorgar_xp` | `xp_otorgada` | `cantidad, xp_antes, xp_despues, motivo` |

Cada evento lleva además `actor="dm"`, `objetivo=<personaje_id>`,
`tool=<nombre interno>`, `timestamp` UTC y `version_schema`. Las **lecturas**
(`hp_xp.consultar_estado_vital`) **no** registran evento.

Ejemplo:

```json
{"id":"…","timestamp":"2026-06-19T…+00:00","tipo":"daño_aplicado","actor":"dm",
 "objetivo":"pj_tyr","tool":"hp_xp.aplicar_daño","motivo":"ataque de goblin",
 "datos":{"cantidad":7,"hp_antes":18,"hp_despues":11,"tipo_daño":"cortante",
          "motivo":"ataque de goblin"},"version_schema":1}
```

## Nota sobre los dos `Evento` (pendiente F3.5)

Coexisten dos representaciones:

- `dm_agent.nucleo.eventos.Evento` — dataclass ligero de **runtime** (lo usan las
  tools como la de dados para emitir eventos en memoria).
- `dm_agent.esquemas.evento.Evento` — modelo pydantic **persistible/auditable**
  (el que se escribe en `eventos.jsonl`).

F3.4 usa el persistible para el log. **La unificación runtime/persistible queda
para F3.5.**

## Limitaciones

- No hay bus de eventos central todavía (cada tool registra directamente).
- No hay índices ni consultas más allá de `listar`.
- No hay rotación/compactación del JSONL.
