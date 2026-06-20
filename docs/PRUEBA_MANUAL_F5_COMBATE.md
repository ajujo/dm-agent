# Prueba manual de F5 (combate narrativo D&D sin grid)

> Mini-fase **F5.6**: validación manual, contra un endpoint LLM real, de una
> escena completa de combate narrativo D&D sin grid. No añade reglas nuevas;
> complementa al test integrado `tests/test_combate_integrado_f5.py`.

Esta guía verifica el ciclo completo de combate construido en F5.1–F5.5:
ficha → escena narrativa → `combate.iniciar` → enemigos → iniciativa → turnos →
ataques contra CA (con ventaja/desventaja) → acción de turno → propuesta de
reacción → confirmación/rechazo (sin aplicar daño) → aplicación explícita de
la reacción confirmada → avance de turno → cierre del combate → memoria
narrativa → cierre de sesión → continuidad.

Si vienes de `docs/PRUEBA_MANUAL_F4.md`, los pasos de levantar el endpoint y
crear la ficha son los mismos; aquí se asume que ya sabes hacerlo.

---

## 1. Preparación

```bash
cd /home/ajujo/Lab/Workspace/dm-agent
conda activate rpg
pip install -e .[dev]
python scripts/check_perfil.py
```

Levanta un endpoint OpenAI-compatible con tool-calling habilitado (ver
`docs/PRUEBA_MANUAL_F4.md`, paso 1, para el comando de `vLLM` recomendado).
Sin `--enable-auto-tool-choice` + el `--tool-call-parser` correcto, el modelo
charla pero nunca llama a las tools de combate.

Lanza el REPL:

```bash
dm-agent --perfil rapido --nueva --debug
```

`--nueva` empieza una sesión limpia; `--debug` muestra cada tool call que
ejecuta el agente — es la única forma fiable de comprobar que una mutación
mecánica (HP, iniciativa, daño) viene de una tool real y no de texto
inventado por el modelo. Comandos del REPL: `/ayuda`, `/continuar`, `/nueva`,
`/guardar`, `/cerrar`, `/debug`, `/salir`.

---

## 2. Estado inicial esperado

El REPL inyecta memoria narrativa y entidades de la campaña activa
(`config/proyecto.json` → `"campaña_activa": "campana_demo"`).

Si ya tienes `campana_demo`/`pj_tyr` de una prueba anterior (F4), puedes
reutilizarlos: lo único que importa es que la ficha exista con `hp_actual`,
`hp_max` y `ca` válidos. Si no existen todavía, créalos con las APIs del
proyecto (no edites JSON a mano):

```bash
conda activate rpg
python - <<'PY'
from dm_agent.estado.gestor import GestorEstado
from dm_agent.esquemas.ficha import Ficha

gestor = GestorEstado("storage")
ficha = Ficha.model_validate({
    "id": "pj_tyr",
    "nombre": "Tyr",
    "clase": "Guerrero",
    "nivel": 1,
    "raza": "Humano",
    "trasfondo": "Soldado",
    "atributos": {"fuerza": 15, "destreza": 12, "constitucion": 14,
                  "inteligencia": 10, "sabiduria": 11, "carisma": 9},
    "hp_max": 12, "hp_actual": 12, "ca": 15,
    "bonificador_competencia": 2, "xp": 0,
    "inventario": [],
})
ruta = gestor.guardar_ficha("campana_demo", ficha)
print("ficha guardada en", ruta)
PY
```

Estado inicial esperado antes de empezar:

- **Campaña activa**: `campana_demo` (o la que configures).
- **Ficha**: `pj_tyr`, `hp_actual = hp_max = 12`, `ca = 15`.
- **Inventario**: mínimo, no hace falta nada especial para combate.
- **Memoria narrativa**: puede estar vacía o tener entradas previas de F4;
  no afecta a esta prueba salvo para confirmar continuidad en el paso 10.
