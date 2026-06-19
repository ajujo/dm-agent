# Tools `combate.*` (F5.1)

> Módulo: `dm_agent.herramientas.combate` · Fase: F5.1

## Propósito

Sostener escenas de combate **narrativo mínimo** (teatro de la mente, D17):
crear la escena, añadir enemigos simples, consultar el estado, aplicar daño a
enemigos y terminarla, todo con eventos auditables. Ver
[`../estado/combate.md`](../estado/combate.md) para el detalle de esquemas y
persistencia. El daño al **personaje jugador** sigue pasando por
[`hp_xp.md`](hp_xp.md) (`hp_xp.aplicar_daño`); estas tools no lo tocan.

## Tools

| Interno | API (LLM) | Modifica | Registra evento |
|---|---|---|---|
| `combate.iniciar` | `combate_iniciar` | sí | `combate_iniciado` |
| `combate.estado` | `combate_estado` | no | no |
| `combate.añadir_enemigo` | `combate_anadir_enemigo` | sí | `enemigo_añadido` |
| `combate.daño_enemigo` | `combate_dano_enemigo` | sí | `daño_enemigo` |
| `combate.terminar` | `combate_terminar` | sí | `combate_terminado` |

## `combate_iniciar`

```json
{
  "campaña_id": "campana_demo",
  "sesion_id": "sesion_001",
  "personaje_id": "pj_tyr",
  "descripcion_escena": "Tyr baja al sótano y dos ratas gigantes emergen entre barriles rotos.",
  "enemigos": [
    {
      "id": "rata_1",
      "nombre": "Rata gigante",
      "hp_max": 7,
      "hp_actual": 7,
      "ca": 12,
      "estado": "activo",
      "descripcion": "Una rata enorme con ojos febriles.",
      "distancia": "cerca",
      "tags": ["bestia", "sotano"]
    }
  ]
}
```

Requeridos: `campaña_id`, `personaje_id`. `enemigos` es opcional (puedes
empezar sin enemigos y añadirlos con `combate_anadir_enemigo`). Genera un
`id` de combate automático (`combate_<8 hex>`), lo guarda y lo marca como
**combate activo** de la campaña. Si ya hay un combate activo cuyo `estado`
no es `terminado`/`cancelado`, devuelve error sin crear nada.

## `combate_estado`

```json
{"campaña_id": "campana_demo", "combate_id": "combate_001"}
```

Único requerido: `campaña_id`. Si se omite `combate_id` (o es `null`), carga
el **combate activo** de la campaña. No modifica nada ni registra evento. Si
no hay combate activo (y no se dio `combate_id`), o el `combate_id` dado no
existe, devuelve error.

## `combate_anadir_enemigo`

```json
{
  "campaña_id": "campana_demo",
  "combate_id": "combate_001",
  "enemigo": {
    "id": "rata_2",
    "nombre": "Rata gigante",
    "hp_max": 7,
    "hp_actual": 7,
    "ca": 12,
    "estado": "activo",
    "descripcion": "Otra rata emerge desde una grieta.",
    "distancia": "media",
    "tags": ["bestia", "sotano"]
  }
}
```

Requeridos: `campaña_id`, `combate_id`, `enemigo` (con al menos `id`,
`nombre`, `hp_max`, `hp_actual`, `ca`). Rechaza si ya existe un enemigo con
ese `id` en el combate.

## `combate_dano_enemigo`

```json
{
  "campaña_id": "campana_demo",
  "combate_id": "combate_001",
  "enemigo_id": "rata_1",
  "cantidad": 4,
  "motivo": "Tyr golpea con su espada"
}
```

Requeridos: `campaña_id`, `combate_id`, `enemigo_id`, `cantidad` (entero
estricto > 0; rechaza `0`, negativos y `bool`). Reduce `hp_actual` del
enemigo sin bajar de 0 y recalcula su `estado`:

```text
hp_actual == 0                      -> derrotado
0 < hp_actual <= 25% hp_max          -> critico
25% hp_max < hp_actual < hp_max      -> herido
hp_actual == hp_max                  -> activo
```

No aplica resistencias ni vulnerabilidades. Devuelve `combate_id`,
`enemigo_id`, `hp_antes`, `hp_despues`, `estado` y el `combate` completo
actualizado.

## `combate_terminar`

```json
{
  "campaña_id": "campana_demo",
  "combate_id": "combate_001",
  "resultado": "Tyr derrota a las ratas y encuentra una trampilla bajo los barriles.",
  "motivo": "enemigos derrotados"
}
```

Requeridos: `campaña_id`, `combate_id`. Marca el combate como `terminado` y,
si era el combate activo de la campaña, libera la referencia activa (la
campaña queda sin combate activo). `resultado`/`motivo` son texto libre que
se registra en el evento auditable; no se persisten como campo del combate.
**No otorga XP automáticamente**: usa `hp_xp.otorgar_xp` aparte.

## Eventos auditables

Cada mutación registra un `Evento` (F3.1) en `eventos.jsonl` vía
`RegistroEventosEstado` (igual que `hp_xp.*`):

| Evento | Datos mínimos |
|---|---|
| `combate_iniciado` | `campaña_id`, `combate_id`, `personaje_id`, `num_enemigos` |
| `enemigo_añadido` | `campaña_id`, `combate_id`, `enemigo_id`, `nombre` |
| `daño_enemigo` | `campaña_id`, `combate_id`, `enemigo_id`, `cantidad`, `hp_antes`, `hp_despues`, `estado`, `motivo` |
| `combate_terminado` | `campaña_id`, `combate_id`, `resultado`, `motivo` |

`combate_estado` no registra evento (es de solo lectura).

## Errores

`campaña_id`/`personaje_id`/`combate_id`/`enemigo_id` vacíos o faltantes,
combate inexistente, enemigo inexistente en el combate, id de enemigo
duplicado, `cantidad` inválida, o combate activo ya en curso al iniciar uno
nuevo → `ResultadoHerramienta(ok=False, errores=[...])`. Sin tracebacks al
LLM.

## Limitaciones (F5.1)

- Sin grid/casillas, iniciativa compleja, economía de acciones, reacciones,
  ataques de oportunidad, cobertura, flanqueo ni áreas de efecto.
- Sin salvaciones de muerte, resistencias/vulnerabilidades ni hechizos.
- Sin XP automática, balance automático, IA táctica enemiga ni bestiario
  completo.
- Sin inyección de combate al contexto narrativo (ver
  [`../estado/combate.md`](../estado/combate.md#memoria-narrativa)).
- El LLM no está obligado a usar estas tools: el DM decide cuándo una escena
  amerita abrir un combate narrativo.
