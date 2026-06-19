# AGENTS.md — guía operativa

> Este archivo es para **agentes** (humanos o IA) que vayan a contribuir a `dm-agent` paso a paso. Léelo entero antes de tocar nada.

---

## 1. Entorno

Trabajar **siempre** dentro del entorno conda `rpg`.

```bash
conda activate rpg
which python      # debe apuntar a ~/miniconda3/envs/rpg/bin/python
python --version  # 3.11.x
```

Reglas:

- **Prohibido** `pip install` fuera de `rpg`.
- **Prohibido** `sudo`.
- **Prohibido** modificar config global del sistema.
- Instalación de deps nuevas: editar `pyproject.toml`, luego `pip install -e .[dev]`.

## 2. Rutas autorizadas

| Ruta | Permiso |
|---|---|
| `/home/ajujo/Lab/Workspace/dm-agent/` | lectura + escritura |
| `/home/ajujo/Lab/Workspace/dnd5e-framework/` | **solo lectura** (referencia para migrar) |
| `/home/ajujo/.hermes/` | **solo lectura**, ignorar archivos sensibles (`.env`, `auth.json`, `sessions/`, `memories/`, `*.db`, `logs/`, `pastes/`, `*.bak`) |
| Cualquier otra ruta del sistema | **no tocar** |

## 3. Qué NO debe tocar un agente

- Archivos en `~/.hermes/` (cualquiera).
- Archivos `.env`, `.envrc`, `credentials*`, `secrets*`, `auth*` en cualquier lugar.
- Logs y caches existentes en `dnd5e-framework/` (no son necesarios).
- Configuración global de git, conda, shell.

## 4. Cómo ejecutar los tests

```bash
conda activate rpg
cd /home/ajujo/Lab/Workspace/dm-agent
pytest                          # todo
pytest tests/test_dados.py -v   # un archivo
pytest -k "registro" -v         # por patrón
pytest --lf                     # solo los que fallaron la última vez
```

Política: **ninguna fase se cierra sin `pytest` verde**. Prohibido marcar issues como hechos con tests rojos.

## 5. Cómo añadir una tool

1. Decide a qué toolset pertenece (ver `docs/ARQUITECTURA.md` §6).
2. Crea `src/dm_agent/herramientas/<toolset>.py` o añade a uno existente.
3. Implementa `Herramienta` (Protocol en `herramientas/base.py`):
   - `nombre`, `descripcion`, `schema` (JSON Schema), `requiere`, `modifica`.
   - `disponible(ctx) -> (bool, str)`.
   - `ejecutar(ctx, **args) -> ResultadoHerramienta`.
4. Registra en `herramientas/__init__.py` o en el constructor del registro.
5. Añade tests: 1 happy path + ≥ 2 errores.
6. Documenta en `docs/ARQUITECTURA.md` §6 si introduce un toolset nuevo.

## 6. Cómo añadir una skill

1. Crea `skills/<slug>/SKILL.md`.
2. Frontmatter YAML obligatorio:
   ```yaml
   ---
   name: <slug>
   description: "Una línea"
   version: 0.1.0
   modo: combate|exploración|social|viaje|descanso|gestión
   requiere_tools: [...]
   lee: [...]
   modifica: [...]
   tono_aplicable: [...]
   nivel_juego: [...]
   ---
   ```
3. Cuerpo: cuándo usar, cuándo NO, procedimiento, criterios de éxito, riesgos, ejemplos.
4. Test en `tests/test_skills_loader.py`: que `CargadorSkills` la detecte.
5. (Cuando exista el router) test de que el router la elige en su escenario.

## 7. Cómo añadir un esquema

1. Define `pydantic.BaseModel` en `src/dm_agent/esquemas/`.
2. Versión en campo `version_schema` (entero, incrementa al cambiar estructura incompatible).
3. Documenta en `docs/esquemas/<nombre>.md`.
4. Si rompe compatibilidad: crea migración en `scripts/migraciones/00X_<descripcion>.py`.

## 8. Cómo modificar estado sin romperlo

**Regla de oro:** ninguna ruta de código no-tool puede modificar `EstadoPartida`. Si necesitas cambiarlo, hazlo a través de una tool con validación.

1. Lee el estado vía `GestorEstado.cargar()`.
2. Aplica cambio en memoria.
3. Pasa por validador del esquema.
4. Persiste con `GestorEstado.guardar()`.
5. Emite `Evento` describiendo el cambio.
6. El `LoggerEventos` lo escribe en `eventos.jsonl` automáticamente.

## 9. Cómo registrar eventos

```python
from dm_agent.nucleo.eventos import Evento, bus

bus.publicar(Evento(
    tipo="daño_aplicado",
    actor="pnj:goblin_3",
    objetivo="pj:thalindra",
    datos={"cantidad": 7, "tipo_dano": "perforante"},
    semilla_dados=42,
    motivo_llm="ataque resuelto en combate",
))
```

El bus tiene subscribers fijos (logger, actualizador de bitácora). No bypassear el bus.

## 10. Migraciones de esquema

- Cada cambio rompedor (eliminar/renombrar campo, cambio de tipo) requiere migración en `scripts/migraciones/`.
- Numeración correlativa (`001_*.py`, `002_*.py`...).
- Cada migración debe ser idempotente (re-ejecutable).
- Tests obligatorios: aplicar a fixture vieja, validar fixture nueva.

