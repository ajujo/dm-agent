---
name: ejemplo-escena-social
description: "Ejemplo mínimo de skill social. Sirve de plantilla y fixture de tests."
version: 0.1.0
modo: social
requiere_tools:
  - dados.tirar
lee:
  - ficha
  - estado_partida
  - pnj
modifica:
  - log_eventos
  - memoria_narrativa
tono_aplicable:
  - epica_heroica
  - intriga_misterio
  - exploracion_maravillas
nivel_juego:
  - todos
---

# Cuándo usar

Cuando el jugador entabla conversación con un PNJ y la escena no es combate ni viaje.

# Cuándo NO usar

- Si el contexto es combate activo → usa `dirigir-combate`.
- Si el jugador pide investigar un lugar sin PNJ presentes → usa `exploracion`.

# Procedimiento

1. Identificar PNJ implicado y cargar su ficha desde memoria de PNJ.
2. Determinar actitud inicial (amistosa / neutral / hostil) según historial y contexto.
3. Narrar la apertura de la escena en 2-4 frases.
4. Cuando el jugador intente persuadir / engañar / intimidar:
   - Pedir tirada con `dados.tirar` (`1d20+mod`) contra CD apropiada.
   - Resolver según resultado.
5. Cerrar la escena con consecuencias narrativas:
   - Cambios de actitud del PNJ.
   - Información revelada (registrada en memoria narrativa).
   - Posibles rumores o pistas.
6. Emitir eventos: `pnj_interactuado`, `informacion_revelada`, `actitud_modificada`.

# Criterios de éxito

- El PNJ responde de forma coherente con su carácter y motivaciones.
- Toda tirada relevante pasa por la tool.
- No se filtra información que el PNJ no conoce.

# Riesgos

- Filtración de spoilers si el PNJ "sabe" cosas que la aventura aún no revela.
- Inventar datos sobre el PNJ que contradicen su ficha.

# Ejemplos

(A documentar con casos reales una vez exista runtime.)
