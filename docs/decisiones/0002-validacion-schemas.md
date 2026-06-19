# ADR-0002 — Validación de schemas

- **Estado:** Aceptada (F1.1, 2026-06-19)
- **Decisión abierta original:** D2

## Contexto

El estado mecánico (fichas, combate, inventario) debe ser auditable y validado.
Se evaluó `pydantic` v2, `dataclasses` + `jsonschema` y `attrs`.

## Decisión

Usar **`pydantic` v2** para la validación y serialización de esquemas de datos.

## Consecuencias

- Ya está declarado en `pyproject.toml` (`pydantic>=2.6`), sin coste de dependencia extra.
- Validación fuerte, serialización JSON y versionado de esquemas listos para F3–F5.
- Los esquemas de parámetros de **herramientas** se siguen expresando como JSON Schema
  plano (formato que esperan las APIs OpenAI-compatible), no necesariamente como
  modelos `pydantic`.