- **Sin combate activo**: si quedó uno de una prueba anterior, termínalo
  primero o usa una campaña nueva.

---

## 3. Mini escena de prueba

Escena pensada para forzar los ocho puntos del checklist (iniciativa,
ataques, ventaja/desventaja, acción de turno, reacción):

> Tyr baja al sótano de una posada. Oye arañazos detrás de unos barriles. Dos
> ratas gigantes emergen entre sacos rotos. Una de ellas está `cuerpo_a_cuerpo`;
> la otra está a distancia `corta`. Hay una lámpara caída que puede servir
> para distraerlas. Si Tyr se aparta de la rata cuerpo a cuerpo sin cubrirse,
> esta podría intentar un ataque de oportunidad.

Elementos cubiertos:

- **1 PJ**: Tyr.
- **2 enemigos sencillos**: `rata_1` (`cuerpo_a_cuerpo`), `rata_2` (`corta`).
- **1 elemento narrativo para ventaja/desventaja**: la lámpara caída (puede
  dar ventaja si Tyr la usa para distraer, o desventaja si una rata la usa
  contra él).
- **1 posible reacción/ataque de oportunidad**: la rata cuerpo a cuerpo si
  Tyr se retira sin cubrirse.
- **1 cierre narrativo**: Tyr derrota o ahuyenta a las ratas y encuentra algo
  (p. ej. una trampilla) tras el combate.

---

## 4. Prompts sugeridos para el usuario

Pega estos textos en el REPL, en orden. No son obligatorios palabra por
palabra; lo importante es que cada uno empuje al modelo a usar la tool
correspondiente.

**Arranque de la escena:**

```text
Inicia una escena de D&D narrativo con Tyr en el sótano de la posada. Hay dos
ratas gigantes, una cuerpo a cuerpo y otra a distancia corta. Usa las tools
cuando haya que modificar estado mecánico (combate, HP, iniciativa, daño).
No inventes HP ni daño sin tool.
```

**Iniciar combate y añadir enemigos:**

```text
Las ratas atacan. Inicia el combate y añade a las dos ratas como enemigos del
combate, con su HP y CA.
```

**Tirar iniciativa:**

```text
Tira la iniciativa para Tyr y para las dos ratas.
```

**Atacar:**

```text
Tyr ataca a la rata que tiene cuerpo a cuerpo con su espada larga.
```

**Usar ventaja:**

```text
Tyr usa la lámpara caída para distraer a la rata antes de atacar: debería
tener ventaja en esta tirada.
```

**Moverse fuera de cuerpo_a_cuerpo:**

```text
Tyr decide retirarse de la rata cuerpo a cuerpo hacia distancia corta, sin
cubrirse, para ir a por la otra rata.
```

**Proponer reacción:**

```text
¿Tiene sentido que la rata cuerpo a cuerpo intente un ataque de oportunidad
ahora que Tyr se retira sin cubrirse? Si es así, propón esa reacción.
```

**Confirmar/rechazar reacción:**

```text
Confirmo que la rata puede intentar ese ataque de oportunidad.
```

(o, para probar el otro camino: `No, Tyr se cubre a tiempo: rechaza esa reacción.`)

**Cerrar combate:**

```text
Las ratas están derrotadas o huyen. Termina el combate y describe brevemente
cómo termina la escena.
```

**Cerrar sesión:**

```text
/cerrar
```

---

## 5. Flujo esperado de tools

Con `--debug` deberías ver, aproximadamente en este orden, estas tool calls
(el orden exacto puede variar un poco según cómo narre el modelo, pero todas
deberían aparecer):

```text
ficha_leer
combate_iniciar
combate_anadir_enemigo
combate_anadir_enemigo
combate_tirar_iniciativa
combate_turno_actual
combate_atacar_enemigo
combate_registrar_accion_turno
combate_proponer_reaccion
combate_resolver_reaccion
combate_atacar_personaje
combate_avanzar_turno
combate_terminar
narrativa_registrar
sesion_cerrar
```

