#!/usr/bin/env python3
"""Smoke del cliente LLM contra un endpoint simulado (sin servidor real).

Usa `httpx.MockTransport` para verificar el camino feliz del cliente:
una respuesta normal y una respuesta con tool_call. No abre la red.

Uso:
    python scripts/check_llm_mock.py

Sale con 0 si el cliente parsea ambas respuestas como se espera.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

_RAIZ = Path(__file__).resolve().parent.parent
_SRC = _RAIZ / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dm_agent.llm.cliente import ClienteLLM  # noqa: E402


def _handler(request: httpx.Request) -> httpx.Response:
    import json

    cuerpo = json.loads(request.content)
    # Si el usuario manda tools, devolvemos un tool_call; si no, texto.
    if cuerpo.get("tools"):
        return httpx.Response(
            200,
            json={
                "model": cuerpo["model"],
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_demo",
                                    "type": "function",
                                    "function": {
                                        "name": "dados_tirar",
                                        "arguments": '{"expresion": "1d20+3"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
        )
    return httpx.Response(
        200,
        json={
            "model": cuerpo["model"],
            "choices": [
                {"finish_reason": "stop", "message": {"role": "assistant", "content": "¡Hola!"}}
            ],
        },
    )


def main() -> int:
    http_client = httpx.Client(transport=httpx.MockTransport(_handler))
    cliente = ClienteLLM.desde_config(
        "rapido", config_dir=_RAIZ / "config", http_client=http_client
    )

    r1 = cliente.chat(messages=[{"role": "user", "content": "Hola"}])
    assert r1.content == "¡Hola!", r1
    print(f"✓ respuesta normal: content={r1.content!r} finish={r1.finish_reason}")

    tools = [{"type": "function", "function": {"name": "dados_tirar", "parameters": {}}}]
    r2 = cliente.chat(
        messages=[{"role": "user", "content": "tira 1d20+3"}], tools=tools, tool_choice="auto"
    )
    assert r2.tiene_tool_calls, r2
    tc = r2.tool_calls[0]
    print(f"✓ tool_call: {tc.nombre_api} args={tc.argumentos}")

    print("✓ smoke del cliente LLM OK (mock, sin red)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
