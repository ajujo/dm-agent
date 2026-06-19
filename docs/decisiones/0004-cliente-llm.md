# ADR-0004 — Cliente LLM

- **Estado:** Aceptada (F1.1, 2026-06-19)
- **Decisión abierta original:** D4
- **Implementación:** Fase 2 (no implementado en F1.1)

## Contexto

El sistema debe funcionar con múltiples backends locales OpenAI-compatible
(vLLM, vMLX, LM Studio, llama.cpp, Open WebUI). Se evaluó el SDK `openai`,
`httpx` directo y `litellm`.

## Decisión

Usar **`httpx` directo** contra los endpoints OpenAI-compatible. No usar el SDK
`openai` ni `litellm` por ahora.

## Consecuencias

- Control total sobre la petición HTTP y mejor compatibilidad con backends que
  difieren en detalles del SDK oficial.
- Dependencias mínimas (`httpx` ya está en `pyproject.toml`).
- En Fase 2 habrá que implementar manualmente: tool-calling, streaming y
  validación en vivo de endpoints (`/models`, `/chat/completions`).
