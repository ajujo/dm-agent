# Arquitectura de `dm-agent`

> "No queremos un chatbot de D&D. Queremos un Hermes-like RPG Agent: un Director de Juego modular, con skills, tools, memoria persistente y verdad mecánica fuera del LLM."

## 1. Principios

1. **Local-first**: todo corre en local; cloud opcional.
2. **El LLM narra, no decide reglas**: ninguna mecánica (HP, tirada, regla) la resuelve el modelo.
3. **Estado crítico auditable**: cada cambio mecánico produce un evento registrado.
4. **Tools deterministas**: el LLM solo modifica estado vía `tool_call` con schema validado.
5. **Memorias separadas por tipo**: mecánica, narrativa, mundo, PNJ, reglas, RAG, etc.
6. **Progressive disclosure**: las skills son instrucción; se cargan bajo demanda.
7. **RAG anti-spoiler**: el contexto del jugador nunca incluye información no descubierta.
8. **Modular y extensible**: nuevas skills y tools sin tocar el núcleo.
9. **Reversible**: el estado se guarda incrementalmente; toda partida es resumible.
10. **Compatible OpenAI**: vLLM, LM Studio, llama.cpp, Open WebUI; ningún acople a un proveedor.

## 2. Diagrama de capas

```
┌─────────────────────────────────────────────────────────────────┐
│  Interfaz (v1: CLI; v2+: TUI, Web, Open WebUI, Voz)             │
├─────────────────────────────────────────────────────────────────┤
│  Núcleo del agente                                              │
│    AgentLoop ── ConstructorContexto ── RouterIntención          │
│        │            │                       │                   │
│        ▼            ▼                       ▼                   │
│    RegistroTools  GestorMemoria        CargadorSkills           │
│        │            │                       │                   │
├────────┼────────────┼───────────────────────┼───────────────────┤
│        ▼            ▼                       ▼                   │
│  TOOLS (deterministas)       SKILLS (procedurales / instrucción)│
│   dados, ficha, combate,     crear_mundo, dirigir_escena,       │
│   reglas, estado, rag        importar_aventura, resumen…        │
├─────────────────────────────────────────────────────────────────┤
│  Motor de reglas (SRD / casero)   │   RAG (aventura + reglas)   │
├───────────────────────────────────┼─────────────────────────────┤
│  Persistencia                     │   Cliente LLM               │
│   estado mecánico (JSON→SQLite)   │   OpenAI-compatible         │
│   memoria narrativa (Markdown)    │   perfiles: rápido / grande │
│   logs auditables (JSONL)         │   / pequeño                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Comparación Hermes → dm-agent

| Hermes Agent | dm-agent |
|---|---|
| `AIAgent.run_conversation` | `AgenteDM.dirigir_turno` |
| Toolsets generales (terminal, browser…) | Toolsets RPG (dados, ficha, combate, reglas, mundo, rag). |
| Skills generales (notion, comfyui…) | Skills de DM (dirigir-escena, crear-mundo, importar-aventura, resumir-sesión, gestionar-combate…). |
| `MEMORY.md` + `state.db` | Varias memorias tipadas: `mecanica/`, `narrativa/`, `mundo/`, `pnj/`, `sesiones/`, `reglas/`, `aventura/`, índice vectorial. |
| Personalidades (`helpful`, `creative`…) | Perfiles de DM (`storyteller`, `tactical`, `sandbox`, `grimdark`, `comedia`). |
| Context files | Lore activo, ficha activa, escena activa, estado mecánico. |
| Planes de tarea | Plan de sesión, plan de aventura, milestones de campaña. |
| Subagentes generales | Subagentes especializados (Narrador, ÁrbitroReglas, DiseñadorMundo, GestorCombate, GuardiánContinuidad) — fase posterior. |
| MCP servers | Diferido a v2+. |

## 4. Estructura del repositorio

```
dm-agent/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── .gitignore
├── Makefile
├── config/
│   ├── proyecto.json
│   ├── modelos.json          # endpoints OpenAI-compatible
│   ├── perfiles.json         # rápido / grande / pequeño / etc.
│   └── tonos/                # narrativas (migrados desde dnd5e)
├── src/dm_agent/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── nucleo/               # agent loop, contexto, eventos, logger
│   ├── herramientas/         # tools deterministas
│   ├── skills/               # loader, router, decorators
│   ├── memoria/              # tipos + almacén
│   ├── estado/               # estado mecánico de partida
│   ├── reglas/               # motor SRD + reglas caseras
│   ├── rag/                  # ingesta + índice + anti-spoiler
│   ├── narrativa/            # director, pacing, fases
│   ├── llm/                  # cliente OpenAI-compatible
│   └── esquemas/             # dataclasses / pydantic
├── skills/                   # skills empacadas (SKILL.md + scripts)
├── compendio/                # contenido permitido/documentado (LICENSE incluido)
├── compendio_privado/        # contenido privado del usuario (gitignored, ver D17)
├── tests/
├── docs/
├── scripts/
└── storage/                  # personajes, campañas, sesiones (datos del usuario, gitignored)
```

### Separación motor / contenido (D17)

Por higiene técnica, el **motor** se mantiene separado del **contenido privado**
(ver [ADR-0017](./decisiones/0017-dnd55-narrativo-solitario.md)):

```text
src/                  -> motor limpio
config/               -> configuración
storage/              -> partidas privadas (gitignored)
compendio/            -> contenido permitido/documentado
compendio_privado/    -> contenido privado del usuario (gitignored)
```

`dm-agent` usa D&D 5.5 como base de resolución, pero lo **adapta** a juego
narrativo en solitario / teatro de la mente mediante reglas caseras persistentes
aprobadas por el usuario (3 capas: regla base → adaptación solitario → preferencias
de campaña). Catálogo de adaptación y flujo: [`REGLAS_ADAPTADAS.md`](./REGLAS_ADAPTADAS.md).

## 5. Núcleo del agente

### `AgenteDM` (`nucleo/agente.py`)
Orquestador por sesión. Mantiene referencias a:
- `GestorContexto`
- `RegistroHerramientas`
- `CargadorSkills`
- `GestorMemoria`
- `EstadoPartida`
- `ClienteLLM`
- `RegistroEventos`

Método principal: `dirigir_turno(entrada_jugador) -> RespuestaDM`.

### Pipeline de turno

```
entrada_jugador
   │
   ▼