No pasa nada si `combate_atacar_personaje` no aparece (solo se llama si
confirmas la reacción Y luego pides aplicarla); el resto debería aparecer
siempre que sigas los prompts del paso 4.

---

## 6. Qué verificar en disco

Todo vive bajo `storage/` (en `.gitignore`), relativo a la raíz del repo:

```text
storage/campañas/<campaña_id>/fichas/<personaje_id>.json
storage/campañas/<campaña_id>/eventos.jsonl
storage/campañas/<campaña_id>/combates/<combate_id>.json
storage/campañas/<campaña_id>/combates/activo.json
storage/campañas/<campaña_id>/narrativa/entradas.jsonl
storage/sesiones/
```

> Nota: el subdirectorio es `campañas` (con ñ), no `campanas`.

Eventos a buscar en `eventos.jsonl` (uno por línea JSON, campo `"tipo"`):

```text
combate_iniciado
enemigo_añadido
iniciativa_tirada
ataque_enemigo_resuelto
ataque_personaje_resuelto      (solo si se confirma y se aplica la reacción)
accion_turno_registrada
reaccion_propuesta
reaccion_resuelta
turno_avanzado
combate_terminado
```

Comandos rápidos:

```bash
cat storage/campañas/campana_demo/eventos.jsonl | python -m json.tool 2>/dev/null
cat storage/campañas/campana_demo/eventos.jsonl | grep -o '"tipo": *"[^"]*"'
ls storage/campañas/campana_demo/combates/
python -c "from dm_agent.estado.gestor import GestorEstado; \
print(GestorEstado('storage').cargar_ficha('campana_demo','pj_tyr').hp_actual)"
```

---

## 7. Criterios de aceptación

La prueba se considera válida si, contra un endpoint real:

1. El agente no inventa cambios mecánicos sin tool (con `--debug` se ve la
   tool call antes de cualquier cambio de HP/iniciativa/daño).
2. Los HP de los enemigos cambian **solo** mediante `combate_atacar_enemigo`
   o `combate_dano_enemigo`.
3. Los HP del PJ cambian **solo** mediante `combate_atacar_personaje` o
   `hp_xp_aplicar_dano`.
4. La iniciativa se guarda (`combate_tirar_iniciativa`, visible en
   `<combate_id>.json` y en el evento `iniciativa_tirada`).
5. El turno actual se puede consultar (`combate_turno_actual`) sin error.
6. El turno **no** avanza automáticamente al atacar (`indice_turno_actual` no
   cambia salvo que se llame explícitamente a `combate_avanzar_turno`).
7. Las reacciones se proponen (`combate_proponer_reaccion`, estado
   `pendiente`) pero no se aplican sin confirmación.
8. Confirmar una reacción (`combate_resolver_reaccion`, `decision="confirmar"`)
   **no** tira dados ni hace daño por sí mismo: el HP del objetivo no cambia
   en ese paso.
9. Para aplicar de verdad una reacción confirmada hace falta una llamada
   explícita aparte a `combate_atacar_personaje`/`combate_atacar_enemigo`.
10. Los eventos del paso 6 aparecen en `eventos.jsonl`.
11. La memoria narrativa se puede registrar (`narrativa_registrar`) sobre el
    desenlace del combate.
12. `/cerrar` genera resumen (`tipo = resumen`) y preparación de la próxima
    sesión (`tipo = siguiente_sesion`).
13. Al continuar (`dm-agent --continuar`), el agente recuerda el resumen y el
    estado de la campaña (memoria narrativa inyectada como `system` antes del
    mensaje de usuario).
14. **El agente no debe escribir bloques JSON simulando llamadas de
    herramientas** (texto tipo `[{"name": "...", "arguments": {...}}]`); si
    necesita una tool, debe llamarla de verdad (F6.1, ver sección 8 más abajo,
    "Si el modelo escribe JSON de tools en vez de llamar tools"). Algunos
    modelos pueden simular tools no solo en JSON, sino también con etiquetas
    tipo `<call:name="...">`. Eso tampoco ejecuta herramientas reales. Una
    tool real siempre aparece en debug como `[debug] tool ...` (F6.1.1).
