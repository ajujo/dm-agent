# compendio/

Datos de juego (monstruos, armas, armaduras, conjuros, progresión).

**Estado actual.** Vacío. En la Fase 5 se migrarán desde `dnd5e-framework/compendio/`:

- `monstruos.json` (327 SRD)
- `armas.json`, `armaduras_escudos.json`
- `progresion_niveles.json`
- `conjuros.json` (completar)
- `miscelanea.json`

## Licencia

Antes de migrar cualquier contenido SRD, crear `compendio/LICENSE` con el texto de la licencia aplicable (SRD 5.1 bajo CC-BY 4.0 / OGL 1.0a según versión). Decisión: ver [`../docs/decisiones/0013-licencia.md`](../docs/decisiones/0013-licencia.md).

> El código del proyecto es Apache-2.0 (ver `../LICENSE`). El contenido del compendio lleva **licencia separada** y **no se migrará nada hasta que exista `compendio/LICENSE`**.

**Prohibido** incluir material no SRD (PHB, MM extendido, módulos comerciales sin licencia).
