# Análisis del proyecto antiguo — dnd5e-framework

> Fuente: `/home/ajujo/Lab/Workspace/dnd5e-framework/` (lectura). Objetivo: decidir qué reutilizar, reescribir o descartar para `dm-agent`.

## 1. Inventario

| Carpeta | Archivos | Resumen |
|---|---|---|
| `src/` | 161 | 7 módulos (`motor`, `narrativa`, `orquestador`, `herramientas`, `generador`, `personaje`, `persistencia`, `llm`) + 7 CLIs. |
| `compendio/` | 9 | Datos SRD (327 monstruos, armas, armaduras, conjuros, progresión). |
| `config/` | 9 | `llm_config.json`, `proyecto.json`, 6 tonos narrativos. |
| `data/` | 4 | clases, razas, trasfondos, etc. |
| `docs/` | 44 | Arquitectura, esquemas (10), SRD JSON crudos (16). |
| `tests/` | 11 | ~3900 líneas, cobertura sólida en motor/. |
| `storage/` | 18 | Personajes, campañas, runs (fixtures útiles). |

## 2. Clasificación por módulo

| Módulo | Acción | Notas |
|---|---|---|
| `motor/dados.py` | **REUTILIZAR DIRECTO** | API limpia: `tirar("2d6+3")`, ventaja/desventaja, semilla, `ResultadoTirada`. Ideal `tool_dados`. |
| `motor/compendio.py` | **MIGRAR PARCIAL** | Cargador JSON con índices. Aceptable como `CompendioReglas` v1; pensar en SQLite/FTS más adelante. |
| `motor/normalizador.py` | **REESCRIBIR** | Idea (regex + vocabulario + fallback LLM) excelente; código atado a verbos D&D. Patrón sí, código no. |
| `motor/validador.py` | **REESCRIBIR** | Igual: patrón "modo estricto / permisivo" útil, código específico. |
| `motor/pipeline_turno.py` | **MIGRAR PARCIAL** | Pipeline `normalizar → clarificar → validar → ejecutar → narrar` es el corazón a portar. |
| `motor/gestor_combate.py` | **MIGRAR PARCIAL** | Iniciativa/turnos/estado bien resuelto. Abstraer interfaz. |
| `motor/narrador.py` | **MIGRAR PARCIAL** | Patrón "LLM recibe eventos resueltos, narra" se mantiene. |
| `motor/combate_utils.py` | **CONVERTIR EN TOOLS** | `resolver_ataque`, `tirar_daño`, `tirar_iniciativa`. |
| `motor/vocabulario.py` | **DATO** | Tablas verbo→acción. Pasar a YAML/JSON. |
| `motor/reglas_basicas.py` | **DATO** | Fórmulas (CA, mod, bonificador). Tabla, no código. |
| `motor/progresion.py` | **MIGRAR PARCIAL** | Tabla XP/niveles. |
| `motor/llm_adapter.py` | **DESCARTAR** | Wrapper específico; se reemplaza por cliente OpenAI-compatible nuevo. |
| `narrativa/director.py` | **REUTILIZAR DIRECTO** | Análisis de pacing → hints. Patrón valioso y genérico. |
| `narrativa/estado_narrativo.py` | **MIGRAR PARCIAL** | Máquina de estados narrativos. |
| `narrativa/runtime_narrativo.py` | **REESCRIBIR** | Orquestación atada a D&D. |
| `narrativa/generador_aventura.py` | **CONVERTIR EN SKILL** | "Generar aventura" como skill. |
| `narrativa/modelos.py` | **MIGRAR PARCIAL** | Dataclasses base. |
| `orquestador/dm_cerebro.py` | **REESCRIBIR** | Inspira el agent loop pero no se importa. |
| `orquestador/contexto.py` | **MIGRAR PARCIAL** | Estructura del contexto. |
| `orquestador/parser_respuesta.py` | **REESCRIBIR** | Reemplazado por tool_calling estándar. |
| `herramientas/herramienta_base.py` | **REUTILIZAR DIRECTO** | ABC limpia. |
| `herramientas/{combate,tiradas,consultas,estado}.py` | **CONVERTIR EN TOOLS** | Pasar a `dm_agent/herramientas/`. |
| `generador/prompts_bible.py` | **REUTILIZAR PROMPTS** | Plantillas excelentes. |
| `generador/bible_generator.py` | **CONVERTIR EN SKILL** | "Crear aventura/bible". |
| `generador/tonos.py` | **DATO** | Mover a `config/tonos/`. |
| `personaje/creador.py` | **DESCARTAR** | Wizard CLI específico. |
| `personaje/calculador.py` | **MIGRAR PARCIAL** | Fórmulas derivadas. |
| `personaje/{mapper,storage}.py` | **REESCRIBIR** | Nueva persistencia. |
| `persistencia/gestor.py` | **REESCRIBIR** | Diseño nuevo basado en SQLite (v3). |
| `llm/__init__.py` | **DESCARTAR** | Cliente nuevo (OpenAI-compatible genérico). |
| `cli_*.py` (7 archivos, 5600 líneas) | **DESCARTAR** | Reemplazados por CLI única + skills. |

