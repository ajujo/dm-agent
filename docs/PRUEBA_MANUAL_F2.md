# Prueba manual de F2.2 (REPL + agent loop + dados)

> Mini-fase **F2.3**: validación manual de que el chat CLI funciona de verdad
> contra un endpoint LLM local. No añade funcionalidad nueva.

Esta guía verifica el camino completo: arranque → escena narrativa → tirada real
con `dados_tirar` → salir → continuar → sesión persistida en JSONL.

Requisitos previos: entorno `conda` `rpg` y `pip install -e .[dev]` ya hecho.

---

## 1. Levantar un endpoint OpenAI-compatible local

El perfil por defecto (`rapido`) apunta al endpoint `local_rtx5090`
(`config/modelos.json`): `base_url = http://localhost:8000/v1`.

Levanta ahí un servidor OpenAI-compatible. Ejemplos:

**vLLM** (recomendado para tool-calling):

```bash
conda activate rpg
vllm serve Qwen/Qwen3.6-27B \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

> El flag de tool-calling (`--enable-auto-tool-choice` + un `--tool-call-parser`
> adecuado al modelo) es **imprescindible** para que `dados_tirar` se dispare.
> El parser correcto depende del modelo (para familia Qwen suele ser `hermes`).

**LM Studio / llama.cpp / MLX**: arranca su servidor en modo OpenAI-compatible y
anota el puerto y la `base_url` reales.

Comprueba que responde:

```bash
curl http://localhost:8000/v1/models
```

---

## 2. Ajustar `config/perfiles.json` si el modelo no coincide

El `modelo` del perfil debe coincidir **exactamente** con el `id` que expone
`/v1/models`. Si no coincide, edita `config/perfiles.json`:

```json
{
  "perfiles": {
    "rapido": {
      "endpoint": "local_rtx5090",
      "modelo": "Qwen/Qwen3.6-27B",   // <-- pon aquí el id real de /v1/models
      "max_tokens": 800,
      "temperatura": 0.7,
      "top_p": 0.9
    }
  }
}
```

Si tu endpoint no es `localhost:8000`, edita la `base_url` del endpoint
correspondiente en `config/modelos.json` (o usa otro perfil con `--perfil`).

Valida la coherencia de la config sin tocar la red:

```bash
python scripts/check_perfil.py
```

---

## 3. Ejecutar el REPL

```bash
conda activate rpg
dm-agent --perfil rapido
```

Verás algo como:

```text
Sesión nueva: sesion-AAAAMMDD-HHMMSS
dm-agent — escribe /ayuda para ver los comandos. /salir para terminar.
>
```

Comandos útiles dentro del REPL: `/ayuda`, `/continuar`, `/nueva`, `/guardar`,
`/debug`, `/salir`. Activa `/debug` (o arranca con `--debug`) para ver las tool
calls que ejecuta el agente.

---

## 4. Probar una escena narrativa

```text
> Entro en una taberna ruidosa al anochecer y busco al tabernero.
```

Debe responder con una descripción breve en español, en tono de Director de Juego.

---

## 5. Forzar una tirada de percepción

```text
> Quiero fijarme si alguien me observa. Hago una tirada de Percepción con +3.
```

Comportamiento esperado:

1. El modelo llama a la herramienta `dados_tirar` (verás la traza si `--debug`).
2. El agente ejecuta la tirada **de verdad** (no la inventa el LLM) y reinyecta el
   resultado al modelo.
3. El modelo integra el número en la narración.

En la sesión quedarán registrados un `tool_call` y un `tool_result`
(ver paso 7).

---

## 6. Salir

```text
> /salir
```

---

## 7. Continuar y comprobar el JSONL

Retomar la última sesión:

```bash
dm-agent --continuar
```

Debe imprimir `Continuando sesión: <id> (<n> registros)`.

Comprobar el fichero de sesión persistido:

```bash
ls -la storage/sesiones/
cat storage/sesiones/<id>.jsonl
```

Cada línea es un registro JSON. Tras los pasos anteriores deberías ver, al menos:

```json
{"tipo":"user","content":"...","timestamp":"..."}
{"tipo":"assistant","content":"...","timestamp":"..."}
{"tipo":"tool_call","nombre_api":"dados_tirar","argumentos":{"expresion":"1d20+3"},"timestamp":"..."}
{"tipo":"tool_result","nombre_api":"dados_tirar","ok":true,"resultado":{...},"timestamp":"..."}
```

> `storage/` está en `.gitignore`: las sesiones son datos locales, no se versionan.

---

## 8. Qué hacer si el modelo NO llama a `dados_tirar`

Si el modelo "inventa" el resultado en vez de tirar:

1. **Verifica el tool-calling del servidor.** Sin `--enable-auto-tool-choice` (y el
   `--tool-call-parser` correcto) el endpoint ignora las `tools`. Reinícialo.
2. **Prueba un modelo con buen soporte de herramientas.** Modelos pequeños
   (< 7B) fallan a menudo en tool-calling. Usa Qwen3.6-27B o el 35B-A3B (ver
   `docs/MODELOS_LOCALES.md`).
3. **Sé explícito en la petición** ("haz una tirada de d20+3"); el system prompt ya
   pide usar la herramienta para los dados.
4. **Confirma que la tool llega al modelo.** Arranca con `--debug`: si nunca aparece
   una tool call, el problema está en el servidor/modelo, no en `dm-agent`.
5. **Descarta config.** `python scripts/check_perfil.py` debe pasar; el `modelo`
   debe coincidir con `/v1/models`.

Si el endpoint no está levantado, un turno mostrará un mensaje limpio
`[error del modelo/endpoint] …` (no un traceback): es lo esperado.

---

## Límites de esta versión

Sigue siendo **chat con dados**, no una campaña: no hay ficha, combate,
inventario, estado mecánico, RAG ni memoria avanzada. El historial entre turnos
se reconstruye solo desde los mensajes de usuario/asistente. Streaming no está
implementado (`stream=False`).
