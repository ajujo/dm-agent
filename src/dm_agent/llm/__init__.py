"""Cliente LLM OpenAI-compatible (Fase 2).

F2.1 implementa el cliente no-streaming (`ClienteLLM`). El agent loop / REPL
jugable es F2.2.
"""

from dm_agent.llm.cliente import (
    ClienteLLM,
    EndpointLLM,
    ErrorConexionLLM,
    ErrorConfiguracionLLM,
    ErrorLLM,
    ErrorRespuestaLLM,
    MensajeChat,
    PerfilLLM,
    RespuestaLLM,
    ToolCall,
    crear_cliente,
)

__all__ = [
    "ClienteLLM",
    "EndpointLLM",
    "ErrorConexionLLM",
    "ErrorConfiguracionLLM",
    "ErrorLLM",
    "ErrorRespuestaLLM",
    "MensajeChat",
    "PerfilLLM",
    "RespuestaLLM",
    "ToolCall",
    "crear_cliente",
]