## 3. Compendio

| Archivo | Acción |
|---|---|
| `monstruos.json` (327 entradas, 1.1 MB) | **MIGRAR DIRECTO** |
| `armas.json`, `armaduras_escudos.json`, `progresion_niveles.json` | **MIGRAR DIRECTO** |
| `conjuros.json` (esqueleto) | **MIGRAR + COMPLETAR** |
| `miscelanea.json` | **MIGRAR PARCIAL** |
| `srd_5e_monsters.json`, `monstruos_backup.json` | **DESCARTAR** (duplicados) |

Licencia: contenido SRD 5.1 está bajo OGL/CC-BY 4.0 (según versión). Documentar licencia explícitamente en `compendio/LICENSE` antes de copiar.

## 4. Configuración

| Archivo | Acción |
|---|---|
| `config/tonos/*.json` (6) | **MIGRAR DIRECTO** — son datos de calidad. |
| `config/llm_config.json` | **REDISEÑAR** — formato nuevo separando endpoint/modelo/perfil. |
| `config/proyecto.json` | **REDISEÑAR**. |

## 5. Esquemas y docs

| Archivo | Acción |
|---|---|
| `docs/esquemas/personaje.md` | **MIGRAR DIRECTO** (fuente → derivados → estado_actual). |
| `docs/esquemas/{combate,inventario,mundo,npcs,historial,acciones_normalizadas,meta,monstruo_schema}` | **MIGRAR**, generalizar nombres. |
| `docs/SRD/*.json` (16, 112k líneas) | **NO COPIAR**: ya en compendio/. |
| `docs/arquitectura/pipeline_turno.md` | **REUSAR COMO BASE** del nuevo `ARQUITECTURA.md`. |

## 6. Tests

`test_dados.py` y `test_pipeline_turno.py` migrables casi tal cual. El resto inspira pero requiere reescritura tras refactor.

## 7. Saves / fixtures

`storage/characters/*.json` y `storage/campaigns/campana_ciudad_sangra/` son fixtures excelentes para tests de integración. **MIGRAR como datos de ejemplo en `tests/fixtures/`**.

## 8. Top 10 a reutilizar

1. `motor/dados.py` — directo como `herramientas/dados.py`.
2. `config/tonos/*.json` — directo.
3. Patrón pipeline de `motor/pipeline_turno.py` — adaptar.
4. `compendio/{monstruos,armas,armaduras,progresion_niveles}.json` — directo.
5. `narrativa/director.py` — directo como skill de análisis de pacing.
6. `generador/prompts_bible.py` — prompts directos, código adaptado.
7. Patrón `motor/normalizador.py` (regex + LLM fallback) — adaptar.
8. `docs/esquemas/personaje.md` — directo.
9. `herramientas/herramienta_base.py` — directo.
10. Estructura de `motor/gestor_combate.py` — migrar parcial.

## 9. Top 5 a descartar

1. Todos los `cli_*.py` (TUI específica).
2. `src/llm/__init__.py` (wrapper LLM viejo).
3. `personaje/creador.py` (wizard interactivo).
4. Backups en `compendio/` (`srd_5e_monsters.json`, `monstruos_backup.json`).
5. `docs/arquitectura.md` duplicado de `ARCHITECTURE.md`.