15. **El agente no ofrece siempre las mismas ~45 tools.** Para mejorar
    tool-calling en modelos locales, `dm-agent` reduce el conjunto de tools
    expuestas según la intención del turno (F6.2): un mensaje de ataque solo
    expone `combate_estado`/`combate_turno_actual`/`combate_atacar_enemigo`/
    `combate_atacar_personaje`/`combate_registrar_accion_turno`, no las 14
    tools de combate ni las de ficha/inventario/memoria. En `--debug`, cada
    turno imprime `[debug] tools expuestas: ...` con la lista real.
16. **El agente no repite una tool call idéntica en el mismo turno** (F6.3):
    si el modelo intenta ejecutar la misma tool con los mismos argumentos
    dos veces dentro de un único turno (p. ej. dos `combate_proponer_reaccion`
    para el mismo enemigo), la segunda se ignora sin volver a llamar la tool
    real; en `--debug` se ve `[debug] tool duplicada ignorada: ...`. Llamadas
    con argumentos distintos, o la misma llamada en un turno posterior, se
    ejecutan con normalidad.
17. **El agente no deja un turno completamente vacío.** Si el modelo termina
    el turno sin texto útil y sin ninguna tool call (F6.3), `dm-agent`
    devuelve un mensaje seguro pidiendo reformular, en vez de un turno sin
    respuesta visible; en `--debug` se ve
    `[debug] respuesta vacía del modelo sin tool calls`.
18. **Si el usuario pide explícitamente una tool por su nombre** (p. ej.
    "usa `combate_resolver_reaccion`...") **y el modelo no la llama de
    verdad**, `dm-agent` reintenta una vez con un mensaje corrector (F6.3); si
    tras el reintento sigue sin llamarla, responde que no se pudo ejecutar
    esa herramienta, sin afirmar que sí se hizo.
19. **El modelo ve un bloque "CONTEXTO OPERATIVO ACTUAL" con los IDs reales**
    (F6.5, ver sección 11 más abajo) y no debería usar placeholders como
    `campaña_actual`/`combate_actual`/`personaje_actual`/"Tyr" cuando el ID
    real es `tyr`.
20. **`combate_avanzar_turno` salta enemigos derrotados** (F6.5): si el
    siguiente en el orden de iniciativa es un enemigo con `estado ==
    "derrotado"` o `hp_actual <= 0`, no se queda ahí — avanza hasta el
    siguiente participante activo (nunca salta al personaje). Si ya no
    queda ningún enemigo activo, el resultado trae
    `todos_los_enemigos_derrotados: true` (solo señal, no cierra el combate
    solo).
21. Hay comandos cómodos sin LLM para consultar combate/turno/reacciones/
    ficha/estado activos sin escribir JSON: `/combate`, `/turno`,
    `/reacciones`, `/ficha`, `/estado` (F6.5, ver sección 11).

---

## 8. Resolución de problemas

- **Si el modelo escribe JSON de tools en vez de llamar tools** (responde con
  un bloque de texto tipo `[{"name": "ficha_leer", "arguments": {...}}]` en
  vez de hacer una llamada real): esto es un **fallo de disciplina de
  tool-use**. No significa que la tool haya corrido. En `--debug`, una tool
  real **siempre** aparece como `[debug] tool <nombre>(<args>) -> ok=...`; si
  solo ves narración/JSON en el texto de la respuesta y no esa línea, ninguna
  tool se ejecutó. Desde F6.1, el agente detecta este patrón
  (`_contiene_tool_call_simulada`) y:
  - en `--debug`, imprime
    `[debug] posible tool call simulada en texto; no se ha ejecutado ninguna herramienta`;
  - reintenta automáticamente **una sola vez** por turno con un mensaje
    correctivo ("Has escrito una llamada a herramienta como texto...").
  Si tras el reintento el modelo **sigue** escribiendo JSON de tools, no es
  un bug de `dm-agent`: es el modelo ignorando la instrucción del system
  prompt. Prueba con un modelo con mejor seguimiento de instrucciones/tool-
  calling (ver `docs/MODELOS_LOCALES.md`), o pide explícitamente "llama a la
  tool real, no escribas el JSON".
