"""Persistencia de sesión (F2.2): JSONL append-only.

Sin SQLite todavía (ver ADR-0005). Cada línea del fichero es un evento/turno
serializable.
"""

from dm_agent.persistencia.sesion import Sesion

__all__ = ["Sesion"]
