# Riesgos técnicos

| # | Riesgo | Impacto | Probabilidad | Mitigación |
|---|---|---|---|---|
| R1 | El LLM intenta resolver mecánica por su cuenta | Estado corrupto, inmersión rota | Alta | System prompt férreo + validador rechaza cambios de HP/XP/inventario sin `tool_call`. Tests verifican intentos directos. |
| R2 | Tool-calling poco fiable con modelos locales pequeños | Loops, errores de schema | Alta | Perfil "pequeño" reservado a parsing; perfil "rápido" 14B+ para juego; reintentos con corrección de schema. |
| R3 | Fugas de spoilers desde RAG | Rompe campañas importadas | Alta | Filtros por `visibilidad_default`; pasos de auditoría; tests dedicados; metadatos obligatorios por chunk. |
| R4 | Crecimiento de contexto descontrolado | Latencia, coste tokens | Media | Memoria tipada, resúmenes periódicos, inyección selectiva. |
| R5 | Conversión PDF → Markdown defectuosa | Aventura importada inútil | Media | Pluggable (marker, docling, pandoc); revisión humana post-ingesta. |
| R6 | Cambios de esquema rompen partidas viejas | Pérdida de campañas | Media | Versionado de esquemas + migraciones en `scripts/migraciones/`. |
| R7 | Dependencia de un único conda env | Conflictos al instalar deps nuevas | Baja | `pyproject.toml` con upper bounds; documentar en `AGENTS.md`. |
| R8 | Mezcla pip/conda | Entorno irreproducible | Media | Política: `conda` solo para Python base; resto `pip install -e .[dev]`. |
| R9 | Persistencia JSON no escala a campañas largas | I/O lento, conflictos | Media | Plan claro de migración a SQLite (F11+). |
| R10 | Subagentes recursivos descontrolados | Coste tokens, complejidad | Media-Baja | Profundidad máxima 1 hasta F12+; blocklist de tools en hijos. |
| R11 | Inclusión accidental de copyright (PHB, MM…) | Legal | Alta si ocurre | Solo SRD 5.1 (OGL/CC-BY 4.0) en `compendio/`. Material importado por el usuario nunca se redistribuye. |
| R12 | Logs con info sensible del jugador | Privacidad | Baja | Política: nada de PII en logs; `redact_secrets` heredado de Hermes idea. |
| R13 | Determinismo roto entre versiones | Tests frágiles | Media | Semillas fijas en tests, congelar versiones de deps clave. |
| R14 | Sobreingeniería temprana | Atascamos en infra antes de jugar | Alta | Política: nada de SQLite/vector/MCP hasta tener combate y memoria funcionales. |
| R15 | Skills mal documentadas → router falla | Skill nunca se invoca | Media | Test obligatorio de router por skill. |
