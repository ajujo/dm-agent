# Entidades narrativas estructuradas (F4.6)

> Módulos: `dm_agent.esquemas.entidades` (modelos) ·
> `dm_agent.memoria.entidades` (`GestorEntidadesNarrativas`) ·
> `dm_agent.herramientas.entidades` (tools) ·
> integración en `dm_agent.memoria.contexto.ConstructorContextoMemoria`.

## Bitácora vs resumen vs entidades

Tres sistemas complementarios, no se mezclan:

| | Bitácora narrativa (F4.1) | Resumen (F4.2) | Entidades (F4.6) |
|---|---|---|---|
| Responde a | **qué pasó** | **qué pasó, condensado** | **quién/qué existe, dónde está, qué sabemos, qué queda pendiente** |
| Modelo | `EntradaNarrativa` | `EntradaNarrativa(tipo="resumen")` | `PNJ` / `Lugar` / `Pista` / `Objetivo` / `FrenteAbierto` |
| Naturaleza | append-only (histórico) | append-only (histórico) | **estado actual** (guardar por `id` reemplaza) |
| Lo escriben | `narrativa.*` | `resumen.*` | `entidad.*` |

Las entidades no sustituyen a la bitácora: una pista puede aparecer mencionada
en una entrada `escena` de la bitácora y, además, tener su propia `Pista`
estructurada con `id`, `descripcion` y `resuelta`.

## Tipos soportados

- **PNJ**: `rol`, `actitud`, `ubicacion_id`, `relacion_con_personaje`.
- **Lugar**: `tipo`, `conectado_con` (lista de ids de otros lugares).
- **Pista**: `origen`, `relacionada_con`, `resuelta`.
- **Objetivo**: `prioridad`, `relacionado_con`. Estados sugeridos (libres, sin
  enum forzado): `pendiente`, `activo`, `resuelto`, `descartado`, `bloqueado`.
- **FrenteAbierto**: `amenaza`, `reloj` (entero 0–6, inspirado en relojes
  narrativos, sin motor de avance automático), `consecuencias`,
  `relacionado_con`.

Todos heredan de `EntidadBase`: `id`, `nombre`, `descripcion`, `estado`,
`tags[]`, `importancia` (1–5, default 3), `notas`, `version_schema` (=1).
`id` y `nombre` no pueden estar vacíos.

## Estructura de almacenamiento

```text
storage/
└── campañas/
    └── <campaña_id>/
        └── entidades/
            ├── pnj.json
            ├── lugares.json
            ├── pistas.json
            ├── objetivos.json
            └── frentes.json
```

Cada fichero es una **lista JSON** con el estado vigente de ese tipo (no
JSONL, no append-only). Escritura atómica (tmp + `os.replace`), igual que
`GestorEstado`. Guardar una entidad con un `id` ya presente en el fichero **la
reemplaza**; no se versiona el histórico de cambios de una entidad (para eso
está la bitácora narrativa).

## Tools

Ver [`../tools/entidades.md`](../tools/entidades.md) para el detalle de
parámetros. Resumen: `entidad.guardar_{pnj,lugar,pista,objetivo,frente}` y
`entidad.listar_{pnj,lugares,pistas,objetivos,frentes}`. Listar siempre
devuelve **ordenado por `importancia` descendente y luego `nombre`**; en una
campaña sin entidades de ese tipo, devuelve lista vacía.

## Inyección al contexto

`ConstructorContextoMemoria` admite un `gestor_entidades` opcional y un
`limite_entidades` (default 8). Si hay entidades, añade una sección compacta
**después** de las entradas recientes de la bitácora, dentro del mismo segundo
mensaje `system`:

```markdown
## Entidades importantes

### PNJ
- Mara, posadera: ayudó a Tyr. Estado: activa.

### Lugares
- Taberna del Ciervo Gris: punto de inicio.

### Pistas
- Llave oxidada: encontrada bajo una mesa.

### Objetivos
- Investigar los ruidos del sótano. Estado: activo.

### Frentes abiertos
- La bruja del medallón. Reloj: 2/6.
```

Cada tipo se trunca a `limite_entidades` (las primeras tras ordenar por
importancia). Cada línea se trunca a una longitud máxima para mantener el
bloque compacto. Si no hay ninguna entidad de ningún tipo, **no se añade la
sección** (y si tampoco hay nada de la bitácora, el bloque entero de memoria
es cadena vacía, igual que en F4.3).

### Configuración

`config/proyecto.json`:

```json
{
  "memoria": {
    "inyectar_narrativa": true,
    "limite_entradas_contexto": 8,
    "incluir_resumenes": true,
    "inyectar_entidades": true,
    "limite_entidades_contexto": 8
  }
}
```

Defaults seguros si falta la clave: `inyectar_entidades=true`,
`limite_entidades_contexto=8`. Si `inyectar_narrativa` es `false`, no se inyecta
memoria en absoluto (ni bitácora ni entidades): es el interruptor general.

## Límites (F4.6)

- **Sin extracción automática con LLM**: las entidades las guarda quien llama a
  la tool (el agente, si decide hacerlo, o tú a mano); no hay un paso que lea la
  narración y genere entidades solo.
- **Sin RAG ni memoria vectorial**: la inyección es una lista completa (hasta el
  límite) ordenada por importancia, no recuperación por relevancia semántica.
- **Sin relaciones complejas**: los campos `relacionado_con` /
  `relacionada_con` / `conectado_con` son ids sueltos en texto libre, no un
  grafo navegable ni validado por integridad referencial.
- Sin facciones, mapas ni quest engine: `Objetivo`/`FrenteAbierto` son
  registros planos, no un motor de progresión.
- Coherente con D17: ayuda a la continuidad narrativa en solitario, no es una
  wiki ni un simulador táctico.
