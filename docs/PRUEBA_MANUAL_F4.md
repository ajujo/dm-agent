# Prueba manual de F4 (campaña persistente básica)

> Mini-fase **F4.5**: validación manual, contra un endpoint LLM real, de que el
> proyecto funciona como **campaña persistente básica**. No añade funcionalidad
> nueva; complementa al test integrado `tests/test_campaña_integrada_f4.py`.

Esta guía verifica el bucle completo de continuidad:
arranque → ficha → escena narrativa → mutaciones mecánicas (inventario + HP/XP) →
memoria narrativa inyectada → `/cerrar` (resumen + preparación de la próxima) →
`/salir` → `dm-agent --continuar` recordando lo anterior.

Requisitos previos: entorno `conda` `rpg` y `pip install -e .[dev]` ya hecho.
Si vienes de la prueba manual de F2 (`docs/PRUEBA_MANUAL_F2.md`), los pasos 1–2
de levantado de endpoint son los mismos.

---

## 1. Levantar un endpoint OpenAI-compatible local

El perfil por defecto (`rapido`) apunta al endpoint `local_rtx5090`
(`config/modelos.json`): `base_url = http://localhost:8000/v1`.

**vLLM** (recomendado para tool-calling):

```bash
conda activate rpg
vllm serve Qwen/Qwen3.6-27B \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

> El tool-calling (`--enable-auto-tool-choice` + el `--tool-call-parser`
> adecuado al modelo) es **imprescindible**: sin él, las tools mecánicas
> (`inventario_anadir`, `hp_xp_aplicar_dano`, `narrativa_registrar`…) nunca se
> disparan y el modelo solo charla. Para familia Qwen el parser suele ser
> `hermes`. Modelos < 7B fallan a menudo en tool-calling; usa Qwen3.6-27B o el
> 35B-A3B (ver `docs/MODELOS_LOCALES.md`).

Comprueba que responde y valida la config sin tocar la red:

```bash
curl http://localhost:8000/v1/models
python scripts/check_perfil.py
```

Si el `id` del modelo no coincide con el del perfil, ajústalo en
`config/perfiles.json` (ver `docs/PRUEBA_MANUAL_F2.md`, paso 2).

---

## 2. Confirmar la campaña activa

El REPL inyecta memoria narrativa de la campaña indicada en `config/proyecto.json`:

```json
{
  "campaña_activa": "campana_demo",
  "memoria": {
    "inyectar_narrativa": true,
    "limite_entradas_contexto": 8,
    "incluir_resumenes": true
  }
}
```

Todo lo que sigue usa la campaña `campana_demo`. El estado (fichas, eventos,
bitácora narrativa, sesiones) vive bajo `storage/`, que está en `.gitignore`.

---

## 3. Crear una ficha de personaje (con las APIs del proyecto)

No edites el JSON a mano. Crea la ficha con las APIs del proyecto. Desde la raíz
del repo y con el entorno activo:

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

La validación de pydantic (`extra="forbid"`, rangos de atributos, HP coherente)
rechaza fichas mal formadas: si imprime un error de validación, corrige los
campos antes de seguir.

---

## 4. Ejecutar el REPL

```bash
conda activate rpg
dm-agent --perfil rapido --debug
```

`--debug` muestra las tool calls que ejecuta el agente: es la forma de comprobar
que las mutaciones mecánicas son **reales** y no inventadas por el LLM.

Comandos del REPL: `/ayuda`, `/continuar`, `/nueva`, `/guardar`, `/cerrar`,
`/debug`, `/salir`.

---

## 5. Escena narrativa inicial

```text
> Tyr entra en una taberna bajo la lluvia. Describe la escena.
```

Debe responder con una descripción breve en español, en tono de Director de
Juego.

---

## 6. Forzar una entrada de memoria narrativa

Pide explícitamente que registre la escena en la bitácora de campaña:

```text
> Registra esta escena en la memoria de la campaña como una entrada de tipo escena.
```

Comportamiento esperado (con `--debug`): el modelo llama a `narrativa_registrar`.
Compruébalo en disco:

```bash
ls storage/campanas/campana_demo/   # o la ruta de campaña que use tu instalación
cat storage/**/narrativa*.jsonl 2>/dev/null | tail
```

> La ruta exacta la define `GestorMemoriaNarrativa`; lo importante es que aparezca
> una línea JSON nueva con `"tipo":"escena"` y tu texto.

---

## 7. Forzar una mutación de inventario

```text
> Tyr encuentra una llave oxidada en el suelo y la recoge. Añádela a su inventario.
```

Esperado: el modelo llama a `inventario_anadir` (campaña `campana_demo`,
personaje `pj_tyr`, objeto con `id`/`nombre`/`cantidad`). Verifica:

```bash
python -c "from dm_agent.estado.gestor import GestorEstado; \
print([o.id for o in GestorEstado('storage').cargar_ficha('campana_demo','pj_tyr').inventario])"
```

Debe listar el objeto recién añadido.

---

## 8. Forzar una mutación de HP/XP

```text
> Tyr pisa una trampa sencilla y recibe 3 puntos de daño.
```

Esperado: el modelo llama a `hp_xp_aplicar_dano`. La verdad mecánica la decide el
motor, no el LLM. Verifica el HP resultante (12 − 3 = 9) y que quedó un evento
auditable:

```bash
python -c "from dm_agent.estado.gestor import GestorEstado; \
print('hp_actual =', GestorEstado('storage').cargar_ficha('campana_demo','pj_tyr').hp_actual)"
cat storage/**/eventos*.jsonl 2>/dev/null | tail
```

Debes ver `hp_actual = 9` y un evento `daño_aplicado` (y, del paso 7, uno
`objeto_añadido`).

---

## 9. Cerrar la sesión

```text
> /cerrar
```

Esperado: el agente envía la transcripción de la sesión al LLM y produce **dos**
entradas narrativas para `campana_demo`:

- un **resumen de cierre** (`tipo = resumen`);
- una **preparación de la próxima sesión** (`tipo = siguiente_sesion`).

El REPL imprime ambas:

```text
Sesión <id> cerrada.

