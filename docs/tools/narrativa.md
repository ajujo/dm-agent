# Tools `narrativa.*` (F4.1)

> Módulo: `dm_agent.herramientas.narrativa` · Fase: F4.1

## Propósito

Registrar y consultar la **bitácora narrativa** de una campaña: decisiones,
pistas, PNJ, lugares, consecuencias, escenas y notas. Es **ficción**, distinta de
los eventos mecánicos (`eventos.jsonl`). Ver
[`../memoria/narrativa.md`](../memoria/narrativa.md). Coherente con D17 (narrativo
en solitario / teatro de la mente): favorece continuidad y consecuencias, no es un
log táctico.

## Tools

| Interno | API (LLM) | Persiste | Evento mecánico |
|---|---|---|---|
| `narrativa.registrar` | `narrativa_registrar` | sí (bitácora) | no |
| `narrativa.reciente` | `narrativa_reciente` | no | no |

## `narrativa_registrar`

```json
{
  "campaña_id": "campana_demo",
  "sesion_id": "sesion_001",
  "tipo": "decision",
  "titulo": "Acepta el pacto de la bruja",
  "contenido": "Tyr aceptó llevar el medallón hasta las ruinas, aunque sospecha que oculta algo.",
  "tags": ["bruja", "pacto", "ruinas"],
  "importancia": 4,
  "origen": "agente"
}
```
Requeridos: `campaña_id`, `tipo`, `contenido`. Genera `id` y `timestamp`. Valida
con `EntradaNarrativa`, persiste en `entradas.jsonl` + `bitacora.md`. Devuelve
`{"ok": true, "entrada": {…}}`. **No** registra evento en `eventos.jsonl`.

## `narrativa_reciente`

```json
{"campaña_id": "campana_demo", "limite": 10}
```
Devuelve `{"ok": true, "entradas": [...], "markdown": "..."}` con las últimas
`limite` entradas. No modifica nada ni registra evento.

## Errores

`contenido`/`tipo`/`campaña_id` vacíos, `importancia` fuera de [1,5], `origen`
inválido o `limite` no entero ≥ 1 → `ResultadoHerramienta(ok=False, errores=[...])`.
Sin tracebacks al LLM.

## Límites (F4.1)

- No hay **resumen automático** (F4.2) ni **inyección automática** al contexto del
  agente (F4.3); las tools están habilitadas pero no se usan solas.
- No hay RAG, memoria vectorial ni PNJ/lugares estructurados.
- Sin combate, reglas adaptadas ni streaming.
