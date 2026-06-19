# Eventos auditables del estado (F3.4 · unificado en F3.5)

> Módulos: `dm_agent.esquemas.evento` (modelo canónico) ·
> `dm_agent.estado.eventos` (registro JSONL) · `dm_agent.nucleo.eventos` (bus runtime).

## Modelo canónico (F3.5)

Existe **un único** modelo de evento: `dm_agent.esquemas.evento.Evento` (pydantic).
`dm_agent.nucleo.eventos` lo **re-exporta** (no hay ya un dataclass paralelo) y su
bus runtime publica ese mismo modelo:

```python
from dm_agent.nucleo.eventos import Evento, crear_evento  # Evento == esquemas.evento.Evento
```

Usa `crear_evento(tipo, ...)` para construir eventos (genera `id` uuid4 y
`timestamp` UTC). Campos: `id, timestamp, tipo, actor, objetivo, tool, datos,
motivo, version_schema`.

## Evento mecánico vs registro de sesión

Son cosas distintas y no deben confundirse:

- **Evento mecánico/auditable** (`Evento` canónico → `eventos.jsonl`): cambios de
  estado del juego (daño, curación, XP, …) para auditoría por campaña.
- **Registro de sesión** (`dm_agent.persistencia.sesion.Sesion` →
  `storage/sesiones/*.jsonl`): historial conversacional del REPL (turnos
  `user`/`assistant`/`tool_call`/`tool_result`). Es la transcripción, no el log
  mecánico.

## Propósito

Registro **append-only** de eventos por campaña, para auditar cada cambio
mecánico. Lo usan las tools `hp_xp.*` para dejar constancia de daño, curación y XP.

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

## Qué tools registran eventos hoy

| Tool | ¿registra? | `tipo` | `datos` |
|---|---|---|---|
| `hp_xp.aplicar_daño` | sí | `daño_aplicado` | `cantidad, hp_antes, hp_despues, tipo_daño, motivo` |
| `hp_xp.aplicar_curacion` | sí | `curacion_aplicada` | `cantidad, hp_antes, hp_despues, motivo` |
| `hp_xp.otorgar_xp` | sí | `xp_otorgada` | `cantidad, xp_antes, xp_despues, motivo` |
| `hp_xp.consultar_estado_vital` | **no** | — | (lectura) |
| `ficha.*` | **no** (todavía) | — | administrativas/CRUD |
| `dados.tirar` | emite `Evento` en memoria (`dados_tirados`) pero **no** lo persiste en `eventos.jsonl` |

Cada evento persistido lleva además `actor="dm"`, `objetivo=<personaje_id>`,
`tool=<nombre interno>`, `timestamp` UTC y `version_schema`.

## Cómo se añadirán eventos en el futuro

Las próximas mecánicas (inventario, combate, reglas adaptadas…) registrarán sus
eventos por la **misma vía canónica**: construir un `Evento` con `crear_evento(...)`
y persistirlo con `RegistroEventosEstado.registrar(campaña_id, evento)`. No deben
crear modelos de evento alternativos. Cuando crezca el número de emisores, el bus
runtime (`nucleo.eventos.bus`) puede centralizar la publicación/subscripción
(p. ej. un subscriber que persista), pero el **modelo** seguirá siendo el canónico.

Ejemplo:

```json
{"id":"…","timestamp":"2026-06-19T…+00:00","tipo":"daño_aplicado","actor":"dm",
 "objetivo":"pj_tyr","tool":"hp_xp.aplicar_daño","motivo":"ataque de goblin",
 "datos":{"cantidad":7,"hp_antes":18,"hp_despues":11,"tipo_daño":"cortante",
          "motivo":"ataque de goblin"},"version_schema":1}
```

## Unificación de `Evento` (F3.5 — hecho)

Antes coexistían dos modelos: un dataclass de runtime en `nucleo.eventos` y el
pydantic persistible en `esquemas.evento`. **F3.5 los unifica**: el modelo
canónico es `esquemas.evento.Evento`; `nucleo.eventos` lo re-exporta y el bus lo
publica; la tool de dados pasó a `crear_evento(...)` (su antiguo campo
`semilla_dados` vive ahora en `datos["semilla"]`). No quedan dos conceptos de
`Evento` evolucionando por separado.

## Limitaciones

- El bus runtime existe pero todavía **no** se usa como vía única de persistencia
  (las tools `hp_xp.*` llaman directamente a `RegistroEventosEstado`).
- No hay índices ni consultas más allá de `listar`.
- No hay rotación/compactación del JSONL.
