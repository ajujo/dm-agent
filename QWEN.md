# dm-agent — Contexto del proyecto

## Qué es este proyecto

**dm-agent** es un Director de Juego local-first, modular y persistente para juegos de rol de mesa (D&D 5e primero, agnóstico por diseño). **No es un chatbot de D&D** — es un agente con skills, tools, memoria persistente y verdad mecánica fuera del LLM. El LLM narra; el motor decide.

Escrito en Python 3.11+, funciona contra cualquier endpoint OpenAI-compatible (vLLM, LM Studio, llama.cpp, Open WebUI) y proporciona un REPL por turnos con herramientas deterministas para dados, fichas, HP/XP, inventario, memoria narrativa, combate y gestión de sesiones.

## Arquitectura

```
CLI (cli.py)
  └── Bucle del Agente (nucleo/agente.py, nucleo/bucle.py)
        ├── Registro de Herramientas (herramientas/registro.py)
        │     ├── dados, ficha, hp_xp, inventario
        │     ├── narrativa, resumen, sesion
        │     ├── entidades (PNJs, lugares, pistas)
        │     └── combate (iniciativa, turnos, ataques, reacciones)
        ├── Sistema de Memoria (memoria/, narrativa/)
        │     ├── Bitácora narrativa
        │     ├── Resúmenes (generados por LLM)
        │     └── Entidades estructuradas (PNJs, lugares, objetivos)
        ├── Gestor de Estado (estado/gestor.py) → persistencia JSON
        ├── Bus de Eventos (nucleo/eventos.py) → auditoría JSONL
        ├── Selector de Tools (nucleo/seleccion_tools.py) → filtra por intención
        ├── Contexto Operativo (nucleo/contexto_operativo.py) → inyecta IDs activos
        └── Cliente LLM (llm/cliente.py) → httpx, OpenAI-compatible, sin SDK
```

### Principios de diseño

1. **El LLM narra, las tools deciden mecánicas** — HP, dados, reglas se resuelven con herramientas Python deterministas, nunca por el modelo.
2. **Todo cambio de estado pasa por una tool** — Ningún código fuera de una tool puede modificar `EstadoPartida`.
3. **Eventos auditables** — Cada cambio mecánico emite un `Evento`, registrado en JSONL.
4. **Mensaje system único** — Todo el contexto system (prompt + memoria + contexto operativo) se fusiona en un único mensaje `system` inicial para evitar errores de backends LLM.
5. **Filtrado de tools** — No todas las tools se ofrecen a la vez; `seleccion_tools.py` filtra por intención del turno para mejorar la fiabilidad del modelo.

## Estructura del proyecto

| Directorio | Propósito |
|---|---|
| `src/dm_agent/` | Paquete principal |
| `src/dm_agent/nucleo/` | Bucle del agente, eventos, selección de tools, contexto operativo |
| `src/dm_agent/herramientas/` | Herramientas deterministas (dados, ficha, combate, etc.) |
| `src/dm_agent/esquemas/` | Modelos Pydantic (Ficha, EstadoPartida, Evento, etc.) |
| `src/dm_agent/estado/` | Persistencia de estado (GestorEstado) |
| `src/dm_agent/llm/` | Cliente HTTP OpenAI-compatible (httpx, sin SDK) |
| `src/dm_agent/memoria/` | Memoria narrativa, resúmenes, inyección de contexto |
| `src/dm_agent/narrativa/` | Bitácora narrativa |
| `src/dm_agent/persistencia/` | Utilidades de persistencia JSON |
| `src/dm_agent/skills/` | Cargador de skills (archivos SKILL.md) |
| `src/dm_agent/prompts/` | Plantillas de prompt system (Markdown) |
| `config/` | `perfiles.json`, `modelos.json`, `proyecto.json`, `tonos/` |
| `skills/` | Definiciones de skills (SKILL.md) |
| `compendio/` | Datos SRD/homebrew (vacío hasta resolver licencias) |
| `storage/` | Datos de campaña en runtime (sesiones, estado, eventos) |
| `docs/` | Arquitectura, plan de fases, ADRs, esquemas, docs de tools, tests manuales |
| `tests/` | Suite de pytest (42 archivos de test) |
| `scripts/` | Scripts de utilidad (check_perfil, check_llm_mock, migraciones) |

