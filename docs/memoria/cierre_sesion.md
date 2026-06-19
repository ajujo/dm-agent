# Cierre y preparación de sesión (F4.4)

> Módulos: `dm_agent.memoria.cierre_sesion` (`CierreSesionNarrativa`) ·
> `dm_agent.herramientas.sesion` (tools) · `prompts/cierre_sesion.md` ·
> comando REPL `/cerrar`.

## Qué es

Cerrar una sesión = pedir al LLM, a partir de la **transcripción de la sesión**,
dos cosas y guardarlas en la memoria narrativa de la campaña:

1. un **resumen de cierre** (`EntradaNarrativa` `tipo="resumen"`): estado actual,
   decisiones, PNJ/lugares/pistas, consecuencias abiertas;
2. una **preparación de la próxima sesión** (`tipo="siguiente_sesion"`): el punto
   exacto de arranque y los hilos abiertos.

Ambas entradas comparten `campaña_id` y `sesion_id` (enlace claro campaña↔sesión).

## Diferencia con `resumen.*` (F4.2)

- `resumen.*` produce **un** resumen (de un texto o de entradas) — una sola
  entrada `resumen`.
- `sesion.*` (cierre) produce **dos** entradas a la vez (resumen **+**
  preparación), a partir de la **transcripción de una sesión JSONL**, y está
  pensado para el final de la partida.

## Relación con la memoria inyectada (F4.3)

Las entradas que genera el cierre (sobre todo el `resumen` y la
`siguiente_sesion`) son entradas narrativas normales: en la próxima sesión, el
`ConstructorContextoMemoria` (F4.3) las recoge y las inyecta como contexto, de
modo que el DM "retoma" por el punto de arranque. Así se cierra el bucle de
continuidad.

## Campaña y sesión (decisión F4.4)

Solución mínima (sin selector de campañas ni rediseño del REPL):

- `campaña_id` = `config/proyecto.json → campaña_activa`, o `campana_demo` por defecto.
- `sesion_id` = el `id` de la sesión JSONL activa del REPL.

`Sesion.texto_para_resumen()` traduce el historial JSONL a texto legible
(`Usuario:` / `DM:` / `Tool ...` / `Resultado ...`, truncando lo muy largo); no
se vuelca el JSON bruto.

## Prompt (`prompts/cierre_sesion.md`)

Prompt fijo y versionado. Pide salida en español con dos encabezados literales:
`# Resumen de cierre` y `# Preparación de próxima sesión`. Prohíbe inventar,
spoilers, resolver decisiones pendientes, tocar reglas/ficha e iniciar escena nueva.

### Parseo y degradación

Se parten las dos secciones por sus encabezados. **Degradación documentada**: si
el modelo no devuelve los encabezados esperados, todo el texto se guarda como
resumen y la preparación queda como `"Pendiente de preparar a partir del resumen
anterior."`.

## Comando `/cerrar`

En el REPL, `/cerrar` cierra la **sesión activa** con la **campaña activa**,
muestra el resumen y el punto de arranque, y **no** sale del REPL. Si el endpoint
falla, muestra un error limpio (sin traceback). No hay cierre automático al usar
`/salir`.

## Tools

- `sesion.cerrar` (`sesion_cerrar`): cierra una sesión por `sesion_id` (lee su
  JSONL). Error controlado si la sesión no existe.
- `sesion.cerrar_texto` (`sesion_cerrar_texto`): cierra a partir de un `texto`
  dado (útil para cierres manuales y tests).

Ver [`../tools/sesion.md`](../tools/sesion.md). Registradas en el agente, pero no
se fuerza su uso automático.

## Límites (F4.4)

- **No hay cierre automático al salir** (`/salir` no cierra).
- **No hay selector completo de campaña** (solo `campaña_activa`).
- Sin RAG, memoria vectorial, PNJ/lugares estructurados, combate, reglas
  adaptadas ni streaming.
- Coherente con D17: continuidad, tono y punto de arranque, no gestión táctica.
