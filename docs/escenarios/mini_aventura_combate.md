# Mini escena: ratas en el sótano (combate narrativo sin grid)

> Escena de referencia para `docs/PRUEBA_MANUAL_F5_COMBATE.md` (F5.6).
> Pensada para probar el flujo completo de `combate.*` con un endpoint LLM
> real, no para jugarse "a secas": es deliberadamente corta y de bajo riesgo.

## Setup

- **PJ**: Tyr (Guerrero nivel 1, `hp_max=12`, `ca=15`) — ver
  `docs/PRUEBA_MANUAL_F5_COMBATE.md`, paso 2, para crear la ficha.
- **Enemigos**: dos ratas gigantes simples.

| Campo | `rata_1` | `rata_2` |
|---|---|---|
| `hp_max` / `hp_actual` | 7 / 7 | 7 / 7 |
| `ca` | 12 | 12 |
| `distancia` | `cuerpo_a_cuerpo` | `corta` |
| `mod_destreza` | 0 | 0 |

- **Elemento narrativo**: una lámpara caída en el suelo, todavía encendida.
  Puede justificar ventaja (Tyr la usa para distraer/cegar a una rata) o
  desventaja (una rata vuelca aceite y dificulta el terreno).
- **Gancho de reacción**: si Tyr abandona `cuerpo_a_cuerpo` sin cubrirse, la
  rata que estaba trabada con él puede intentar un ataque de oportunidad
  *narrativo* — propuesto, nunca aplicado sin confirmación (D-COMBATE-04).

## Texto de escena

> Tyr baja al sótano de una posada. Oye arañazos detrás de unos barriles. Dos
> ratas gigantes emergen entre sacos rotos. Una de ellas está cuerpo a
> cuerpo; la otra está a distancia corta. Hay una lámpara caída que puede
> servir para distraerlas.

## Guion sugerido (no obligatorio)

1. **Iniciar combate** con las dos ratas como enemigos.
2. **Tirar iniciativa** para Tyr y las ratas.
3. **Atacar** a `rata_1` (cuerpo a cuerpo); si Tyr usa la lámpara para
   distraerla, pedir la tirada **con ventaja**.
4. **Registrar la acción de turno** de Tyr.
5. Narrar que Tyr se retira de `cuerpo_a_cuerpo` hacia `corta` sin cubrirse,
   para encarar a `rata_2`.
6. **Proponer una reacción**: `rata_1` podría tener un ataque de oportunidad.
7. **Confirmar o rechazar** la reacción propuesta.
8. Si se confirma y tiene sentido aplicarla, hacer la **llamada explícita**
   de ataque (`combate.atacar_personaje`) — nunca automática.
9. **Avanzar turno** cuando Tyr termine su acción.
10. Repetir ataques/turnos según convenga; **terminar el combate** cuando las
    ratas queden derrotadas o huyan.
11. **Cierre narrativo**: Tyr encuentra algo tras el combate (p. ej. una
    trampilla bajo los barriles rotos) — buen gancho para registrar en
    memoria narrativa (`narrativa.registrar`) y para la próxima escena.

## Qué NO debería pasar

- Que el modelo narre daño o HP sin que aparezca una tool call
  (`combate_dano_enemigo`/`combate_atacar_enemigo`/`combate_atacar_personaje`/`hp_xp_aplicar_dano`).
- Que el turno avance solo porque alguien atacó (debe ser una llamada
  explícita a `combate_avanzar_turno`).
- Que confirmar la reacción de `rata_1` aplique el ataque por sí sola (debe
  requerir una llamada aparte a una tool de ataque).
- Que aparezca medición de casillas, pies o pulgadas: las distancias son
  `cuerpo_a_cuerpo`/`corta`/`media`/`larga`/`fuera_de_alcance`, nada más.

## Después de la escena

Ver `docs/PRUEBA_MANUAL_F5_COMBATE.md` para el checklist de eventos a
verificar en `storage/campañas/<campaña_id>/eventos.jsonl` y los criterios de
aceptación completos.
