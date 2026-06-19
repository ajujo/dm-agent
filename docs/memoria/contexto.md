# Inyección de memoria narrativa al contexto (F4.3)

> Módulos: `dm_agent.memoria.contexto` (`ConstructorContextoMemoria`) ·
> integrado en `dm_agent.nucleo.agente.AgenteDM` y `nucleo.bucle`.

## Qué se inyecta

En cada turno, `AgenteDM` antepone al historial un **segundo mensaje `system`**
con un bloque Markdown compacto de memoria narrativa (si existe), justo después
del system prompt base del DM y **antes** del mensaje del usuario:

```text
1. system: prompt base del DM
2. system: bloque de memoria narrativa  (solo si hay memoria)
3. historial user/assistant de la sesión
4. (mensaje del usuario, que ya está en el historial)
```

El system prompt base **no se sustituye**; la memoria es un añadido.

## De dónde sale

`ConstructorContextoMemoria.construir_bloque_memoria(campaña_id)` lee la bitácora
narrativa (`GestorMemoriaNarrativa`) y compone:

- **Resumen reciente**: el último `EntradaNarrativa` de tipo `resumen` (F4.2), si
  `incluir_resumenes` está activo.
- **Entradas recientes**: las últimas `limite_entradas` entradas **no-resumen**,
  una línea compacta por entrada (`- [tipo] título o contenido`).

Lee una ventana acotada (200 entradas) para localizar el último resumen aunque no
esté entre las más recientes, pero **solo inyecta** resumen + N entradas. No
modifica ficheros ni llama al LLM.

## Formato

```markdown
# Memoria narrativa de campaña

Usa esta memoria solo para mantener continuidad. No inventes hechos nuevos a
partir de ella. Si algo no está claro, pregunta o mantén la ambigüedad.

## Resumen reciente

...

## Entradas recientes

- [decision] Tyr aceptó el pacto de la bruja...
- [pista] El medallón vibra cerca de las ruinas...
```

Si no hay nada que mostrar, devuelve cadena vacía y no se añade el segundo system.

Desde **F4.6**, si se pasa un `gestor_entidades`, el bloque también puede
incluir una sección `## Entidades importantes` (PNJ, lugares, pistas,
objetivos, frentes abiertos). Ver
[`entidades.md`](entidades.md#inyección-al-contexto) para el detalle.

## Configuración

`config/proyecto.json`:

```json
{
  "campaña_activa": "campana_demo",
  "memoria": {
    "inyectar_narrativa": true,
    "limite_entradas_contexto": 8,
    "incluir_resumenes": true,
    "inyectar_entidades": true,
    "limite_entidades_contexto": 8
  }
}
```

Comportamiento seguro si falta: `inyectar_narrativa=true`, `limite=8`,
`incluir_resumenes=true`, `campaña_activa="campana_demo"`,
`inyectar_entidades=true`, `limite_entidades_contexto=8`. Si
`inyectar_narrativa` es `false`, no se inyecta nada (tampoco entidades).

### Campaña activa (decisión F4.3)

El REPL aún no tiene selector de campaña. Solución mínima: se usa
`proyecto.json → campaña_activa` y, si no existe, la campaña por defecto
**`campana_demo`**. El selector completo de campañas se hará más adelante; aquí
no se rediseña el REPL.

## Diferencias

- **vs historial de sesión**: el historial son los turnos literales de la sesión
  actual (`storage/sesiones/*.jsonl`); la memoria narrativa es continuidad
  curada y persistente de la campaña (decisiones, pistas, resúmenes).
- **vs RAG**: esto **no** es RAG ni búsqueda semántica. Es una ventana reciente
  fija (último resumen + N entradas). No hay embeddings ni recuperación por
  relevancia.

## Límites (F4.3+F4.6) y futuro

- Ventana reciente fija; sin recuperación semántica ni por tags.
- Desde F4.6 hay PNJ/lugares/pistas/objetivos/frentes **estructurados**
  (`entidad.*`, ver [`entidades.md`](entidades.md)), pero sin extracción
  automática, sin facciones complejas y sin grafo de relaciones validado.
- Sin resumen automático al cerrar sesión (las tools `resumen.*` son manuales).
- Sin combate, reglas adaptadas ni streaming.
- Coherente con D17: continuidad narrativa, no log táctico.

Futuro: selección de campaña, recuperación por relevancia/tags, y
extracción automática de entidades desde la narración.