- **Si el modelo escribe XML/pseudo-calls en vez de llamar tools** (responde
  con algo tipo `<call:name="ficha_leer"><call:param="...">...</call:>`, o
  con etiquetas `<tool_call>`/`<tool>`): es el mismo fallo de disciplina de
  tool-use que el caso anterior, solo que en otro formato. Algunos modelos
  pueden simular tools no solo en JSON, sino también con etiquetas tipo
  `<call:name="...">`. Eso tampoco ejecuta herramientas reales. Una tool real
  siempre aparece en debug como `[debug] tool ...`. Desde F6.1.1, el detector
  (`_contiene_tool_call_simulada`) también reconoce este patrón y aplica la
  misma política: aviso en `--debug` + reintento automático una sola vez por
  turno con un mensaje correctivo que nombra ambos formatos prohibidos.
- **Si un modelo simula tool calls** (JSON o XML/pseudo-call, ver los dos
  casos anteriores), **mira en `--debug` qué tools estaban expuestas** con
  la línea `[debug] tools expuestas: ...` (F6.2). Si esa lista tiene muchas
  tools (p. ej. las 14 de combate completas en vez de las 5 relevantes para
  un ataque), es probable que el modelo se esté "ahogando" en schemas: el
  filtrado contextual de F6.2 debería haber reducido la lista; si no lo
  hizo para un mensaje claro, puede faltar una palabra clave en
  `src/dm_agent/nucleo/seleccion_tools.py` para esa categoría — no es un bug
  de seguridad (el detector de F6.1/F6.1.1 sigue protegiendo igual), es una
  oportunidad de ajustar las palabras clave. Algunos modelos o chat
  templates pueden emitir pseudo tool calls tipo `<tool_call>` incluso con
  pocas tools expuestas: eso indica un desajuste entre modelo/chat
  template/parser del servidor (no algo que `dm-agent` pueda corregir desde
  el cliente). `dm-agent` nunca ejecuta esos textos por seguridad — ver F6.1/
  F6.1.1 más arriba.
- **Si el modelo repite una misma tool call en un turno** (mismo nombre y
  mismos argumentos, p. ej. dos `combate_proponer_reaccion` para el mismo
  enemigo): `dm-agent` ignora duplicados exactos (F6.3) — la segunda llamada
  no se ejecuta de verdad, se le devuelve al modelo un resultado sintético
  indicando que ya se ejecutó en este turno, y en `--debug` aparece
  `[debug] tool duplicada ignorada: ...`. No es un bug si ves la tool real
  solo una vez en el log aunque el modelo "la pidiera" dos veces.
- **Si el modelo devuelve una respuesta vacía sin tool calls** (sin texto y
  sin ninguna llamada real): `dm-agent` lo muestra como error seguro (F6.3,
  `[debug] respuesta vacía del modelo sin tool calls`) en vez de devolver un
  turno en blanco. Pide reformular la instrucción de forma más directa.
- **Si el usuario pide explícitamente una tool y el modelo no la llama**
  (p. ej. "usa `combate_resolver_reaccion` para confirmar..." y el modelo
  responde con texto o nada, sin tool call real): `dm-agent` reintenta una
  vez (F6.3, `[debug] tool explícita mencionada pero no ejecutada: ...`); si
  tras el reintento sigue sin llamarla, responde
  "No se ha podido ejecutar la herramienta solicitada: ..." — nunca afirma
  que se ejecutó si no hay una línea `[debug] tool <nombre>(...) -> ok=...`
  real respaldándolo. Si esto pasa repetidamente con la misma tool/modelo,
  usa el comando manual `/tool` (F6.4, ver sección 10 más abajo) para
  ejecutarla tú directamente sin depender del LLM.
