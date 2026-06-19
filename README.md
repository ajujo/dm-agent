# dm-agent

> Director de Juego local-first, modular y persistente. Inspirado arquitectónicamente en Hermes Agent, especializado en rol (D&D 5e primero, agnóstico por diseño).

**Filosofía:** No queremos un chatbot de D&D. Queremos un agente con skills, tools, memoria persistente y verdad mecánica fuera del LLM. El LLM narra; el motor decide.

## Estado actual

**Fase 0–1**: análisis y esqueleto. Aún no se puede jugar. Hay diseño, plantilla de proyecto y un tool real (`dados`) con tests.

Roadmap completo: [`docs/PLAN_FASES.md`](docs/PLAN_FASES.md).

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

Por decidir (ver `DECISIONES_ABIERTAS.md` D13). El contenido SRD que se migre al `compendio/` está bajo OGL 1.0a / CC-BY 4.0 según la versión y deberá llevar `compendio/LICENSE` explícito.

## Inspirado en

- [Hermes Agent](https://github.com/hermes-org/hermes-agent) — patrón de skills + tools + memoria.
- `dnd5e-framework` (proyecto privado anterior) — motor de reglas y tonos narrativos.
