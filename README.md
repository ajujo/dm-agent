# dm-agent

> Director de Juego local-first, modular y persistente para D&D 5e.
> El LLM narra; el motor decide.

`dm-agent` es un agente con skills, tools, memoria persistente y verdad mecánica fuera del modelo. No es un chatbot — es un DM que resuelve dados, HP, inventario, combate y memoria a través de herramientas deterministas.

---

## Características

| Módulo | Qué hace |
|---|---|
| **Dados** | `dados_tirar` con semilla determinista, ventaja/desventaja |
| **Ficha** | Leer, guardar, validar, actualizar y listar fichas de personaje |
| **HP / XP** | Daño, curación, XP, estado vital — cada cambio auditable |
| **Inventario** | Añadir, quitar, equipar, desequipar objetos |
| **Memoria** | Bitácora narrativa, resúmenes con LLM, inyección automática al contexto |
| **Entidades** | PNJ, lugares, pistas, objetivos y frentes abiertos estructurados |
| **Combate** | Iniciativa, turnos, ataques contra CA, ventaja/desventaja, reacciones |
| **Sesión** | Cierre con resumen, punto de arranque para la próxima partida |
| **Robustez** | Detección de pseudo-tool-calls, filtrado contextual, deduplicación, comandos manuales |

## Requisitos

- Linux / macOS
- `conda` con entorno `rpg` (Python 3.11+)
- Endpoint OpenAI-compatible local: vLLM, LM Studio, llama.cpp, Open WebUI

## Instalación

```bash
conda activate rpg
git clone https://github.com/ajujo/dm-agent.git
cd dm-agent
pip install -e ".[dev]"
pytest
```

> Toda la instalación va al entorno `rpg`. No usar `pip` global ni `sudo`.

## Uso

```bash
dm-agent                 # sesión nueva, perfil por defecto
dm-agent --perfil rapido # elige perfil de modelo
dm-agent --continuar     # retoma la última sesión
dm-agent --debug         # traza de tool calls
```

### Comandos del REPL

| Comando | Descripción |
|---|---|
| `/ayuda` | Lista de comandos |
| `/salir` | Salir del REPL |
| `/guardar` | Guardar sesión |
| `/continuar` | Retomar última sesión |
| `/nueva` | Crear sesión nueva |
| `/cerrar` | Cerrar sesión con resumen narrativo |
| `/debug` | Alternar modo debug |
| `/tool <nombre> <json>` | Ejecutar una tool sin pasar por el LLM |
| `/combate` | Estado del combate activo |
| `/turno` | Turno actual y ronda |
| `/reacciones` | Reacciones pendientes |
| `/ficha` | Ficha del personaje activo |
| `/estado` | Resumen compacto (ficha, combate, enemigos) |

## Arquitectura

```
CLI (cli.py)
  └── Agent Loop (nucleo/agente.py, nucleo/bucle.py)
        ├── Tool Registry (herramientas/registro.py)
        │     ├── dados, ficha, hp_xp, inventario
        │     ├── narrativa, resumen, sesion
        │     ├── entidades (NPCs, places, clues)
        │     └── combate (initiative, turns, attacks, reactions)
        ├── Memory System (memoria/, narrativa/)
        │     ├── Narrative log (bitácora)
        │     ├── Summaries (LLM-generated)
        │     └── Structured entities (NPCs, places, objectives)
        ├── State Manager (estado/gestor.py) → JSON persistence
        ├── Event Bus (nucleo/eventos.py) → JSONL audit log
        ├── Tool Selector (nucleo/seleccion_tools.py) → filters by intent
        ├── Operational Context (nucleo/contexto_operativo.py) → injects active IDs
        └── LLM Client (llm/cliente.py) → httpx, OpenAI-compatible
```

## Principios de diseño

1. **El LLM narra, las tools deciden mecánica** — HP, dados, reglas se resuelven por herramientas deterministas, nunca por el modelo.
2. **Todo cambio de estado pasa por tools** — Ningún código fuera de una tool modifica `EstadoPartida`.
3. **Eventos auditables** — Cada cambio mecánico emite un `Evento`, registrado en JSONL.
4. **Un solo mensaje system** — Todo el contexto (prompt + memoria + operativo) se fusiona en un único mensaje `system` para compatibilidad con backends.
5. **Filtrado de tools** — No todas las tools se ofrecen a la vez; se filtran por intención del turno para mejorar la fiabilidad del modelo.

