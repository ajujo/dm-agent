# ADR-0005 — Persistencia inicial

- **Estado:** Aceptada (F1.1, 2026-06-19)
- **Decisión abierta original:** D5
- **Implementación:** Fases 2–4

## Contexto

El sistema es local-first y debe poder cerrar y reabrir una campaña sin perder
estado. Hay estado mutable, eventos auditables, bitácora narrativa y datos curados.

## Decisión

- **JSON** para estado mutable (fichas, estado de combate, campaña).
- **JSONL** append-only para eventos/logs.
- **Markdown** para bitácora narrativa y resúmenes de sesión.
- **YAML** para datos curados.
- **SQLite** diferido a F11 (o antes si el volumen lo justifica).

## Consecuencias

- Sin dependencias de base de datos al principio; todo legible/auditable a mano.
- La migración a SQLite queda como decisión futura cuando el volumen lo requiera.
