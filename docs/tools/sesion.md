# Tools `sesion.*` (F4.4)

> Módulo: `dm_agent.herramientas.sesion` · Fase: F4.4

## Propósito

Cerrar una sesión generando, con el LLM, un **resumen de cierre** + una
**preparación de la próxima sesión**, y guardarlos como dos `EntradaNarrativa`
(`resumen` y `siguiente_sesion`) en la bitácora de la campaña. Ver
[`../memoria/cierre_sesion.md`](../memoria/cierre_sesion.md). No registran evento
mecánico. Coherente con D17.

## Tools

| Interno | API (LLM) | Fuente | Persiste |
|---|---|---|---|
| `sesion.cerrar` | `sesion_cerrar` | transcripción de la sesión JSONL (`sesion_id`) | 2 entradas |
| `sesion.cerrar_texto` | `sesion_cerrar_texto` | `texto` proporcionado | 2 entradas |

## `sesion_cerrar`

```json
{"campaña_id": "campana_demo", "sesion_id": "sesion-20260619-123000"}
```
Localiza `storage/sesiones/<sesion_id>.jsonl`, genera su texto legible y lo
cierra. Error controlado si la sesión no existe.

## `sesion_cerrar_texto`

```json
{"campaña_id": "campana_demo", "sesion_id": "manual_001", "texto": "Texto largo de lo ocurrido…"}
```
Cierra a partir del `texto` dado (cierres manuales y tests).

## Salida

```json
{"ok": true,
 "resumen": { "...tipo:resumen..." },
 "preparacion": { "...tipo:siguiente_sesion..." }}
```

## Errores

Texto vacío, cierre vacío del modelo, sesión inexistente o fallo del endpoint →
`ResultadoHerramienta(ok=False, errores=[...])`. Sin tracebacks al LLM.

## Límites (F4.4)

- No hay cierre automático al salir del REPL (ver comando `/cerrar`).
- Sin selector completo de campaña, RAG, combate, reglas adaptadas ni streaming.
