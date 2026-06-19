# Tools `resumen.*` (F4.2)

> Módulo: `dm_agent.herramientas.resumen` · Fase: F4.2

## Propósito

Generar un resumen narrativo con el LLM y guardarlo como
`EntradaNarrativa(tipo="resumen")` en la bitácora de la campaña. Ver
[`../memoria/resumenes.md`](../memoria/resumenes.md). No registran evento
mecánico. Coherente con D17 (continuidad narrativa, no log táctico).

## Tools

| Interno | API (LLM) | Llama al LLM | Persiste |
|---|---|---|---|
| `resumen.entradas` | `resumen_entradas` | sí | entrada `resumen` |
| `resumen.texto` | `resumen_texto` | sí | entrada `resumen` |

## `resumen_entradas`

```json
{"campaña_id": "campana_demo", "limite": 20, "sesion_id": "sesion_001"}
```
Resume las últimas `limite` entradas de la bitácora. Error controlado si no hay
entradas. Devuelve `{"ok": true, "entrada": {…tipo:"resumen"…}}`.

## `resumen_texto`

```json
{"campaña_id": "campana_demo", "texto": "Texto largo de escena o sesión…", "sesion_id": "sesion_001"}
```
Resume el `texto` proporcionado. Error controlado si está vacío.

## Errores

Texto/entradas vacíos, `limite` inválido o fallo del endpoint →
`ResultadoHerramienta(ok=False, errores=[...])`. Sin tracebacks al LLM.

## Límites (F4.2)

- Las tools están **habilitadas** pero no se ejecutan solas al cerrar sesión.
- **No hay inyección automática** de los resúmenes al contexto del agente (F4.3).
- Sin RAG, memoria vectorial, preparación de siguiente sesión, combate, reglas
  adaptadas ni streaming.
