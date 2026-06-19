# Análisis arquitectónico — Hermes Agent

> Fuente: `/home/ajujo/.hermes/` (lectura). **No se modifica nada en esa ruta.** Datos sensibles (`.env`, `auth.json`, `sessions/`, `memories/`, `*.db`, `logs/`, `pastes/`) excluidos del análisis.

## 1. Layout general

```
~/.hermes/
├── hermes-agent/      # Código fuente (Python)
│   ├── agent/         # Núcleo: agent loop, contexto, memoria, init
│   ├── tools/         # ~100 tools auto-registradas
│   ├── hermes_cli/    # CLI + MCP config
│   ├── gateway/       # Adaptadores externos (Discord, Slack, etc.)
│   ├── plugins/       # Plugins terceros
│   ├── run_agent.py   # Clase AIAgent (orquestador)
│   ├── model_tools.py # Orquestación del registro de tools
│   └── cli.py         # Entry point CLI
├── skills/            # 16 categorías de skills instaladas
├── bin/               # Binarios (uv, uvx, tirith)
├── config.yaml        # Configuración centralizada (no secretos)
├── models.json        # Catálogo de modelos + perfiles
└── SOUL.md            # Template de personalidad/identidad del agente
```

## 2. Sistema de skills (clave a imitar)

Cada skill = carpeta con `SKILL.md` (frontmatter YAML + cuerpo Markdown) + `scripts/`, `references/`, `workflows/`, `tests/` opcionales.

Frontmatter típico:

```yaml
---
name: <slug>
description: "Una línea"
version: X.Y.Z
author: [...]
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [...]
  commands: [...]
metadata:
  hermes:
    tags: [...]
    related_skills: [...]
---
```

Cuerpo: cuándo usar, setup, API, ejemplos, troubleshooting.

**Discovery:** escaneo recursivo de `skills/<categoria>/<slug>/SKILL.md` al inicio; el contenido se inyecta en contexto **solo cuando se invoca** `/skill`. Es el patrón canónico de *progressive disclosure*: la skill es instrucción, no código que siempre se carga.

**Bundles:** un YAML puede agrupar varias skills bajo un comando.

## 3. Sistema de tools

Registro central: `tools/registry.py` con `ToolRegistry`. Cada `tools/*.py` se auto-registra:

```python
registry.register(
    name="my_tool",
    toolset="terminal",
    schema={...},                   # JSON Schema
    handler=my_handler,
    check_fn=availability_check,    # gate por disponibilidad
    requires_env=["MY_VAR"],
    is_async=False,
    description="...",
)
```

`model_tools.py` orquesta: importa módulos, lista definiciones para el LLM, dispatcha por nombre. Toolsets agrupan tools relacionadas (`browser`, `terminal`, `memory`...). MCP se integra como toolset externo descubierto al arranque.

## 4. Agent loop

Entrada: `cli.py` → `AIAgent` (`run_agent.py`). El método core es `run_conversation` (en `agent/conversation_loop.py`).

```
prologue → build_turn_context (system prompt, memoria, compresión)
turn loop:
    LLM call (streaming)
    tool dispatch (secuencial o paralelo)
    inject results
    repeat hasta que no haya tool_calls
post-turn → sync memoria, snapshot sesión
```

Errores clasificados en `error_classifier.py` (rate_limit, quota, invalid_key…) con retry/jitter, credential pool rotation y model fallback. Guardrail anti-loop (`tool loop guard`).

## 5. Memoria

- **Corto plazo:** historial conversación (`messages`).
- **Largo plazo:** `MEMORY.md` (hechos persistentes).
- **Perfil usuario:** archivo separado.
- **Skills history:** uso/frecuencia.

Backends: JSON + SQLite (`state.db`, `response_store.db`). Prefetch al inicio del turno + inyección como "System note" antes del user message. Sync post-turn asincrono.

