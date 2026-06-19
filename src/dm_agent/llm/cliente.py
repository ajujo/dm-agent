"""Cliente LLM OpenAI-compatible basado en `httpx`.

Diseñado para hablar con endpoints OpenAI-compatible locales (vLLM, MLX-LM,
LM Studio, llama.cpp server, Open WebUI…). No usa el SDK `openai` ni `litellm`
(ver ADR-0004).

Alcance F2.1:
- Carga de configuración (`modelos.json`, `perfiles.json`, `proyecto.json`).
- Resolución de perfil → endpoint.
- `chat()` no-streaming, con o sin `tools`.
- Parseo de `tool_calls` SIN ejecutarlas (eso es trabajo del agent loop / registro).
- `stream=True` queda diseñado pero lanza `NotImplementedError` (será F2.2+).

Decisiones técnicas (F2.1):
- Los `arguments` de un tool_call llegan como string JSON en la API OpenAI.
  El cliente los parsea a `dict` (`ToolCall.argumentos`) y conserva el string
  original en `ToolCall.argumentos_json`. Si el JSON es inválido → `ErrorRespuestaLLM`.
- El nombre de función devuelto por el modelo es el **nombre API** (p. ej.
  `dados_tirar`); el cliente NO lo traduce a nombre interno: eso lo hace
  `RegistroHerramientas.dispatch_api()` aguas abajo.
- Cualquier respuesta HTTP no-2xx o fallo de conexión → `ErrorConexionLLM`.
- Cualquier cuerpo 2xx que no encaje en el contrato esperado → `ErrorRespuestaLLM`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

# --- Errores tipados ----------------------------------------------------------


class ErrorLLM(Exception):
    """Base de todos los errores del subsistema LLM."""


class ErrorConfiguracionLLM(ErrorLLM):
    """Configuración ausente o incoherente (perfil/endpoint mal resueltos)."""


class ErrorConexionLLM(ErrorLLM):
    """Fallo de red o respuesta HTTP no-2xx del endpoint."""


class ErrorRespuestaLLM(ErrorLLM):
    """La respuesta del endpoint no encaja con el contrato esperado."""


# --- Modelos de datos ---------------------------------------------------------


class EndpointLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nombre: str
    base_url: str
    tipo: str = "openai-compatible"
    backend: str | None = None
    api_key_env: str | None = None


class PerfilLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nombre: str
    endpoint: str
    modelo: str
    max_tokens: int | None = None
    temperatura: float | None = None
    top_p: float | None = None


class MensajeChat(BaseModel):
    """Mensaje en formato OpenAI. Conveniencia opcional: `chat()` también
    acepta dicts directamente."""

    model_config = ConfigDict(extra="allow")

    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    id: str
    nombre_api: str
    argumentos: dict[str, Any]
    argumentos_json: str


class RespuestaLLM(BaseModel):
    role: str = "assistant"
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    modelo: str | None = None
    uso: dict[str, Any] | None = None
    bruto: dict[str, Any] | None = None

    @property
    def tiene_tool_calls(self) -> bool:
        return bool(self.tool_calls)


# --- Cliente ------------------------------------------------------------------

_RAIZ = Path(__file__).resolve().parents[3]
_CONFIG_POR_DEFECTO = _RAIZ / "config"


def _cargar_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise ErrorConfiguracionLLM(f"no se encuentra {path}") from e
    except json.JSONDecodeError as e:
        raise ErrorConfiguracionLLM(f"{path}: JSON inválido ({e})") from e


def _serializar_mensaje(m: MensajeChat | dict[str, Any]) -> dict[str, Any]:
    if isinstance(m, MensajeChat):
        return m.model_dump(exclude_none=True)
    if isinstance(m, dict):
        return m
    raise ErrorConfiguracionLLM(f"mensaje no soportado: {type(m)!r}")


class ClienteLLM:
    """Cliente para un perfil concreto contra un endpoint OpenAI-compatible."""

    def __init__(
        self,
        perfil: PerfilLLM,
        endpoint: EndpointLLM,
        *,
        api_key: str | None = None,
        timeout: float = 60.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.perfil = perfil
        self.endpoint = endpoint
        self._api_key = api_key
        self._timeout = timeout
        self._http_client = http_client

    # -- Construcción desde config --------------------------------------------

    @classmethod
    def desde_config(
        cls,
        nombre_perfil: str,
        *,
        config_dir: Path | None = None,
        timeout: float = 60.0,
        http_client: httpx.Client | None = None,
    ) -> ClienteLLM:
        config_dir = config_dir or _CONFIG_POR_DEFECTO
        modelos = _cargar_json(config_dir / "modelos.json")
        perfiles = _cargar_json(config_dir / "perfiles.json")

        perfiles_map = perfiles.get("perfiles", {})
        if nombre_perfil not in perfiles_map:
            disponibles = ", ".join(sorted(perfiles_map)) or "(ninguno)"
            raise ErrorConfiguracionLLM(
                f"perfil {nombre_perfil!r} no existe. Disponibles: {disponibles}"
            )
        perfil = PerfilLLM(nombre=nombre_perfil, **perfiles_map[nombre_perfil])

        endpoints_map = modelos.get("endpoints", {})
        if perfil.endpoint not in endpoints_map:
            raise ErrorConfiguracionLLM(
                f"perfil {nombre_perfil!r} apunta a endpoint inexistente {perfil.endpoint!r}"
            )
        endpoint = EndpointLLM(nombre=perfil.endpoint, **endpoints_map[perfil.endpoint])

        api_key = None
        if endpoint.api_key_env:
            api_key = os.environ.get(endpoint.api_key_env) or None

        return cls(
            perfil,
            endpoint,
            api_key=api_key,
            timeout=timeout,
            http_client=http_client,
        )

    # -- Petición -------------------------------------------------------------

    @property
    def url_chat(self) -> str:
        return self.endpoint.base_url.rstrip("/") + "/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _construir_payload(
        self,
        messages: list[MensajeChat | dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None,
        tool_choice: Any | None,
        temperature: float | None,
        max_tokens: int | None,
        stream: bool,
    ) -> dict[str, Any]:
        temp = temperature if temperature is not None else self.perfil.temperatura
        max_t = max_tokens if max_tokens is not None else self.perfil.max_tokens

        payload: dict[str, Any] = {
            "model": self.perfil.modelo,
            "messages": [_serializar_mensaje(m) for m in messages],
            "stream": stream,
        }
        if temp is not None:
            payload["temperature"] = temp
        if max_t is not None:
            payload["max_tokens"] = max_t
        if self.perfil.top_p is not None:
            payload["top_p"] = self.perfil.top_p
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        return payload

    def chat(
        self,
        messages: list[MensajeChat | dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> RespuestaLLM:
        if stream:
            raise NotImplementedError(
                "streaming (stream=True) no está implementado en F2.1; usa stream=False"
            )

        payload = self._construir_payload(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )

        try:
            if self._http_client is not None:
                resp = self._http_client.post(
                    self.url_chat, json=payload, headers=self._headers()
                )
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.post(self.url_chat, json=payload, headers=self._headers())
        except httpx.RequestError as e:
            # No incluimos headers (podrían llevar la API key) en el mensaje.
            raise ErrorConexionLLM(f"fallo de conexión con {self.url_chat}: {e}") from e

        if resp.status_code >= 400:
            raise ErrorConexionLLM(
                f"endpoint respondió HTTP {resp.status_code} en {self.url_chat}"
            )

        return self._parsear_respuesta(resp)

    # -- Parseo ---------------------------------------------------------------

    def _parsear_respuesta(self, resp: httpx.Response) -> RespuestaLLM:
        try:
            cuerpo = resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            raise ErrorRespuestaLLM(f"el cuerpo no es JSON válido: {e}") from e

        if not isinstance(cuerpo, dict):
            raise ErrorRespuestaLLM("respuesta inesperada: el cuerpo no es un objeto JSON")

        choices = cuerpo.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ErrorRespuestaLLM("respuesta sin 'choices'")

        primero = choices[0]
        if not isinstance(primero, dict):
            raise ErrorRespuestaLLM("'choices[0]' malformado")
        mensaje = primero.get("message")
        if not isinstance(mensaje, dict):
            raise ErrorRespuestaLLM("'choices[0].message' ausente o malformado")

        tool_calls = self._parsear_tool_calls(mensaje.get("tool_calls"))

        return RespuestaLLM(
            role=mensaje.get("role", "assistant"),
            content=mensaje.get("content"),
            tool_calls=tool_calls,
            finish_reason=primero.get("finish_reason"),
            modelo=cuerpo.get("model"),
            uso=cuerpo.get("usage"),
            bruto=cuerpo,
        )

    @staticmethod
    def _parsear_tool_calls(raw: Any) -> list[ToolCall]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ErrorRespuestaLLM("'tool_calls' debe ser una lista")

        salida: list[ToolCall] = []
        for tc in raw:
            if not isinstance(tc, dict):
                raise ErrorRespuestaLLM("tool_call malformado (no es objeto)")
            func = tc.get("function")
            if not isinstance(func, dict) or "name" not in func:
                raise ErrorRespuestaLLM("tool_call sin 'function.name'")

            args_raw = func.get("arguments", "{}")
            if isinstance(args_raw, dict):
                argumentos = args_raw
                argumentos_json = json.dumps(args_raw, ensure_ascii=False)
            elif isinstance(args_raw, str):
                argumentos_json = args_raw
                try:
                    argumentos = json.loads(args_raw or "{}")
                except json.JSONDecodeError as e:
                    raise ErrorRespuestaLLM(
                        f"'arguments' de tool_call no es JSON válido: {e}"
                    ) from e
                if not isinstance(argumentos, dict):
                    raise ErrorRespuestaLLM("'arguments' de tool_call no decodifica a objeto")
            else:
                raise ErrorRespuestaLLM("'arguments' de tool_call con tipo inesperado")

            salida.append(
                ToolCall(
                    id=tc.get("id", ""),
                    nombre_api=func["name"],
                    argumentos=argumentos,
                    argumentos_json=argumentos_json,
                )
            )
        return salida


def crear_cliente(
    nombre_perfil: str,
    *,
    config_dir: Path | None = None,
    timeout: float = 60.0,
    http_client: httpx.Client | None = None,
) -> ClienteLLM:
    """Atajo de fábrica equivalente a `ClienteLLM.desde_config`."""
    return ClienteLLM.desde_config(
        nombre_perfil,
        config_dir=config_dir,
        timeout=timeout,
        http_client=http_client,
    )