## Estado actual

El proyecto tiene una **campaña persistente básica** con:
- memoria narrativa + memoria estructurada (PNJ, lugares, pistas, objetivos)
- combate narrativo con iniciativa, turnos, ataques con ventaja/desventaja y reacciones
- validado de extremo a extremo con tests integrados

**Aún no tiene:** RAG, memoria vectorial, economía, streaming, IA enemiga, motor completo de economía de acciones, XP automática ni cierre automático al salir.

Roadmap completo: [`docs/PLAN_FASES.md`](docs/PLAN_FASES.md)

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Visión completa del sistema |
| [`docs/PLAN_FASES.md`](docs/PLAN_FASES.md) | Hoja de ruta por fases |
| [`docs/REGLAS_ADAPTADAS.md`](docs/REGLAS_ADAPTADAS.md) | D&D 5.5 adaptado a solitario / teatro de la mente |
| [`docs/PRUEBA_MANUAL_F5_COMBATE.md`](docs/PRUEBA_MANUAL_F5_COMBATE.md) | Validar combate narrativo contra endpoint real |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | Issues y backlog |
| [`docs/DECISIONES_ABIERTAS.md`](docs/DECISIONES_ABIERTAS.md) | Decisiones de diseño pendientes |
| [`docs/MODELOS_LOCALES.md`](docs/MODELOS_LOCALES.md) | Recomendaciones por hardware |
| [`AGENTS.md`](AGENTS.md) | Guía operativa para contribuir |

### Herramientas

| Documento | Tools |
|---|---|
| [`docs/tools/dados.md`](docs/tools/dados.md) | `dados_tirar` |
| [`docs/tools/ficha.md`](docs/tools/ficha.md) | `ficha.*` (leer, guardar, validar, actualizar, listar) |
| [`docs/tools/hp_xp.md`](docs/tools/hp_xp.md) | `hp_xp.*` (daño, curación, XP, estado vital) |
| [`docs/tools/inventario.md`](docs/tools/inventario.md) | `inventario.*` (listar, añadir, quitar, equipar, desequipar) |
| [`docs/tools/narrativa.md`](docs/tools/narrativa.md) | `narrativa.*` (bitácora) |
| [`docs/tools/resumen.md`](docs/tools/resumen.md) | `resumen.*` (resúmenes con LLM) |
| [`docs/tools/sesion.md`](docs/tools/sesion.md) | `sesion.*` (cierre de sesión) |
| [`docs/tools/entidades.md`](docs/tools/entidades.md) | `entidad.*` (PNJ, lugares, pistas, objetivos, frentes) |
| [`docs/tools/combate.md`](docs/tools/combate.md) | `combate.*` (combate narrativo) |

### Estado y memoria

| Documento | Contenido |
|---|---|
| [`docs/esquemas/`](docs/esquemas/) | Esquemas de datos: ficha, estado, evento |
| [`docs/estado/gestor_estado.md`](docs/estado/gestor_estado.md) | Persistencia JSON (GestorEstado) |
| [`docs/estado/combate.md`](docs/estado/combate.md) | Combate: esquemas y persistencia |
| [`docs/estado/eventos.md`](docs/estado/eventos.md) | Eventos auditables JSONL |
| [`docs/memoria/narrativa.md`](docs/memoria/narrativa.md) | Bitácora narrativa |
| [`docs/memoria/resumenes.md`](docs/memoria/resumenes.md) | Resúmenes narrativos |
| [`docs/memoria/contexto.md`](docs/memoria/contexto.md) | Inyección de memoria al contexto |
| [`docs/memoria/entidades.md`](docs/memoria/entidades.md) | Entidades narrativas estructuradas |
| [`docs/memoria/cierre_sesion.md`](docs/memoria/cierre_sesion.md) | Cierre y preparación de sesión |

## Licencia

Código bajo **Apache-2.0** ([`LICENSE`](LICENSE)). El contenido SRD que se migre al `compendio/` llevará licencia separada.

## Inspirado en

- [Hermes Agent](https://github.com/hermes-org/hermes-agent) — patrón de skills + tools + memoria
- `dnd5e-framework` (proyecto privado anterior) — motor de reglas y tonos narrativos