1. router_intencion   → ¿skill explícita?, ¿comando?, ¿acción libre?
   │
   ▼
2. constructor_contexto
      ├─ system prompt (perfil DM + tono + reglas básicas)
      ├─ resumen mecánico (estado actual)
      ├─ memoria narrativa relevante (últimos eventos clave)
      ├─ ficha activa (compacta)
      └─ recuperaciones RAG (filtradas anti-spoiler)
   │
   ▼
3. ciclo LLM ↔ tools
      ├─ LLM emite respuesta o tool_calls
      ├─ registro.dispatch(tool_call)  →  Tool.ejecutar → Evento
      ├─ resultados se inyectan
      └─ se repite hasta no haber tool_calls (max_iter)
   │
   ▼
4. post-turno
      ├─ registrar eventos en log
      ├─ persistir cambios de estado
      ├─ actualizar memoria narrativa
      └─ devolver mensaje al jugador (sin secretos)
```

Resultado tipado (`ResultadoTurno`) con discriminador: `NARRACION`, `NECESITA_CLARIFICAR`, `ACCION_RECHAZADA`, `ERROR`.

## 6. Herramientas (tools)

### Contrato

```python
class Herramienta(Protocol):
    nombre: str
    descripcion: str
    schema: dict        # JSON Schema de parámetros
    requiere: list[str] # nombres de recursos (ficha, combate, etc.)
    modifica: list[str] # nombres de áreas de estado que puede tocar

    def disponible(self, ctx) -> tuple[bool, str]: ...
    def ejecutar(self, ctx, **args) -> ResultadoHerramienta: ...