## Construcción y ejecución

### Prerrequisitos
- Linux / macOS
- `conda` con entorno `rpg` (Python 3.11+)
- Endpoint OpenAI-compatible (vLLM, LM Studio, llama.cpp, etc.)

### Instalación
```bash
conda activate rpg
pip install -e ".[dev]"
```

### Ejecutar el REPL
```bash
dm-agent                          # sesión nueva, perfil por defecto
dm-agent --perfil rapido          # perfil específico
dm-agent --continuar              # reanudar última sesión
dm-agent --debug                  # traza de tool calls
```

### Comandos del REPL
`/ayuda`, `/salir`, `/guardar`, `/continuar`, `/nueva`, `/cerrar`, `/debug`, `/tool <nombre> <json_args>`, `/combate`, `/turno`, `/reacciones`, `/ficha`, `/estado`

### Makefile
```bash
make install      # pip install -e ".[dev]"
make test         # pytest -v
make lint         # ruff check .
make format       # ruff format src tests scripts
make check        # lint + test + check-config
make clean        # eliminar artefactos de build
```

### Testing
```bash
conda activate rpg
pytest                          # suite completa
pytest tests/test_dados.py -v   # archivo individual
pytest -k "registro" -v         # por patrón
pytest --lf                     # últimos fallos
```

**Política: Ninguna fase se cierra sin tests verdes.**

## Configuración

- **`config/perfiles.json`** — Perfiles de modelo (`rapido`, `grande`, `pequeno`) con endpoint, nombre de modelo, tokens, temperatura.
- **`config/modelos.json`** — Definiciones de endpoint (base_url, tipo de backend, variable de entorno de API key).
- **`config/proyecto.json`** — Valores por defecto del proyecto (perfil, tono, configuración de memoria, campaña activa, rutas).
- **`config/tonos/`** — Configuraciones de tono narrativo.

## Convenciones de desarrollo

### Estilo de código
- Formatter: `ruff format`
- Linter: `ruff check` (E, F, W, I, UP, B, C4, SIM; E501 ignorado)
- Type check: `mypy src/dm_agent` (modo gradual)
- Longitud de línea: < 100 chars (objetivo, no obsesivo)
- Docstrings: Estilo Google solo en clases y funciones públicas; sin docstrings que solo repitan la firma

### Convenciones de nombres
- Módulos/paquetes: `snake_case`, español para términos de dominio (`combate`, `ficha`)
- Clases: `PascalCase` en español (`AgenteDM`, `RegistroHerramientas`)
- Skills: `kebab-case` (`dirigir-combate`)
- Tools: `<toolset>.<accion>` snake_case (`combate.iniciar_combate`)
- Tipos de evento: `snake_case` participio (`daño_aplicado`, `combate_iniciado`)
- IDs: con prefijo (`pj:`, `pnj:`, `esc:`, `loc:`, `evt:`, `obj:`)

### Formato de commits
```
<prefix>: <resumen <70 chars imperativo>

<cuerpo opcional explicando el porqué>

Refs: #F1-04
```
Prefijos: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `data:`

### Solo imports absolutos
Usar `from dm_agent.X import Y`, nunca imports relativos cross-paquete.

### Dependencias
- `pyproject.toml` minimalista. Nuevas deps deben estar justificadas, licenciadas (MIT/Apache/BSD/MPL) y necesarias para la fase actual.
- El cliente LLM usa solo `httpx` — nunca importar SDK de `openai` directamente.

## Disciplina de fases

El proyecto sigue un roadmap por fases (`docs/PLAN_FASES.md`). Reglas clave:
- **No trabajar en archivos de fases posteriores hasta cerrar la actual.**
- **Ninguna fase se cierra sin `pytest` verde.**
- **Sin archivos placeholder vacíos.** Cada archivo nuevo sirve un propósito identificable.
- **Sin tests `xfail`.** Arreglar o eliminar.