- **El modelo no llama tools** (solo narra): falta
  `--enable-auto-tool-choice`/`--tool-call-parser` en el servidor, o el
  modelo es demasiado pequeño para tool-calling fiable. Usa un modelo más
  grande (ver `docs/MODELOS_LOCALES.md`) o revisa el arranque del servidor.
- **El modelo inventa daño o HP** (dice "Tyr pierde 5 PV" sin que aparezca
  una tool call): el system prompt ya pide no inventar mecánica; si persiste,
  reformula el prompt insistiendo en "usa la tool correspondiente" o cambia
  de modelo. Verifica con `--debug` que de verdad no hubo tool call antes de
  reportarlo como bug.
- **El modelo avanza turno sin tool**: si narra "ahora es el turno de la
  rata" sin llamar a `combate_avanzar_turno`, el estado mecánico
  (`indice_turno_actual`) no cambió de verdad — es solo narración. Pídele
  explícitamente que "avance el turno" o llama tú a la tool si tienes acceso
  directo. No es un bug: F5.5 decidió que avanzar turno sea siempre una
  llamada explícita, nunca automática.
- **El modelo aplica la reacción automáticamente** (llama a
  `combate_atacar_personaje` justo después de confirmar, sin que tú lo
  pidieras): repasa el system prompt/instrucciones — el diseño es "propone,
  confirmas, y si quieres aplicarla pides explícitamente el ataque". Si el
  modelo encadena confirmar→aplicar sin pedir tu confirmación explícita para
  el segundo paso, es un problema de instrucción del modelo, no de las
  tools (las tools en sí nunca encadenan esto).
- **Error de campaña/ficha inexistente**: revisa que `campaña_activa` en
  `config/proyecto.json` coincide con la campaña donde guardaste la ficha
  (paso 2), y que no falta `pj_tyr.json` bajo
  `storage/campañas/<campaña_id>/fichas/`.
- **Endpoint LLM no responde**: `curl http://localhost:8000/v1/models` y
  `python scripts/check_perfil.py` deben pasar antes de tocar el REPL.
- **Contexto demasiado largo**: si la sesión lleva muchos turnos, considera
  `/cerrar` y `--continuar` con una sesión nueva, o sube `max_tokens` del
  perfil en `config/perfiles.json` si el modelo lo soporta.
- **JSON/tool call inválido** (el modelo manda argumentos mal formados): la
  tool devuelve `ResultadoHerramienta(ok=False, errores=[...])` sin
  traceback; el agente debería poder reintentar. Si se cuelga, revisa el log
  de `--debug` para ver qué argumentos mandó el modelo.

---

## 9. Resultado esperado de una sesión buena

El DM narra con fluidez, pero cuando hay mecánica usa tools: iniciar combate,
añadir enemigos, tirar iniciativa, atacar, registrar acción de turno,
proponer una reacción. El usuario decide qué acciones toma Tyr y si confirma
o rechaza las reacciones propuestas. El combate avanza por turnos explícitos,
no automáticos. Las reacciones se proponen y esperan confirmación; confirmar
no es lo mismo que aplicar. Al terminar el combate, queda una entrada
narrativa del desenlace. Al cerrar la sesión, queda un resumen y un punto de
arranque para la próxima; al continuar, el agente recuerda ambos.

---

## 10. Comando manual `/tool` (F6.4)

`/tool <nombre_tool_api> <json_argumentos>` ejecuta una tool real
**directamente desde el REPL, sin pasar por el LLM**. Sirve para depuración
y recuperación manual cuando un modelo local no emite una tool call real
aunque la tool esté disponible y el usuario la haya pedido explícitamente
(F6.3 lo detecta y reintenta una vez, pero si el modelo sigue sin llamarla,
`/tool` permite seguir jugando sin esperar a que el modelo coopere).

