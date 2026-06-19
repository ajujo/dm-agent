# dm-agent

> Director de Juego local-first, modular y persistente. Inspirado arquitectónicamente en Hermes Agent, especializado en rol (D&D 5e primero, agnóstico por diseño).

**Filosofía:** No queremos un chatbot de D&D. Queremos un agente con skills, tools, memoria persistente y verdad mecánica fuera del LLM. El LLM narra; el motor decide.

## Estado actual

**Fase 0–1 + F1.1 + F2.1 + F2.2 + F3.1–F3.6 + F4.1–F4.6 + F5.1**: análisis, esqueleto, repo preparado, cliente LLM, **REPL mínima jugable**, **esquemas base de estado** (`Ficha`, `EstadoPartida`, `Evento`), **persistencia JSON** (`GestorEstado`), **tools `ficha.*` / `hp_xp.*` / `inventario.*`** con **eventos auditables unificados**, **memoria narrativa** (`narrativa.*`), **resúmenes con LLM** (`resumen.*`), **inyección automática de memoria al contexto** y **cierre de sesión** (`sesion.*` + comando `/cerrar`: resumen de cierre + punto de arranque de la próxima). Con **F4.5** el bucle de continuidad quedó **validado extremo a extremo** (test integrado con mock LLM, `tests/test_campaña_integrada_f4.py`) y documentado para validación real (`docs/PRUEBA_MANUAL_F4.md`). Con **F4.6**, el agente ya puede guardar y consultar **PNJ, lugares, pistas, objetivos y frentes abiertos** como entidades narrativas estructuradas (`entidad.*`), e inyectar las más relevantes al contexto. Con **F5.1**, el agente ya puede gestionar **combates narrativos mínimos** con enemigos simples y daño auditable (`combate.*`: iniciar, estado, añadir enemigo, daño a enemigo, terminar), con distancias abstractas (`cerca`/`media`/`lejos`/`fuera_de_alcance`) en vez de grid; **pero aún no implementa el combate táctico completo de D&D**. El proyecto tiene una **campaña persistente básica con memoria narrativa + memoria estructurada + combate narrativo mínimo**. **Aún no tiene RAG, memoria vectorial, extracción automática de entidades, economía, reglas adaptadas implementadas, streaming, iniciativa compleja, XP automática ni cierre automático al salir**: no es una campaña completa.

`dm-agent` usa D&D 5.5 como base pero lo **adapta** a juego narrativo en solitario / teatro de la mente (ver [`docs/REGLAS_ADAPTADAS.md`](docs/REGLAS_ADAPTADAS.md) y [ADR-0017](docs/decisiones/0017-dnd55-narrativo-solitario.md)); esa adaptación es por ahora solo diseño.

Roadmap completo: [`docs/PLAN_FASES.md`](docs/PLAN_FASES.md).

## REPL mínima (F2.2)

`dm-agent` arranca un chat por turnos contra un endpoint LLM OpenAI-compatible. El agente:
- usa un system prompt mínimo de Director de Juego;
- ofrece la tool `dados_tirar` (si el modelo la llama, se ejecuta de verdad y el resultado vuelve al modelo);
- persiste cada turno en un JSONL append-only bajo `storage/sesiones/`.

```bash
conda activate rpg
dm-agent                 # sesión nueva
dm-agent --perfil rapido # elige perfil de modelo
dm-agent --continuar     # retoma la última sesión
dm-agent --debug         # traza de tool calls
```

Comandos dentro del REPL: `/ayuda`, `/salir`, `/guardar`, `/continuar`, `/nueva`, `/debug`.

Limitaciones de F2.2: solo `stream=False`; **sin ficha, combate, inventario, estado mecánico, RAG ni memoria avanzada**; el historial entre turnos se reconstruye solo desde los mensajes de usuario/asistente (el round-trip de tools vive dentro del turno).

## Cliente LLM

Desde **F2.1** existe un cliente OpenAI-compatible basado en `httpx` (sin SDK de OpenAI, sin `litellm`): `dm_agent.llm.ClienteLLM`. Resuelve un perfil de `config/perfiles.json` contra su endpoint en `config/modelos.json`, construye la petición a `POST {base_url}/chat/completions`, soporta `tools` y parsea `tool_calls` **sin ejecutarlas** (la ejecución es trabajo del agent loop, F2.2).

```python
from dm_agent.llm import ClienteLLM

cliente = ClienteLLM.desde_config("rapido")
resp = cliente.chat(messages=[{"role": "user", "content": "Hola"}])
print(resp.content)
```

Limitaciones de F2.1: solo `stream=False` (con `stream=True` lanza `NotImplementedError`). Smoke sin servidor real: `python scripts/check_llm_mock.py`.

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
| [`docs/PRUEBA_MANUAL_F2.md`](docs/PRUEBA_MANUAL_F2.md) | Cómo validar la REPL contra un endpoint local. |
| [`docs/PRUEBA_MANUAL_F4.md`](docs/PRUEBA_MANUAL_F4.md) | Cómo validar la campaña persistente básica contra un endpoint real. |
| [`docs/esquemas/`](docs/esquemas/) | Esquemas de datos: ficha, estado de partida, evento. |
| [`docs/estado/gestor_estado.md`](docs/estado/gestor_estado.md) | Persistencia JSON de estado (GestorEstado). |
| [`docs/tools/ficha.md`](docs/tools/ficha.md) | Tools `ficha.*` (leer/guardar/validar/actualizar/listar). |
| [`docs/tools/hp_xp.md`](docs/tools/hp_xp.md) | Tools `hp_xp.*` (daño/curación/XP/estado vital). |
| [`docs/tools/inventario.md`](docs/tools/inventario.md) | Tools `inventario.*` (inventario simple). |
| [`docs/tools/narrativa.md`](docs/tools/narrativa.md) | Tools `narrativa.*` (bitácora narrativa). |
| [`docs/memoria/narrativa.md`](docs/memoria/narrativa.md) | Memoria narrativa por campaña (bitácora). |
| [`docs/tools/resumen.md`](docs/tools/resumen.md) | Tools `resumen.*` (resúmenes narrativos con LLM). |
| [`docs/memoria/resumenes.md`](docs/memoria/resumenes.md) | Resúmenes narrativos (generación y persistencia). |
| [`docs/memoria/contexto.md`](docs/memoria/contexto.md) | Inyección de memoria narrativa al contexto del agente. |
| [`docs/memoria/cierre_sesion.md`](docs/memoria/cierre_sesion.md) | Cierre y preparación de sesión (`/cerrar`). |
| [`docs/tools/sesion.md`](docs/tools/sesion.md) | Tools `sesion.*` (cierre de sesión). |
| [`docs/tools/entidades.md`](docs/tools/entidades.md) | Tools `entidad.*` (PNJ, lugares, pistas, objetivos, frentes abiertos). |
| [`docs/memoria/entidades.md`](docs/memoria/entidades.md) | Entidades narrativas estructuradas por campaña. |
| [`docs/tools/combate.md`](docs/tools/combate.md) | Tools `combate.*` (combate narrativo mínimo). |
| [`docs/estado/combate.md`](docs/estado/combate.md) | Combate narrativo mínimo: esquemas y persistencia. |
| [`docs/estado/eventos.md`](docs/estado/eventos.md) | Eventos auditables JSONL por campaña. |
| [`docs/REGLAS_ADAPTADAS.md`](docs/REGLAS_ADAPTADAS.md) | D&D 5.5 adaptado a solitario / teatro de la mente (D17). |
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
