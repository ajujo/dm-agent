# dm-agent

> Director de Juego local-first, modular y persistente. Inspirado arquitectónicamente en Hermes Agent, especializado en rol (D&D 5e primero, agnóstico por diseño).

**Filosofía:** No queremos un chatbot de D&D. Queremos un agente con skills, tools, memoria persistente y verdad mecánica fuera del LLM. El LLM narra; el motor decide.

## Estado actual

**Fase 0–1 + F1.1 + F2.1**: análisis, esqueleto, repo preparado y cliente LLM. **Aún no se puede jugar** (no hay REPL ni agent loop todavía: eso es F2.2). Hay diseño, plantilla de proyecto, un tool real (`dados`) y un cliente LLM OpenAI-compatible, todo con tests.

Roadmap completo: [`docs/PLAN_FASES.md`](docs/PLAN_FASES.md).

## Cliente LLM

Desde **F2.1** existe un cliente OpenAI-compatible basado en `httpx` (sin SDK de OpenAI, sin `litellm`): `dm_agent.llm.ClienteLLM`. Resuelve un perfil de `config/perfiles.json` contra su endpoint en `config/modelos.json`, construye la petición a `POST {base_url}/chat/completions`, soporta `tools` y parsea `tool_calls` **sin ejecutarlas** (la ejecución es trabajo del agent loop, F2.2).

```python
from dm_agent.llm import ClienteLLM

cliente = ClienteLLM.desde_config("rapido")
resp = cliente.chat(messages=[{"role": "user", "content": "Hola"}])
print(resp.content)
```

Limitaciones de F2.1: solo `stream=False` (con `stream=True` lanza `NotImplementedError`); **no hay todavía REPL ni bucle de juego**. Smoke sin servidor real: `python scripts/check_llm_mock.py`.

## Requisitos

- Linux / macOS.
- `conda` con un entorno llamado `rpg` (Python 3.11+).
- (Para jugar, desde F2) un endpoint OpenAI-compatible local: vLLM, LM Studio, llama.cpp server, vMLX u Open WebUI.

## Instalación

```bash
conda activate rpg
git clone <repo> dm-agent
cd dm-agent
pip install -e .[dev]
pytest
```

> Toda la instalación va al entorno `rpg`. **No usar `pip` global ni `sudo`.**

## Uso (futuro, desde F2)

```bash
dm-agent                          # REPL interactivo
dm-agent --perfil rapido          # cambia perfil de modelo
dm-agent --continuar              # retoma última sesión
```

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Visión completa del sistema. |
| [`docs/PLAN_FASES.md`](docs/PLAN_FASES.md) | Hoja de ruta por fases. |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | Issues iniciales. |
| [`docs/RIESGOS.md`](docs/RIESGOS.md) | Riesgos técnicos y mitigaciones. |
| [`docs/DECISIONES_ABIERTAS.md`](docs/DECISIONES_ABIERTAS.md) | Decisiones pendientes. |
| [`docs/MODELOS_LOCALES.md`](docs/MODELOS_LOCALES.md) | Recomendaciones por hardware. |
| [`docs/ANALISIS_HERMES.md`](docs/ANALISIS_HERMES.md) | Análisis de Hermes Agent. |
| [`docs/ANALISIS_DND5E.md`](docs/ANALISIS_DND5E.md) | Qué reutilizamos de dnd5e-framework. |
| [`AGENTS.md`](AGENTS.md) | Guía operativa para agentes (incluido Claude Code). |

## Licencia

Código bajo **Apache-2.0** (ver [`LICENSE`](LICENSE) y ADR-0013 en `docs/decisiones/`). El contenido SRD que se migre al `compendio/` llevará **licencia separada** (`compendio/LICENSE`, OGL 1.0a / CC-BY 4.0 según versión) y no se migrará nada hasta que ese archivo exista.

## Inspirado en

- [Hermes Agent](https://github.com/hermes-org/hermes-agent) — patrón de skills + tools + memoria.
- `dnd5e-framework` (proyecto privado anterior) — motor de reglas y tonos narrativos.
