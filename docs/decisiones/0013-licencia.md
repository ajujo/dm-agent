# ADR-0013 — Licencia del proyecto

- **Estado:** Aceptada (F1.1, 2026-06-19)
- **Decisión abierta original:** D13

## Contexto

El proyecto mezcla código propio con la posibilidad futura de incluir contenido
de juego (SRD, monstruos, conjuros) y material de aventuras del usuario, con
licencias distintas.

## Decisión

- **Código:** Apache-2.0 (ver `LICENSE` y `pyproject.toml`).
- **Contenido SRD/compendio:** licencia separada en `compendio/LICENSE`, a definir
  **antes** de migrar ningún dato.
- **Material de aventuras/PDFs del usuario:** nunca redistribuir dentro del repo.

## Consecuencias

> ⚠️ No se migrará contenido SRD, compendio, monstruos, conjuros ni material
> externo hasta que exista `compendio/LICENSE` y se confirme la licencia aplicable.

- Apache-2.0 da concesión explícita de patentes y es permisiva.
- La separación de licencias evita contaminar el código con restricciones de
  contenido (p. ej. OGL/CC-BY del SRD).