== Resumen de cierre ==
...

== Punto de arranque de la próxima ==
...
```

> Si el modelo no devuelve las cabeceras `# Resumen de cierre` /
> `# Preparación de próxima sesión`, el cierre degrada con gracia (verás un aviso,
> no un traceback). Reintenta o usa un modelo con mejor seguimiento de formato.

---

## 10. Salir y continuar recordando

```text
> /salir
```

```bash
dm-agent --continuar
```

Debe imprimir `Continuando sesión: <id> (<n> registros)`. Ahora haz una pregunta
de continuidad:

```text
> Continúa desde donde lo dejamos. ¿Qué recuerda Tyr de la sesión anterior?
```

Esperado: la respuesta menciona la llave oxidada y/o el punto de arranque
preparado en el paso 9. Esa información llega al modelo como un **segundo mensaje
`system`** ("# Memoria narrativa de campaña"), inyectado **antes** del mensaje de
usuario, sin sustituir al system prompt base. Con `--debug` puedes confirmar que
el bloque de memoria viaja en la petición.

---

## Criterios de aceptación

La prueba es correcta si, sin editar JSON a mano y contra un endpoint real:

1. La ficha `pj_tyr` se crea y valida con las APIs del proyecto.
2. Una escena queda registrada en la bitácora narrativa (`tipo = escena`).
3. `inventario_anadir` añade de verdad la llave oxidada a la ficha.
4. `hp_xp_aplicar_dano` deja `hp_actual = 9` y un evento `daño_aplicado`
   auditable (la mecánica la decide el motor, no el LLM).
5. `/cerrar` genera resumen (`resumen`) + preparación (`siguiente_sesion`) para la
   misma campaña.
6. Tras `--continuar`, el agente recuerda lo anterior porque la memoria narrativa
   se inyecta como `system` antes del mensaje de usuario.

---

## Resolución de problemas

- **El modelo no llama a las tools** (charla en vez de mutar estado): falta
  `--enable-auto-tool-choice` o el `--tool-call-parser` correcto, o el modelo es
  demasiado pequeño. Reinicia el servidor; usa Qwen3.6-27B / 35B-A3B. Con
  `--debug`, si nunca aparece una tool call el problema está en el servidor/modelo,
  no en `dm-agent`.
- **`/cerrar` dice que no hay contenido**: la sesión activa aún no tiene turnos;
  juega al menos un turno antes de cerrar.
- **No recuerda al continuar**: confirma `inyectar_narrativa: true` y que
  `campaña_activa` coincide con la campaña donde guardaste la ficha y la bitácora
  (`campana_demo`). Revisa que el paso 9 dejó entradas `resumen` /
  `siguiente_sesion` en la bitácora de esa campaña.
- **Error de validación al crear la ficha**: pydantic rechaza campos extra o
  fuera de rango; ajusta el snippet del paso 3.
- **`[error del modelo/endpoint] …`**: el endpoint no está levantado o el `modelo`
  del perfil no coincide con `/v1/models`. `python scripts/check_perfil.py` debe
  pasar.

---

## Límites de esta versión

Es una **campaña persistente básica**: ficha + estado mecánico auditable +
memoria narrativa con continuidad entre sesiones. **Aún no** hay combate, RAG,
memoria vectorial, entidades estructuradas (PNJ/lugares/pistas), economía, reglas
adaptadas implementadas, streaming ni cierre automático al salir. El `/cerrar`
es manual.