```text
> /tool combate_listar_reacciones {"campaña_id":"campana_tyr","combate_id":"combate_aa6049b2"}
[tool] combate_listar_reacciones -> ok=True
{
  "combate_id": "combate_aa6049b2",
  "propuestas": [...]
}

> /tool combate_resolver_reaccion {"campaña_id":"campana_tyr","combate_id":"combate_aa6049b2","propuesta_id":"reaccion_f8b95457","decision":"confirmar","motivo":"ataque de oportunidad aceptado"}
[tool] combate_resolver_reaccion -> ok=True
{
  "propuesta_id": "reaccion_f8b95457",
  "estado": "confirmada"
}

> /tool ficha_leer {"campaña_id":"campana_tyr","personaje_id":"tyr"}
[tool] ficha_leer -> ok=True
{
  "personaje_id": "tyr",
  ...
}
```

Notas:

- Acepta el **nombre API real** de la tool (el mismo que ves en
  `[debug] tools expuestas: ...` o `[debug] tool <nombre>(...)`), no el
  nombre interno con puntos.
- Los argumentos son JSON tras el nombre de la tool, en una sola línea.
- JSON inválido o tool inexistente muestran un error controlado
  (`[tool] error: ...` / `[tool] <nombre> -> error: herramienta
  desconocida`) sin romper el REPL.
- La tool se ejecuta de verdad (`RegistroHerramientas.dispatch_api`): los
  cambios se persisten igual que si los hubiera llamado el LLM.
- La llamada manual **no entra en el historial conversacional** que se
  reinyecta al LLM (no es un turno `user`/`assistant`); sí queda registrada
  como `tool_call`/`tool_result` en la sesión, igual que el rastro de
  auditoría de una tool llamada por el LLM.
- `/tool` solo se ejecuta cuando el usuario lo escribe explícitamente; no
  tiene relación con la detección de pseudo-calls de F6.1/F6.1.1 (que sigue
  sin parsear ni ejecutar nunca el texto que escribe el modelo).

---

## 11. Contexto operativo activo y comandos cómodos (F6.5)

Tras una prueba manual completa de combate, aparecieron tres fricciones más:
el modelo inventaba placeholders (`campaña_actual`, `combate_actual`, "Tyr"
en vez de `tyr`) en lugar de usar los IDs reales aunque ya estaban
disponibles; `/tool` era incómodo para operaciones frecuentes (hay que
escribir el JSON entero a mano); y al avanzar turno o atacar, nada avisaba
de que todos los enemigos ya estaban derrotados. F6.5 corrige las tres sin
añadir mecánicas nuevas de D&D.

### Contexto operativo activo (sin placeholders)

Antes de cada turno, `dm-agent` inyecta un mensaje `system` adicional con
los IDs reales de la campaña/combate/personaje activos, derivados de los
gestores existentes (sin LLM):

```text
CONTEXTO OPERATIVO ACTUAL

- campaña_id activa: campana_tyr
- personaje_id activo: tyr
- combate_id activo: combate_aa6049b2
- estado combate: activo
- ronda: 3
- turno actual: tyr

Usa estos IDs reales en las herramientas.
No uses placeholders como campaña_actual, combate_actual, personaje_actual o Tyr si el ID real es tyr.
```

Si no hay combate activo, el bloque de combate se omite y dice
explícitamente "sin combate activo detectado" — nunca falla ni inventa un
`combate_id`. Este mismo bloque se añade también al reintento corrector de
F6.3 cuando el usuario pide una tool explícita y el modelo no la llama: así
el segundo intento ya tiene los IDs reales delante, no solo el nombre de la
tool.

### Comandos cómodos: `/combate`, `/turno`, `/reacciones`, `/ficha`, `/estado`