Config relevante (`memory:` en `config.yaml`): `memory_enabled`, `user_profile_enabled`, `memory_char_limit`, `nudge_interval`, `flush_min_turns`, `provider` (Honcho/Mem0 si aplica).

## 6. Configuración y perfiles

`config.yaml` (estructura, sin valores):

```yaml
model: {default, provider, base_url}
providers: {}            # creds en .env, no aquí
fallback_providers: []
toolsets: [...]
agent:
  max_turns, gateway_timeout, tool_use_enforcement, reasoning_effort
  personalities: {helpful, creative, ...}
delegation: {model, max_concurrent_children, max_spawn_depth}
memory: {...}
cron: {...}
security: {tirith_enabled, redact_secrets}
```

Variables de entorno (sólo nombres): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `HERMES_HOME`…

## 7. Subagentes / delegación

`delegate_task` tool crea `AIAgent` hijo:
- Contexto aislado (sin historial del padre).
- Task ID propio (sesión terminal, file cache).
- Toolset restringido. Blocklist típica: `delegate_task` (no recursión), `clarify`, `memory`, `send_message`.
- Profundidad máxima configurable (`max_spawn_depth`).
- Aprobación: `subagent_auto_deny` por defecto, opt-in a auto-approve.

## 8. Patrones de carga bajo demanda

- Skills: solo al invocar.
- MCP: descubrimiento asíncrono al startup, cacheado.
- `tools/lazy_deps.py`: imports diferidos por provider.
- Context compression: resumen automático cuando se acerca al límite (preservando cache de prompt).

## 9. Convenciones útiles

- Skills `kebab-case`; tools `snake_case`.
- Config nested: `toolset:<nombre>:<clave>`.
- Versionado semver en `SKILL.md`; pin via `/<skill>@X.Y.Z`.
- Separación estricta: código en `hermes-agent/`, datos/estado en `~/.hermes/`.

## 10. Recomendaciones para dm-agent

| Patrón Hermes | dm-agent |
|---|---|
| `AIAgent` + `run_conversation` | **IMITAR**: misma forma (loop + tool dispatch + memoria), recortado. |
| `tools/registry.py` con auto-registro | **IMITAR simplificado**: ~15–25 tools de dominio RPG. |
| Skill = carpeta + `SKILL.md` | **IMITAR**: frontmatter YAML + cuerpo MD; añadir campos RPG. |
| Progressive disclosure de skills | **IMITAR**: discovery global, inyección bajo demanda. |
| Memoria como prefetch + inject | **ADAPTAR**: varias memorias tipadas (mecánica, narrativa, mundo…). |
| MCP integrado | **EVITAR (v1)**, **PREPARAR (v2)**: añade superficie y dependencias. |
| Delegación a subagentes | **EVALUAR (v2)**: útil para "árbitro de reglas" o "guardián continuidad". |
| Gateways multiplataforma | **EVITAR**: CLI primero; web/voz queda fuera de v1. |
| Tirith / sandboxing | **EVITAR (v1)**. |
| `lazy_deps.py` | **SIMPLIFICAR**: imports directos, deps mínimas. |
| Personalidades en config | **ADAPTAR**: perfiles de DM (storyteller, tactical, sandbox, grimdark). |
| Credential pool / rotation | **EVITAR (v1)**: un endpoint local-first basta. |
| Compression de contexto | **DIFERIR (v3+)**: nice-to-have. |

**Tres ideas estructurales que dm-agent adopta sin modificar:**
1. *Skill = unidad de instrucción declarativa, descubrible, opt-in.*
2. *Tool = handler determinista con schema y gate de disponibilidad.*
3. *Memoria persistente como prefetch + inyección controlada.*

**Cosas que dm-agent NO copia:**
- Megaarchivo `run_agent.py` (237 KB). El loop puede caber en <500 líneas si está enfocado.
- Soporte multi-provider exhaustivo: solo OpenAI-compatible (vLLM / LM Studio / llama.cpp / Open WebUI) en v1.
- Plugins / gateways / cron: posterior.