```

Resultado: `ResultadoHerramienta(ok, datos, eventos, errores)`.

### Inventario inicial de tools (v1)

| Toolset | Tools |
|---|---|
| `dados` | `tirar`, `tirar_ventaja`, `tirar_desventaja` |
| `ficha` | `leer_ficha`, `actualizar_ficha`, `validar_ficha` |
| `hp_xp` | `aplicar_daño`, `aplicar_curacion`, `otorgar_xp`, `consultar_estado_vital` |
| `inventario` | `listar_inventario`, `añadir_objeto`, `quitar_objeto`, `equipar`, `mover_oro` |
| `conjuros` | `lanzar_conjuro`, `recuperar_huecos`, `listar_conjuros` |
| `condiciones` | `aplicar_condicion`, `retirar_condicion`, `listar_condiciones` |
| `combate` | `iniciar_combate`, `avanzar_turno`, `aplicar_ataque`, `finalizar_combate` |
| `personaje` | `crear_personaje`, `subir_nivel` |
| `campaña` | `crear_campana`, `leer_estado_campana`, `actualizar_estado_campana` |
| `escena` | `crear_escena`, `actualizar_escena`, `cerrar_escena` |
| `mundo` | `gestionar_pnj`, `gestionar_faccion`, `gestionar_localizacion`, `gestionar_mision` |
| `reglas` | `consultar_regla`, `buscar_compendio` |
| `rag` | `buscar_aventura`, `buscar_mundo`, `buscar_memoria` |
| `sesion` | `registrar_evento`, `generar_resumen`, `guardar_resumen`, `preparar_siguiente` |

Cada tool tiene su SCHEMA y validación; jamás escribe sin pasar por validador.

## 7. Skills

`skills/<slug>/SKILL.md` con frontmatter YAML + cuerpo Markdown.

Frontmatter ampliado para dm-agent:

```yaml
---
name: dirigir-combate
description: "Conducir un encuentro de combate por turnos"
version: 0.1.0
modo: combate                       # exploración | social | combate | viaje | descanso | gestión
requiere_tools: [combate.*, dados.tirar, condiciones.*]
lee: [ficha, estado_combate, compendio.monstruos]
modifica: [estado_combate, ficha.hp, ficha.condiciones, log_eventos]
tono_aplicable: [todos]
nivel_juego: [todos]
---
# Cuándo usar
…
# Cuándo NO usar
…
# Procedimiento
1. …
# Criterios de éxito
…
# Riesgos / fallos
…
# Ejemplos
…
```

### Skills v1

`crear-mundo`, `crear-campana`, `crear-aventura`, `importar-aventura`, `dirigir-aventura`, `dirigir-escena`, `exploracion`, `escena-social`, `dirigir-combate`, `viaje`, `descanso`, `crear-personaje`, `gestionar-ficha`, `subir-nivel`, `gestionar-inventario`, `gestionar-conjuros`, `gestionar-xp`, `consultar-reglas`, `arbitrar-regla-ambigua`, `gestionar-pnj`, `gestionar-faccion`, `gestionar-localizacion`, `gestionar-mision`, `memoria-campana`, `resumir-sesion`, `preparar-siguiente`, `rag-anti-spoiler`, `improvisar-contenido`, `mantener-continuidad`.

### Carga
`CargadorSkills` escanea `skills/**/SKILL.md` al inicio y cachea metadatos. El cuerpo se inyecta solo cuando el `RouterIntencion` decide invocar la skill o el jugador la pide explícitamente.

## 8. Memoria

| Memoria | Backend v1 | Fase con SQLite/vector |
|---|---|---|
| Mecánica (estado partida) | JSON | SQLite (F11+) |
| Narrativa (eventos clave) | Markdown append-only | SQLite + FTS |
| Sesiones (resúmenes) | Markdown | idem |
| PNJ | YAML por archivo | tabla SQLite |
| Facciones | YAML | tabla |
| Localizaciones | YAML | tabla + GIS opcional |
| Misiones | YAML | tabla |
| Mundo (lore) | Markdown | vector (RAG) |
| Aventura (importada) | Markdown + meta JSON | vector + filtros |
| Reglas (SRD/casero) | JSON/MD | vector |
| Jugador (perfil OOC) | YAML | tabla |
| Logs auditables | JSONL append-only | idem |

`GestorMemoria` expone `cargar(tipo, query, ctx)`, `escribir(tipo, payload, motivo)`. Toda escritura pasa por validador del tipo correspondiente.

## 9. Estado mecánico

Esquemas serializados (versionados):

```
storage/
└── campañas/<slug>/
    ├── meta.json                # versión, fecha, semilla
    ├── ficha_<id>.json          # personajes activos
    ├── mundo.yaml               # localización actual + visibles
    ├── estado_partida.json      # tiempo, oro grupal, recursos, condiciones globales
    ├── combate_actual.json      # null si no hay
    ├── narrativa.md             # bitácora narrativa
    ├── eventos.jsonl            # log auditable
    └── memorias/{pnj,faccion,localizacion,mision}/*.yaml
```

Cada modificación produce un `Evento`:

```json
{
  "id": "evt_2026-06-18T20:45:00Z_001",
  "tipo": "daño_aplicado",
  "tool": "hp_xp.aplicar_daño",
  "actor": "pnj:goblin_3",
  "objetivo": "pj:thalindra",
  "datos": {"cantidad": 7, "tipo_dano": "perforante"},
  "estado_previo_ref": "snap_2026-06-18T20:44:58Z",
  "motivo_llm": "ataque resuelto en combate",
  "semilla_dados": 42
}
```

## 10. Motor de reglas

`reglas/` contiene:
- `srd/`: contenido SRD permitido (con `LICENSE`).
- `casero/`: overlays YAML del usuario.
- `motor.py`: resuelve consultas tipadas (`consultar_regla(tema, contexto)`).
- Componentes: condiciones, combate, conjuros, descanso, viaje, tiradas habilidad, salvaciones, ventaja/desventaja, concentración, muerte, subida de nivel, equipo, monstruos.

No se incluye material con copyright restringido. Cualquier contenido externo va en `compendio/` o cargado dinámicamente por el usuario.

## 11. RAG anti-spoiler

### Ingesta
1. Origen: PDF, Markdown, texto.
2. Conversor (PDF → MD): pluggable (marker, pandoc, docling…).
3. Limpieza: normaliza titulares, listas, tablas.
4. Chunking semántico (por escena/encuentro/sección).
5. Metadatos por chunk: `escena_id`, `localizacion_id`, `pnj_ids`, `tags`, `visibilidad_default` (`oculto`/`condicional`/`publico`), `condiciones_revelacion`.
6. Doble índice: léxico (BM25/FTS) + vectorial (FAISS/Chroma en F7).

### Estado de descubrimiento
`mundo.yaml` registra qué `escena_id` / `localizacion_id` / `pnj_id` son visibles para el jugador.

### Filtros
`rag.buscar_aventura(query, perspectiva)` aplica:
1. Filtra a chunks con `visibilidad_default=publico` **o** cuyo `id` aparece en estado descubierto.
2. Si la skill es de DM (`perspectiva=dm`), no aplica filtro.
3. Si una respuesta contendría tokens marcados como spoiler, se reemplaza por nota `[REDACTADO POR SPOILER]` (log auditable de redacciones).

## 12. Integración con modelos locales

`llm/cliente.py`: cliente OpenAI-compatible (`base_url` + `api_key` configurables). Soporta endpoints: vLLM, vMLX, llama.cpp server, LM Studio, Open WebUI.

Configuración por perfil (`config/perfiles.json`):

```json
{
  "rapido": {"base_url": "...", "modelo": "...", "max_tokens": 800, "temperatura": 0.7, "uso": "juego en vivo"},
  "grande": {"base_url": "...", "modelo": "...", "max_tokens": 4096, "temperatura": 0.8, "uso": "creación de mundos y aventuras"},
  "pequeno": {"base_url": "...", "modelo": "...", "max_tokens": 600, "temperatura": 0.2, "uso": "resúmenes, parsing, tests"}
}
```

Modos: `narrativa`, `reglas`, `resumen`, `worldbuilding`, `aventura`, `combate` → afectan `system_prompt` y `temperatura`/`top_p` recomendados.

### Recomendación inicial de modelos (hardware del usuario: RTX 5090 + Mac Studio M2 Ultra 128 GB)

| Perfil | Sugerencia |
|---|---|
| `rapido` (juego en vivo) | Qwen 2.5 14B / Llama 3.1 8B Instruct (RTX 5090 con vLLM). Latencia baja, buenos diálogos. |
| `grande` (creación) | Qwen 2.5 72B AWQ o Llama 3.3 70B en Mac Studio (mlx) — para campañas/aventuras profundas. |
| `pequeno` (parsing/resumen) | Llama 3.2 3B / Qwen 2.5 7B — coste mínimo para parsing de intención y resúmenes. |

(Estas son recomendaciones iniciales; revisar y validar empíricamente.)

## 13. Sistema de eventos y logs

`nucleo/eventos.py` define `Evento` (dataclass) y bus simple `pub/sub`. Subscribers v1:
- `LoggerEventos`: append a `eventos.jsonl`.
- `ActualizadorMemoriaNarrativa`: agrega entradas a `narrativa.md`.

Todos los `eventos.jsonl` son inmutables (append-only). Se permite "marcar revertido" pero nunca borrar.

## 14. Recuperación de errores

- Validación previa por tool: errores devueltos como `ResultadoHerramienta(ok=False)`; el LLM puede reintentar con corrección.
- Guard anti-loop: máximo de iteraciones LLM↔tool por turno (`config.proyecto.max_iter_turno`).
- Snapshot del estado por turno (`storage/.../snapshots/`) → permite `restaurar_turno_anterior` si una sesión queda corrupta.
- Logger separado para errores (`logs/errores.log`).

## 15. Interfaces futuras

- v1: CLI (`dm-agent`).
- v2: TUI (Textual / Rich).
- v3: web (FastAPI + frontend ligero, integrable con Open WebUI).
- v4: voz (STT/TTS local), generación de imágenes (ComfyUI), mapas.
- v5: multijugador (modo party local), pantalla de DM separada.

El núcleo no asume interfaz: la CLI es un cliente más sobre `AgenteDM`.

## 16. Frase guía

> El LLM narra y guía. La verdad mecánica vive fuera del LLM. Las skills son instrucción descubrible. Las tools son contratos deterministas. Las memorias son tipadas y auditables. El RAG protege spoilers. Cada partida puede continuar mañana exactamente donde quedó.