Atajos sobre el mismo mecanismo que `/tool` (`dispatch_api` directo, sin
LLM), pero sin tener que escribir `campaña_id`/`combate_id`/`personaje_id` a
mano: resuelven esos IDs solos a partir del combate activo de la campaña.

```text
> /combate
[comando] combate_estado -> ok=True
{ ... }

> /turno
[comando] combate_turno_actual -> ok=True
{ ... }

> /reacciones
[comando] combate_listar_reacciones -> ok=True
{ ... }

> /ficha
[comando] ficha_leer -> ok=True
{ ... }

> /estado
[estado]
Campaña: campana_tyr
Personaje: Tyr (tyr) — HP 1/12, CA 16
Combate: combate_aa6049b2 — terminado
Ronda: 3
Enemigos:
- rata_1: derrotado, 0/5 HP
- rata_2: derrotado, 0/5 HP
Reacciones pendientes: 0
```

Si no hay combate activo, `/combate`, `/turno` y `/reacciones` muestran
`[comando] No hay combate activo detectado.` en vez de fallar; `/ficha` sin
personaje activo conocido muestra
`[comando] No se conoce personaje activo. Usa /tool ficha_leer {...}`.
`/estado` nunca rompe: si falta combate o ficha, lo dice en el propio
resumen. Ninguno de estos comandos llama al LLM.

### Avanzar turno salta enemigos derrotados

`combate_avanzar_turno` ya no deja como turno activo a un enemigo derrotado
(`estado == "derrotado"` o `hp_actual <= 0`): lo salta automáticamente y
sigue hasta el siguiente participante activo. Los personajes nunca se
saltan por esta vía. El resultado incluye `enemigos_derrotados_saltados`
(lista de ids saltados en esa llamada) y `todos_los_enemigos_derrotados`/
`deberia_terminar_combate` (`true` si ya no queda ningún enemigo activo) —
**solo señaliza, no termina el combate solo**: sigue haciendo falta un
`combate_terminar` explícito (D-COMBATE-04).

### Señal `todos_los_enemigos_derrotados` al atacar

`combate_atacar_enemigo` añade los mismos dos campos
(`todos_los_enemigos_derrotados`, `deberia_terminar_combate`) cuando el
ataque deja a todos los enemigos del combate derrotados. Sigue sin terminar
el combate automáticamente: es una señal para que el DM (humano o LLM) sepa
que toca llamar a `combate_terminar` si quiere cerrar la escena.

### Recomendación: registrar la acción narrativa después de ver el resultado real

Durante la prueba apareció una rata que hizo un crítico, pero la acción
narrativa se registró como "falló" antes de comprobar `impacta`/`critico`
en el resultado real de la tool — hubo que corregirlo a mano después.
Recomendación para evitarlo:

- **Registra la acción (`combate_registrar_accion_turno`) después de ver el
  resultado real del ataque**, no antes ni en paralelo: lee `impacta`,
  `critico`, `pifia` y `dano` de la respuesta de `combate_atacar_enemigo`/
  `combate_atacar_personaje` antes de describir qué pasó.
- **No escribas "falló" (ni "impactó", ni "crítico") antes de comprobar
  `impacta`** en el resultado: la narración debe seguir a la mecánica, no
  adelantarse a ella.
- Si aun así se registra una acción incorrecta, **no la edites**: registra
  una acción nueva de tipo `correccion` que la corrija explícitamente (no
  hay edición de acciones todavía; ver `docs/BACKLOG.md`).

---

## Límites de esta versión

F5.6 es **validación manual**, no mecánica nueva: no añade IA enemiga,
selector automático de acciones, motor completo de economía de acciones,
ataques de oportunidad o flanqueo automáticos, condiciones completas,
hechizos, grid/casillas, XP automática, RAG, memoria vectorial ni streaming.
Si algo de eso falla en esta prueba, es esperado — no está implementado
todavía (ver `docs/estado/combate.md` y `docs/BACKLOG.md`).