## Estado actual del proyecto

Completado hasta **F6.5.1** — campaña persistente con memoria narrativa, entidades estructuradas, combate narrativo (iniciativa, turnos, ataques con ventaja/desventaja, propuestas de reacción), validado extremo a extremo.

**Brechas actuales:** Sin RAG, sin memoria vectorial, sin extracción automática de entidades, sin economía, sin streaming, sin IA enemiga, sin economía de acciones completa, sin XP automática, sin cierre automático de combate.

**Contexto reciente:**
- F6.5: Contexto operativo activo, comandos cómodos del REPL, trim de comandos, salto de enemigos derrotados, señales `todos_los_enemigos_derrotados` / `deberia_terminar_combate`.
- F6.5.1: Corrección de compatibilidad con vLLM/Qwen — todos los bloques `system` se fusionan en un único mensaje `system` inicial.
- Tests actuales: 472 passed. `ruff check .`: limpio. `python scripts/check_perfil.py`: configuración válida.

## Archivos clave para desarrollo

| Archivo | Importancia |
|---|---|
| `src/dm_agent/nucleo/agente.py` | Bucle del agente, construcción de mensajes, ejecución de tools, lógica de reintento |
| `src/dm_agent/nucleo/bucle.py` | Bucle interactivo REPL, gestión de sesiones, comandos REPL |
| `src/dm_agent/nucleo/seleccion_tools.py` | Filtrado de tools por intención (crítico para fiabilidad del modelo) |
| `src/dm_agent/nucleo/contexto_operativo.py` | Inyecta IDs activos en el prompt system |
| `src/dm_agent/herramientas/registro.py` | Registro de herramientas — donde se registran todas las tools |
| `src/dm_agent/esquemas/estado.py` | Esquema `EstadoPartida` — única fuente de verdad |
| `src/dm_agent/llm/cliente.py` | Cliente HTTP OpenAI-compatible |
| `src/dm_agent/cli.py` | Punto de entrada CLI |
| `AGENTS.md` | Guía operativa para agentes que contribuyen a este proyecto |

## Reglas de trabajo

1. **Trabajar siempre en fases pequeñas y acotadas.** Cada cambio debe ser lo suficientemente pequeño como para entenderse, testearse y revertirse.
2. **No ampliar alcance sin pedir confirmación.** Si surge trabajo adicional, preguntar antes de hacerlo.
3. **No cambiar mecánicas de D&D salvo instrucción explícita.** Las reglas de juego son sagradas; cualquier adaptación requiere aprobación.
4. **No tocar configuración local ni secretos.** `config/perfiles.json` solo lectura. Nunca incluir en commits.
5. **No incluir `docs/seguimiento/` en commits** salvo instrucción explícita.
6. **Ejecutar siempre antes de commitear:**
   - `pytest` (tests verdes)
   - `ruff check .` (lint limpio)
   - `python scripts/check_perfil.py` (config válida)
7. **Antes de tocar código, revisar tests existentes relacionados.** Entender qué cubren antes de modificar.
8. **Cada bug corregido debe tener test de regresión.** Sin test, no hay fix.
9. **Si hay dudas de diseño, parar y preguntar.** No asumir ni improvisar.
10. **Activar entorno antes de trabajar:** `conda activate rpg`.

## Prohibiciones (de AGENTS.md)

- ❌ Nunca modificar estado fuera de una tool
- ❌ Nunca dejar que el LLM tire dados (todo pasa por `dados.tirar`)
- ❌ Nunca incluir material con copyright (PHB, MM, módulos comerciales) — solo SRD 5.1 y homebrew
- ❌ Nunca filtrar secretos, tokens o contenidos de chat en logs
- ❌ Nunca usar `sudo` ni instalar fuera del entorno conda `rpg`
- ❌ Nunca tocar archivos en `~/.hermes/`
- ❌ Nunca tocar `/home/ajujo/Lab/Workspace/dnd5e-framework/` (solo lectura como referencia)
