# Resúmenes narrativos (F4.2)

> Módulos: `dm_agent.memoria.resumen` (`ResumidorNarrativo`) ·
> `dm_agent.herramientas.resumen` (tools) · `prompts/resumen_narrativo.md`.

## Propósito

La bitácora narrativa (F4.1) registra hechos sueltos. F4.2 los **consolida** con
el LLM en un resumen útil para continuidad entre sesiones, y lo persiste como una
`EntradaNarrativa(tipo="resumen")` más en la misma bitácora.

## Entrada narrativa vs resumen

Un **resumen** es una `EntradaNarrativa` como cualquier otra, pero:

- `tipo = "resumen"`, `origen = "resumen"`, `importancia = 5`, `tags` incluye `"resumen"`;
- su `contenido` lo genera el LLM a partir de material existente (entradas o un texto);
- se guarda en `entradas.jsonl` + `bitacora.md` (no es un fichero aparte).

## Cómo se genera

`ResumidorNarrativo(cliente_llm, gestor_memoria)`:

- `resumir_texto(campaña_id, texto, sesion_id=None)` — resume un texto de
  escena/sesión que se le pasa.
- `resumir_entradas(campaña_id, limite=20, sesion_id=None)` — resume las últimas
  `limite` entradas de la bitácora (en Markdown).

Ambos: construyen `messages = [system(prompt fijo), user(material)]`, llaman a
`ClienteLLM.chat(..., stream=False)`, validan que el resumen no esté vacío y lo
persisten como entrada `resumen`.

## Prompt (`prompts/resumen_narrativo.md`)

Prompt fijo y versionado. Instruye al modelo a: resumir **solo** lo presente, no
inventar, no spoilers, no resolver decisiones pendientes, no tocar reglas/ficha,
responder en español y con una estructura recomendada (Estado actual · Decisiones
· PNJ y lugares · Pistas/objetos · Consecuencias abiertas · Ganchos).

## Errores

- `MaterialVacio` — texto a resumir vacío.
- `SinEntradasParaResumir` — no hay entradas que resumir.
- `ResumenVacio` — el modelo devolvió contenido vacío.

Las tools los traducen a `ResultadoHerramienta(ok=False, errores=[...])`; los
errores del cliente (`ErrorLLM`) también se capturan sin traceback.

## Límites (F4.2) y relación con F4.3

- **No hay inyección automática** de memoria/resúmenes al contexto del agente:
  eso es **F4.3**. Aquí los resúmenes solo se generan y guardan bajo demanda
  (tool o llamada directa).
- No hay preparación automática de la siguiente sesión, RAG, memoria vectorial ni
  PNJ/lugares estructurados.
- El resumen es texto Markdown libre (sin JSON estricto) en F4.2.
- Coherente con D17: favorece continuidad narrativa, no registro táctico.
