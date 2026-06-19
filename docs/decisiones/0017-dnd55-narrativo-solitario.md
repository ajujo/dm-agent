# ADR-0017 — D&D 5.5 narrativo en solitario / teatro de la mente

- **Estado:** Aceptada (F3.2, 2026-06-19)
- **Decisión abierta original:** D17
- **Implementación:** ninguna todavía — esto es arquitectura y documentación.

## Contexto

`dm-agent` es una herramienta personal y de uso privado. Por higiene técnica, el
**motor** debe permanecer separado del **contenido privado importado**, sin
necesidad de obsesionarse con copyright pero manteniendo una arquitectura limpia:

```text
src/                  -> motor limpio
config/               -> configuración
storage/              -> partidas privadas (gitignored)
compendio/            -> contenido permitido/documentado
compendio_privado/    -> contenido privado del usuario (gitignored)
```

`compendio_privado/` se añade a `.gitignore`.

`dm-agent` **no** pretende ser un simulador táctico exacto de tablero. Se basa en
D&D 5.5 pero lo adapta a un único jugador, fantasía narrativa y teatro de la
mente: sin figuras, sin tablero, escenas fluidas, menos microgestión de
casillas/pies/pulgadas y más continuidad narrativa, interpretación y decisiones
aprobadas por el usuario.

## Decisión

> **dm-agent usa D&D 5.5 como base de resolución e inspiración, pero lo adapta a
> una experiencia narrativa en solitario mediante reglas caseras persistentes
> aprobadas por el usuario.**

### Tres capas de reglas

1. **Regla base D&D 5.5.**
2. **Adaptación teatro de la mente / juego en solitario.**
3. **Preferencias de campaña del usuario.**

La capa 3 prevalece sobre la 2, y la 2 sobre la 1, cuando hay conflicto.

## Consecuencias

- El motor (`src/`) no incrusta contenido privado; el contenido del usuario vive
  en `compendio_privado/` (gitignored).
- Las futuras reglas adaptadas serán **datos** (reglas caseras persistentes
  aprobadas por el usuario), no lógica incrustada: ver el flujo de adaptación en
  `docs/REGLAS_ADAPTADAS.md`.
- La fase de reglas adaptadas (motor de adaptación, tools de aprobación, catálogo
  de hechizos adaptados) queda planificada pero **no** se implementa aquí.

## No implementado a propósito

No se crean en esta tarea: `rules_adapter.py`, tools de reglas adaptadas, sistema
de aprobación de reglas ni base de datos de hechizos adaptados. Solo se deja la
arquitectura preparada y el catálogo de áreas a adaptar documentado en
`docs/REGLAS_ADAPTADAS.md`.