## 11. Cómo documentar cambios

- README solo cambia si afecta a usuario final.
- `docs/ARQUITECTURA.md` se actualiza si cambia un patrón global.
- Nuevas decisiones cerradas: mover de `DECISIONES_ABIERTAS.md` a un `docs/decisiones/D-XXX-<slug>.md` (ADR ligero).

## 12. Dependencias

- Mantener `pyproject.toml` minimalista.
- Antes de añadir una dep:
  1. ¿La necesito **ya** para una fase actual?
  2. ¿Existe alternativa en stdlib razonable?
  3. ¿Tiene licencia compatible (MIT/Apache/BSD/MPL)?
- Documentar nueva dep con 1 línea de justificación al commitear.

## 13. Compatibilidad con modelos locales

- El cliente LLM (`src/dm_agent/llm/cliente.py`) habla **solo** OpenAI-compatible (`/v1/chat/completions`).
- Prohibido importar `openai` SDK directamente; usar `httpx`.
- Configuración por perfil (`config/perfiles.json`) — no hardcodear `base_url`/`modelo`.

## 14. Trabajar fase por fase

- Cada fase tiene su sección en `docs/PLAN_FASES.md` con archivos, tests y "definición de hecho".
- **Prohibido** trabajar en archivos de fases posteriores hasta cerrar la actual.
- Si una fase necesita reabrirse (bug crítico), abrir issue y discutir antes de avanzar.

## 15. Prohibiciones explícitas

- ❌ **Avanzar de fase sin tests verdes.**
- ❌ **Crear archivos vacíos decorativos.** Cada archivo nuevo cumple un propósito identificable hoy.
- ❌ **Simular tiradas de dados desde el LLM.** Toda tirada pasa por `dados.tirar`.
- ❌ **Modificar estado crítico (HP, XP, inventario, oro, condiciones, misiones) fuera de una tool.**
- ❌ **Incluir material con copyright restringido** (PHB, MM, módulos comerciales sin licencia). Solo SRD 5.1 y casero.
- ❌ **Imports relativos cross-paquete oscuros.** Usa imports absolutos: `from dm_agent.X import Y`.
- ❌ **Tirar tests `xfail` para "ya lo arreglaré".** Borrar o arreglar.

## 16. Política de backups

- Antes de modificar `storage/` de una campaña real, crear copia en `storage/_backups/<campaña>/<timestamp>/`.
- Tests usan fixtures aislados en `tests/fixtures/`, nunca tocan `storage/`.
- Migraciones de esquema generan backup automático del archivo afectado.

## 17. Política de logs

- `logs/sesion_*.jsonl` — append-only, no rotación automática v1 (lo veremos en F11).
- `logs/errores.log` — texto plano, con timestamp y traceback completo.
- `eventos.jsonl` por campaña — append-only, **inmutable**. Reverts se marcan como nuevo evento `evento_revertido`.
- **Nunca** logear: datos personales del jugador, credenciales, tokens, contenidos completos de chat con cloud.

## 18. Política anti-spoiler (F7+)

- Todo chunk RAG tiene `visibilidad_default` obligatorio.
- Filtros se aplican **antes** de inyectar al LLM.
- Tests anti-spoiler son P0: ningún cambio en el filtro merge sin que esos tests pasen.
- Auditoría: cada redacción aplicada se loguea en `logs/redacciones.jsonl` con motivo.

## 19. Convenciones de nombres

- **Módulos / paquetes Python**: `snake_case`, español para dominio (`combate`, `ficha`), inglés para genéricos (`registry` si conviene; preferir `registro`).
- **Clases**: `PascalCase` en español (`AgenteDM`, `RegistroHerramientas`).
- **Skills**: `kebab-case` (`dirigir-combate`).
- **Tools**: `<toolset>.<accion>` snake_case (`combate.iniciar_combate`).
- **Tipos de evento**: `snake_case` participio (`daño_aplicado`, `combate_iniciado`).
- **IDs**: prefijos (`pj:`, `pnj:`, `esc:`, `loc:`, `evt:`, `obj:`).

## 20. Estilo de código

- Formatter: `ruff format`.
- Linter: `ruff check`.
- Type-check: `mypy src/dm_agent` (modo gradual).
- Docstrings en clases y funciones públicas (estilo Google).
- **No** docstrings que solo repitan la firma.
- Líneas < 100 chars (objetivo, no obsesivo).

## 21. Estructura de commits

Prefijos:

| Prefijo | Uso |
|---|---|
| `feat:` | nueva funcionalidad |
| `fix:` | corrección de bug |
| `docs:` | solo documentación |
| `refactor:` | sin cambio funcional |
| `test:` | tests nuevos o mejorados |
| `chore:` | infra, deps, build |
| `data:` | cambios en `compendio/`, `config/tonos/`, fixtures |

Mensaje:
```
<prefix>: <resumen <70 chars en imperativo>

<cuerpo opcional explicando el porqué>

Refs: #F1-04
```

## 22. Checklist por PR / cambio significativo

- [ ] Tests verdes (`pytest`).
- [ ] Lint limpio (`ruff check`).
- [ ] Documentación actualizada si cambia API o patrón.
- [ ] Issue del backlog referenciada o creada.
- [ ] No se modifica estado crítico fuera de tools.
- [ ] No se incluye contenido con copyright restringido.
- [ ] No se introducen secretos.
