# Decisiones abiertas

> A discutir antes de empezar la fase correspondiente.
>
> **Cerradas en F1.1:** D1, D2, D3, D4, D5, D13 — ver [§ Decisiones cerradas](#decisiones-cerradas)
> y los ADR ligeros en [`docs/decisiones/`](./decisiones/).
> **Cerrada en F3.2:** D17 — ver [ADR-0017](./decisiones/0017-dnd55-narrativo-solitario.md).

| # | Decisión | Opciones | Recomendación inicial | Fase |
|---|---|---|---|---|
| D1 | ✅ **CERRADA** — Lengua de identificadores | Español (como dnd5e) / Inglés / Mixto | **Español** para identificadores de dominio (`ficha`, `combate`), inglés solo para estándares técnicos (`schema`, `httpx`, `JSONL`). | F1 |
| D2 | ✅ **CERRADA** — Validación de schemas | `pydantic` v2 / `dataclasses` + `jsonschema` / `attrs` | **`pydantic` v2** por madurez y validación rica. | F1 |
| D3 | ✅ **CERRADA** — Backend de configuración | JSON / YAML / TOML | **JSON** para configs leídas por código; **YAML/Markdown** para datos curados; **JSONL** para logs/eventos. | F1 |
| D4 | ✅ **CERRADA** — Cliente LLM | `openai` SDK / `httpx` directo / `litellm` | **`httpx` directo** (control total, deps mínimas; mejor compatibilidad multi-backend). | F2 |
| D5 | ✅ **CERRADA** — Persistencia inicial | JSON / YAML / SQLite | **JSON** estado mutable, **JSONL** eventos, **Markdown** bitácora, **YAML** datos curados; SQLite diferido a F11. | F2-F4 |
| D6 | Memoria vectorial | FAISS / Chroma / Qdrant / `sqlite-vec` | **`sqlite-vec`** o **Chroma local** por simplicidad; FAISS si se necesita perf. Decidir en F7. | F7 |
| D7 | Conversión PDF | `marker` / `docling` / `pandoc` / `pdfplumber` | **`marker` o `docling`** (calidad alta); pluggable. | F7 |
| D8 | TUI | `rich` / `textual` / `prompt_toolkit` | **`rich`** para output, `prompt_toolkit` para input; `textual` si crece. | F10 |
| D9 | Sistema de plugins | Entry points / discovery directo en `skills/` | **Discovery directo** para skills (Hermes-style); entry points solo si crece. | F8 |
| D10 | Internacionalización | Hard-coded ES / `gettext` / i18n custom | **Hard-coded ES** v1. Diferir i18n. | F12 |
| D11 | Modelos locales por defecto | Qwen 2.5 / Llama 3 / Mixtral | Ver `MODELOS_LOCALES.md`; perfil "rápido" = Qwen 2.5 14B Instruct (tentativo). | F9 |
| D12 | Subagentes | Cuándo introducir | **F12 o nunca**; primero validar que el agente único basta. | F12 |
| D13 | ✅ **CERRADA** — Licencia del proyecto | MIT / Apache 2.0 / AGPL | **Apache-2.0** para el código; contenido del compendio con licencia separada. | F1 |
| D14 | Soporte multi-sistema (PbtA, FATE…) | Sí v1 / No v1 | **No v1** — primero D&D 5e sólido. Arquitectura genérica preserva opción. | F12 |
| D15 | Estado de combate compartido entre PJ y enemigos | Una estructura única / dos estructuras separadas | **Una única estructura** con `participantes[]`. | F5 |
| D16 | Cómo se pide a un agente pequeño implementar una fase | Issue → PR / Tareas en `AGENTS.md` / Plan + chequeo manual | **Issue (en `docs/BACKLOG.md`) → rama → tests → review** flujo simple. | F1 |
| D17 | ✅ **CERRADA** — D&D 5.5 narrativo en solitario / teatro de la mente | Simulador táctico fiel / Adaptación narrativa | **Adaptación narrativa en solitario** con reglas caseras persistentes aprobadas por el usuario (3 capas). Ver [ADR-0017](./decisiones/0017-dnd55-narrativo-solitario.md) y [`REGLAS_ADAPTADAS.md`](./REGLAS_ADAPTADAS.md). | F3.2 (doc) |

---

## Decisiones cerradas

> Cerradas en la mini-fase **F1.1** (2026-06-19). Detalle ampliado en `docs/decisiones/`.

### D1 — Lengua de identificadores → **Español de dominio, inglés solo técnico**

- Español para el dominio RPG: `ficha`, `combate`, `campaña`, `herramientas`, `memoria`, `reglas`.
- Inglés solo cuando es estándar técnico o ayuda a interoperabilidad: `schema`, `httpx`, `OpenAI-compatible`, `JSONL`.
- **Motivo:** proyecto de uso personal en español que hereda estructura de `dnd5e-framework`.

### D2 — Validación de schemas → **`pydantic` v2**

- Ya está en `pyproject.toml`; aporta validación fuerte, serialización y versionado de esquemas.

### D3 — Backend de configuración → **JSON + YAML/Markdown + JSONL**

- **JSON** para configs leídas por código: `modelos.json`, `perfiles.json`, `proyecto.json`.
- **YAML/Markdown** para datos curados por humanos: skills, tonos, lore, PNJ, facciones.
- **JSONL** para logs/eventos.

### D4 — Cliente LLM → **`httpx` directo**

- Sin SDK `openai` y sin `litellm` por ahora.
- **Motivo:** control total, dependencias mínimas y mejor compatibilidad con vLLM, vMLX, LM Studio, llama.cpp y Open WebUI.

### D5 — Persistencia inicial → **JSON + JSONL + Markdown + YAML**

- **JSON** para estado mutable.
- **JSONL** append-only para eventos/logs.
- **Markdown** para bitácora narrativa y resúmenes.
- **YAML** para datos curados.
- **SQLite** diferido a F11 o cuando el volumen lo justifique.

### D13 — Licencia → **Apache-2.0 (código) + licencia separada para compendio**

- **Código:** Apache-2.0.
- **Contenido SRD/compendio:** licencia separada en `compendio/LICENSE` antes de migrar nada.
- **Material de aventuras/PDFs del usuario:** nunca redistribuir dentro del repo.

> ⚠️ No se migrará contenido SRD, compendio, monstruos, conjuros ni material externo hasta que exista `compendio/LICENSE` y se confirme la licencia aplicable.

### D-COMBATE-06 — Avisos no bloqueantes vs. bloqueo estricto de flujo de combate → **Avisos no bloqueantes**

- `combate_atacar_enemigo` y `combate_atacar_personaje` emiten `"avisos": []` cuando el ataque ocurre fuera del flujo normal (sin iniciativa, fuera de turno, contra enemigo derrotado, todos derrotados).
- **Motivo:** el LLM narra; las herramientas señalizan; el jugador decide. Bloquear el ataque rompería la flexibilidad narrativa (teatro de la mente, D17) y obligaría a un estricto seguimiento de turnos que no siempre es deseable en solitario.
- **Consecuencia:** el ataque se resuelve mecánicamente igual (tirada, daño, HP), pero el resultado incluye avisos que el LLM puede usar para narrar la anomalía ("atacas aunque no es tu turno", "el enemigo ya ha caído", etc.).

---

## Notas para Fase 2

- **Open WebUI (`local_openwebui`):** la `base_url` puede variar según el despliegue. Fase 2 debe validar el endpoint real con un check de red antes de asumir `/api/v1` o `/v1`. Ver también `docs/MODELOS_LOCALES.md`.
