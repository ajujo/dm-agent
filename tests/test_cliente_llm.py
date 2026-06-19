"""Tests del cliente LLM OpenAI-compatible (`dm_agent.llm.cliente`).

Sin red real: se inyecta un `httpx.Client` con `httpx.MockTransport`.
"""

import json

import httpx
import pytest

from dm_agent.llm.cliente import (
    ClienteLLM,
    ErrorConexionLLM,
    ErrorConfiguracionLLM,
    ErrorRespuestaLLM,
)

# --- Utilidades de test -------------------------------------------------------


def _escribir_config(dir_config, *, endpoint_extra=None, perfiles_extra=None):
    endpoints = {
        "local": {
            "base_url": "http://localhost:8000/v1",
            "tipo": "openai-compatible",
            "backend": "vllm",
            "api_key_env": "DM_TEST_KEY",
        }
    }
    if endpoint_extra:
        endpoints.update(endpoint_extra)
    perfiles = {
        "rapido": {
            "endpoint": "local",
            "modelo": "qwen3.6-27b",
            "max_tokens": 800,
            "temperatura": 0.7,
            "top_p": 0.9,
        }
    }
    if perfiles_extra:
        perfiles.update(perfiles_extra)

    (dir_config / "modelos.json").write_text(
        json.dumps({"version": 1, "endpoints": endpoints}), encoding="utf-8"
    )
    (dir_config / "perfiles.json").write_text(
        json.dumps({"version": 1, "perfiles": perfiles}), encoding="utf-8"
    )
    (dir_config / "proyecto.json").write_text(
        json.dumps({"perfil_por_defecto": "rapido", "permitir_cloud": False}),
        encoding="utf-8",
    )
    return dir_config


def _cliente_con_handler(dir_config, handler, perfil="rapido"):
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return ClienteLLM.desde_config(perfil, config_dir=dir_config, http_client=http_client)


# --- Carga de configuración ---------------------------------------------------


def test_carga_perfil_valido(tmp_path):
    _escribir_config(tmp_path)
    cliente = ClienteLLM.desde_config("rapido", config_dir=tmp_path)
    assert cliente.perfil.modelo == "qwen3.6-27b"
    assert cliente.endpoint.base_url == "http://localhost:8000/v1"
    assert cliente.url_chat == "http://localhost:8000/v1/chat/completions"


def test_perfil_inexistente(tmp_path):
    _escribir_config(tmp_path)
    with pytest.raises(ErrorConfiguracionLLM):
        ClienteLLM.desde_config("no_existe", config_dir=tmp_path)


def test_endpoint_inexistente(tmp_path):
    _escribir_config(
        tmp_path,
        perfiles_extra={"roto": {"endpoint": "fantasma", "modelo": "x"}},
    )
    with pytest.raises(ErrorConfiguracionLLM):
        ClienteLLM.desde_config("roto", config_dir=tmp_path)


# --- Request sin tools --------------------------------------------------------


def test_request_sin_tools_estructura(tmp_path):
    _escribir_config(tmp_path)
    capturado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = str(request.url)
        capturado["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "hola"}}]},
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    resp = cliente.chat(
        messages=[{"role": "user", "content": "saluda"}],
        temperature=0.3,
        max_tokens=123,
    )

    assert capturado["url"] == "http://localhost:8000/v1/chat/completions"
    body = capturado["body"]
    assert body["model"] == "qwen3.6-27b"
    assert body["messages"] == [{"role": "user", "content": "saluda"}]
    assert body["temperature"] == 0.3
    assert body["max_tokens"] == 123
    assert "tools" not in body
    assert resp.content == "hola"
    assert resp.tiene_tool_calls is False


def test_defaults_de_perfil_si_no_se_pasan_overrides(tmp_path):
    _escribir_config(tmp_path)

    capturado = {}

    def handler(request):
        capturado["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    cliente.chat(messages=[{"role": "user", "content": "x"}])
    assert capturado["body"]["temperature"] == 0.7
    assert capturado["body"]["max_tokens"] == 800
    assert capturado["body"]["top_p"] == 0.9


# --- Request con tools --------------------------------------------------------


def test_request_con_tools_incluye_tools(tmp_path):
    _escribir_config(tmp_path)
    capturado = {}
    tools = [
        {
            "type": "function",
            "function": {"name": "dados_tirar", "description": "tira", "parameters": {}},
        }
    ]

    def handler(request):
        capturado["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    cliente.chat(messages=[{"role": "user", "content": "tira"}], tools=tools, tool_choice="auto")
    assert capturado["body"]["tools"] == tools
    assert capturado["body"]["tool_choice"] == "auto"


# --- Parseo de respuestas -----------------------------------------------------


def test_response_normal_parsea_content(tmp_path):
    _escribir_config(tmp_path)

    def handler(request):
        return httpx.Response(
            200,
            json={
                "model": "qwen3.6-27b",
                "choices": [
                    {"message": {"role": "assistant", "content": "narración"},
                     "finish_reason": "stop"}
                ],
                "usage": {"total_tokens": 10},
            },
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    resp = cliente.chat(messages=[{"role": "user", "content": "x"}])
    assert resp.content == "narración"
    assert resp.finish_reason == "stop"
    assert resp.modelo == "qwen3.6-27b"
    assert resp.uso == {"total_tokens": 10}


def test_response_con_tool_calls_se_parsea(tmp_path):
    _escribir_config(tmp_path)

    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "dados_tirar",
                                        "arguments": "{\"expresion\": \"1d20+3\"}",
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    resp = cliente.chat(messages=[{"role": "user", "content": "tira"}])
    assert resp.content is None
    assert resp.tiene_tool_calls
    tc = resp.tool_calls[0]
    assert tc.id == "call_1"
    assert tc.nombre_api == "dados_tirar"
    # Decisión: 'arguments' se parsea de string JSON a dict, conservando el original.
    assert tc.argumentos == {"expresion": "1d20+3"}
    assert tc.argumentos_json == '{"expresion": "1d20+3"}'


def test_tool_call_con_arguments_dict(tmp_path):
    """Algunos backends devuelven `arguments` ya como objeto; debe aceptarse."""
    _escribir_config(tmp_path)

    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_2",
                                    "function": {
                                        "name": "dados_tirar",
                                        "arguments": {"expresion": "2d6"},
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    resp = cliente.chat(messages=[{"role": "user", "content": "x"}])
    assert resp.tool_calls[0].argumentos == {"expresion": "2d6"}


def test_tool_call_arguments_json_invalido(tmp_path):
    _escribir_config(tmp_path)

    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "c",
                                    "function": {"name": "dados_tirar", "arguments": "{rota"},
                                }
                            ],
                        }
                    }
                ]
            },
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    with pytest.raises(ErrorRespuestaLLM):
        cliente.chat(messages=[{"role": "user", "content": "x"}])


