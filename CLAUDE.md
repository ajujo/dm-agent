# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Early-stage Python framework for solo tabletop RPG adventures with LLM narration and a deterministic rules engine. Intended as a system-agnostic generalization of the sibling project at `../dnd5e-framework/`, which implements the same architecture for D&D 5e specifically.

The core invariant (inherited from `dnd5e-framework`): **the LLM narrates and guides; the rules engine decides mechanics.** The LLM never resolves dice, damage, or rule adjudications.

## Reference implementation

`/home/ajujo/Lab/Workspace/dnd5e-framework/` is the canonical reference. Its `CLAUDE.md`, `docs/arquitectura/`, and `src/` are authoritative sources for architectural patterns, naming conventions, and the pipeline contract. When the intent of a new module is unclear, check the dnd5e equivalent first.

Key patterns to carry forward:

- **Layered structure**: CLI → Orchestrator (`dm_cerebro`) → Motor (rules) + LLM client + Tools
- **Dependency injection**: `CompendioMotor` (or equivalent data registry) is injected through constructors; only CLI entry points call the factory function directly
- **Pipeline contract**: `PipelineTurno.procesar()` returns a discriminated result (`NECESITA_CLARIFICAR` / `ACCION_RECHAZADA` / `ACCION_APLICADA`); all three cases must be handled by callers
- **LLM integration at exactly two points**: normalization fallback and narrator callback; no new LLM call sites inside the motor
- **Event-driven narration**: events emitted by the motor are the only payload the narrator LLM sees — it cannot inspect raw state
- **Spanish naming**: identifiers, log strings, and user-facing text in Spanish

## Conventions

- Commit prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Single external dependency target: `requests` (avoid adding heavy dependencies)
- LLM target: OpenAI-compatible endpoint at `http://localhost:8000/v1` (vLLM)
