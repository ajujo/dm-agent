# ADR-0001 — Lengua de identificadores

- **Estado:** Aceptada (F1.1, 2026-06-19)
- **Decisión abierta original:** D1

## Contexto

El proyecto hereda estructura de `dnd5e-framework` (en español) y es de uso
personal en español. Hay que fijar en qué idioma se nombran identificadores,
logs y texto de usuario.

## Decisión

- **Español** para el dominio RPG: `ficha`, `combate`, `campaña`, `herramientas`,
  `memoria`, `reglas`, etc.
- **Inglés** solo cuando es estándar técnico o ayuda a la interoperabilidad:
  `schema`, `httpx`, `OpenAI-compatible`, `JSONL`.

## Consecuencias

- Coherencia con el reference implementation y con el CLAUDE.md (naming en español).
- Los nombres internos de herramientas siguen `<toolset>.<accion>` en español
  (ver [ADR sobre nombres API](../../src/dm_agent/herramientas/registro.py) para
  la conversión a nombres seguros de API).