# --- API key ------------------------------------------------------------------


def test_api_key_presente_anade_header(tmp_path, monkeypatch):
    _escribir_config(tmp_path)
    monkeypatch.setenv("DM_TEST_KEY", "secreto-123")
    capturado = {}

    def handler(request):
        capturado["auth"] = request.headers.get("Authorization")
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    cliente.chat(messages=[{"role": "user", "content": "x"}])
    assert capturado["auth"] == "Bearer secreto-123"


def test_endpoint_local_sin_api_key_no_falla(tmp_path, monkeypatch):
    _escribir_config(tmp_path)
    monkeypatch.delenv("DM_TEST_KEY", raising=False)
    capturado = {}

    def handler(request):
        capturado["auth"] = request.headers.get("Authorization")
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    cliente = _cliente_con_handler(tmp_path, handler)
    resp = cliente.chat(messages=[{"role": "user", "content": "x"}])
    assert resp.content == "ok"
    assert capturado["auth"] is None


# --- Errores ------------------------------------------------------------------


def test_http_500_es_error_conexion(tmp_path):
    _escribir_config(tmp_path)

    def handler(request):
        return httpx.Response(500, json={"error": "boom"})

    cliente = _cliente_con_handler(tmp_path, handler)
    with pytest.raises(ErrorConexionLLM):
        cliente.chat(messages=[{"role": "user", "content": "x"}])


def test_fallo_de_red_es_error_conexion(tmp_path):
    _escribir_config(tmp_path)

    def handler(request):
        raise httpx.ConnectError("sin ruta al host")

    cliente = _cliente_con_handler(tmp_path, handler)
    with pytest.raises(ErrorConexionLLM):
        cliente.chat(messages=[{"role": "user", "content": "x"}])


def test_respuesta_sin_choices_es_error_respuesta(tmp_path):
    _escribir_config(tmp_path)

    def handler(request):
        return httpx.Response(200, json={"sin": "choices"})

    cliente = _cliente_con_handler(tmp_path, handler)
    with pytest.raises(ErrorRespuestaLLM):
        cliente.chat(messages=[{"role": "user", "content": "x"}])


def test_cuerpo_no_json_es_error_respuesta(tmp_path):
    _escribir_config(tmp_path)

    def handler(request):
        return httpx.Response(200, content=b"no soy json", headers={"content-type": "text/plain"})

    cliente = _cliente_con_handler(tmp_path, handler)
    with pytest.raises(ErrorRespuestaLLM):
        cliente.chat(messages=[{"role": "user", "content": "x"}])


# --- Streaming ----------------------------------------------------------------


def test_stream_true_no_implementado(tmp_path):
    _escribir_config(tmp_path)

    def handler(request):  # no debería llegar a la red
        raise AssertionError("no debe hacerse petición con stream=True")

    cliente = _cliente_con_handler(tmp_path, handler)
    with pytest.raises(NotImplementedError):
        cliente.chat(messages=[{"role": "user", "content": "x"}], stream=True)
