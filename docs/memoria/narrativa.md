# Memoria narrativa (F4.1)

> Módulos: `dm_agent.esquemas.narrativa` (modelo) ·
> `dm_agent.memoria.narrativa` (gestor) · `dm_agent.herramientas.narrativa` (tools).

## Eventos mecánicos vs memoria narrativa

Dos sistemas **distintos y complementarios**, no se mezclan:

| | Eventos mecánicos (`eventos.jsonl`) | Memoria narrativa (`narrativa/`) |
|---|---|---|
| Responde a | **qué cambió mecánicamente** (HP, XP, inventario) | **qué pasó en la ficción** |
| Modelo | `esquemas.evento.Evento` | `esquemas.narrativa.EntradaNarrativa` |
| Lo escriben | `hp_xp.*`, `inventario.*` | `narrativa.*` |
| Contenido | deltas auditables | decisiones, pistas, PNJ, lugares, consecuencias |

## Estructura de almacenamiento

```text
storage/
└── campañas/
    └── <campaña_id>/
        └── narrativa/
            ├── bitacora.md      (legible por humanos, append-only)
            └── entradas.jsonl   (una EntradaNarrativa por línea)
```

Raíz tomada de `config/proyecto.json → rutas.storage`.

## `EntradaNarrativa`

```text
id · timestamp · campaña_id · sesion_id? · tipo · titulo? · contenido ·
tags[] · importancia(1–5) · origen?(usuario|agente|sistema|resumen) · version_schema
```

Validaciones: `campaña_id`, `tipo` y `contenido` no vacíos; `importancia` ∈ [1,5];
`origen` (si se da) ∈ {usuario, agente, sistema, resumen}. `tipo` es texto libre,
sugerido: `escena, decision, pista, pnj, lugar, consecuencia, nota, resumen`.

## Formato Markdown (`bitacora.md`)

```markdown
## 2026-06-19T10:30:00+00:00 — Decision: Acepta el pacto de la bruja

Tyr aceptó llevar el medallón hasta las ruinas, aunque sospecha que oculta algo.

Tags: bruja, pacto, ruinas
Importancia: 4
Origen: agente
```

## Formato JSONL (`entradas.jsonl`)

Una línea por entrada = `EntradaNarrativa.model_dump_json()`. Append-only.

## Tools

- `narrativa.registrar` (`narrativa_registrar`): valida y persiste una entrada
  (JSONL + Markdown). No registra evento mecánico.
- `narrativa.reciente` (`narrativa_reciente`): devuelve las últimas entradas
  (JSON estructurado + `markdown`). No modifica nada.

Ver [`../tools/narrativa.md`](../tools/narrativa.md).

## Límites de F4.1

- **No hay resumen automático** (con LLM): F4.2.
- **No hay inyección automática** de memoria al contexto del agente: F4.3.
- No hay RAG ni memoria vectorial.
- No hay PNJ / facciones / localizaciones **estructurados** (solo texto + tags).
- Las tools están **habilitadas** pero el agente no las usa por sí mismo todavía.
