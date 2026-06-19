# ADR-0003 — Backend de configuración

- **Estado:** Aceptada (F1.1, 2026-06-19)
- **Decisión abierta original:** D3

## Contexto

Hay tres clases de datos: configuración leída por código, datos curados a mano
y registros append-only (logs/eventos).

## Decisión

- **JSON** para configs leídas por código: `modelos.json`, `perfiles.json`, `proyecto.json`.
- **YAML/Markdown** para datos curados por humanos: skills, tonos, lore, PNJ, facciones.
- **JSONL** para logs y eventos.

## Consecuencias

- JSON es rápido de parsear y no requiere dependencias extra para las configs.
- YAML/Markdown son cómodos para edición humana (frontmatter de skills, lore).
- JSONL permite append-only auditable de eventos sin reescribir el fichero.
