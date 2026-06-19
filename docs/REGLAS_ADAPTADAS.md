# Reglas adaptadas — D&D 5.5 narrativo en solitario

> Decisión de base: [ADR-0017](./decisiones/0017-dnd55-narrativo-solitario.md) (D17).
> **Estado: documentación.** No hay todavía motor de reglas adaptadas, ni tools,
> ni sistema de aprobación, ni catálogo de hechizos adaptados.

`dm-agent` usa D&D 5.5 como base de resolución e inspiración, pero lo adapta a una
experiencia narrativa en solitario (teatro de la mente, sin tablero ni figuras)
mediante **reglas caseras persistentes aprobadas por el usuario**.

## Capas de reglas

1. **Regla base D&D 5.5.**
2. **Adaptación teatro de la mente / juego en solitario.**
3. **Preferencias de campaña del usuario.** (prevalece sobre 2, y 2 sobre 1)

## Áreas que requerirán adaptación futura

Movimiento · alcance · áreas de efecto · cobertura · posición · flanqueo ·
reacciones · acciones adicionales · iniciativa · encuentros balanceados para
personaje único · habilidades sociales · sigilo · percepción · investigación ·
hechizos tácticos · invocaciones · compañeros · trampas · exploración · descanso
corto/largo · economía de recursos · muerte y consecuencias · dificultad
heroica/gritty · ritmo narrativo.

## Flujo futuro de adaptación

```text
1. El agente detecta una regla/habilidad/hechizo difícil de aplicar sin tablero
   o con un solo personaje.
2. Propone adaptación.
3. Explica:
   - regla base;
   - problema en juego narrativo/solitario;
   - opción A: fiel a D&D;
   - opción B: narrativa/simple;
   - opción C: heroica/cinemática.
4. El usuario elige.
5. La decisión se guarda como regla casera persistente.
6. El sistema la aplica automáticamente en adelante.
```

## Ejemplos de adaptación (documentales)

### Movimiento

```text
Regla táctica: pies/casillas.
Adaptación narrativa:
- cerca
- media distancia
- lejos
- fuera de alcance
```

### Área de efecto

```text
Regla táctica: radio, cono, línea.
Adaptación narrativa:
- un objetivo
- varios objetivos cercanos
- grupo
- zona completa
```

### Reacciones

```text
El DM Agent recuerda automáticamente si el personaje ya usó reacción en la
ronda/escena.
```

### Encuentros

```text
Los encuentros no se diseñan para party estándar, sino para un héroe solitario
con posibles compensaciones narrativas.
```

## Qué NO cubre todavía

- No existe `rules_adapter.py` ni motor de adaptación.
- No hay tools de reglas adaptadas ni sistema de aprobación/persistencia de reglas
  caseras.
- No hay catálogo de hechizos/invocaciones adaptados.
- Este documento es la guía de diseño; la implementación se planificará en una
  fase posterior dedicada a reglas.
