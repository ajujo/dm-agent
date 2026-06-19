"""Registro central de herramientas.

Mantiene un dict nombre→Herramienta y expone:
- registrar(herramienta)
- dispatch(nombre_interno, ctx, **args) -> ResultadoHerramienta
- dispatch_api(nombre_api, ctx, **args) -> ResultadoHerramienta
- esquemas_disponibles(ctx) -> list[dict] (para enviar al LLM como `tools`)

Compatibilidad OpenAI-compatible
--------------------------------
Internamente las herramientas usan nombres `<toolset>.<accion>` (p. ej.
`dados.tirar`). Las APIs OpenAI-compatible exigen que `function.name` cumpla
`^[a-zA-Z0-9_-]{1,64}$` (sin puntos ni espacios). Por eso se mantiene un mapeo:

    interno: dados.tirar  <->  api: dados_tirar

El registro genera el nombre API al registrar, valida el formato interno y
detecta colisiones (dos nombres internos que producirían el mismo nombre API).
"""

from __future__ import annotations

import re
from typing import Any

from dm_agent.herramientas.base import Herramienta, ResultadoHerramienta

# Nombre interno: segmentos seguros separados por puntos. P. ej. `dados.tirar`,
# `combate.iniciar_combate`, o un único segmento `dados_tirar`.
_REGEX_NOMBRE_INTERNO = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$")
# Nombre API válido para endpoints OpenAI-compatible.
_REGEX_NOMBRE_API = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class HerramientaNoRegistrada(KeyError):
    pass


class HerramientaYaRegistrada(ValueError):
    pass


class NombreHerramientaInvalido(ValueError):
    pass


class ColisionNombreApi(ValueError):
    pass


def nombre_interno_a_api(nombre: str) -> str:
    """Convierte un nombre interno (`dados.tirar`) a un nombre API seguro
    (`dados_tirar`). Lanza `NombreHerramientaInvalido` si el nombre interno
    no cumple el formato esperado o si el resultado no es válido para la API.
    """
    if not _REGEX_NOMBRE_INTERNO.match(nombre):
        raise NombreHerramientaInvalido(
            f"nombre interno inválido: {nombre!r} "
            "(se esperan segmentos [A-Za-z0-9_] separados por puntos)"
        )
    api = nombre.replace(".", "_")
    if not _REGEX_NOMBRE_API.match(api):
        raise NombreHerramientaInvalido(
            f"nombre API resultante inválido: {api!r} (límite 64 chars, [A-Za-z0-9_-])"
        )
    return api


class RegistroHerramientas:
    def __init__(self) -> None:
        self._herramientas: dict[str, Herramienta] = {}
        # nombre_api -> nombre_interno
        self._api_a_interno: dict[str, str] = {}

    def registrar(self, h: Herramienta) -> None:
        if h.nombre in self._herramientas:
            raise HerramientaYaRegistrada(h.nombre)
        api = nombre_interno_a_api(h.nombre)  # valida formato interno
        if api in self._api_a_interno:
            existente = self._api_a_interno[api]
            raise ColisionNombreApi(
                f"colisión de nombre API {api!r}: {h.nombre!r} y {existente!r} "
                "producen el mismo nombre para la API; renombra una de las dos"
            )
        self._herramientas[h.nombre] = h
        self._api_a_interno[api] = h.nombre

    def obtener(self, nombre: str) -> Herramienta:
        if nombre not in self._herramientas:
            raise HerramientaNoRegistrada(nombre)
        return self._herramientas[nombre]

    def nombre_api_a_interno(self, nombre_api: str) -> str:
        """Resuelve el nombre interno a partir del nombre API. Lanza
        `HerramientaNoRegistrada` si no hay ninguna herramienta con ese
        nombre API (el mapeo `_`→`.` no es reversible sin la tabla)."""
        if nombre_api not in self._api_a_interno:
            raise HerramientaNoRegistrada(nombre_api)
        return self._api_a_interno[nombre_api]

    def dispatch(self, nombre: str, ctx: Any, **args: Any) -> ResultadoHerramienta:
        h = self.obtener(nombre)
        ok, motivo = h.disponible(ctx)
        if not ok:
            return ResultadoHerramienta(ok=False, errores=[f"no disponible: {motivo}"])
        return h.ejecutar(ctx, **args)

    def dispatch_api(self, nombre_api: str, ctx: Any, **args: Any) -> ResultadoHerramienta:
        """Despacha usando el nombre API que envía el LLM (`dados_tirar`)."""
        interno = self.nombre_api_a_interno(nombre_api)
        return self.dispatch(interno, ctx, **args)

    def esquemas_disponibles(self, ctx: Any) -> list[dict]:
        salida: list[dict] = []
        for h in self._herramientas.values():
            ok, _ = h.disponible(ctx)
            if not ok:
                continue
            salida.append(
                {
                    "type": "function",
                    "function": {
                        "name": nombre_interno_a_api(h.nombre),
                        "description": h.descripcion,
                        "parameters": h.schema,
                    },
                }
            )
        return salida

    def __len__(self) -> int:
        return len(self._herramientas)

    def __contains__(self, nombre: object) -> bool:
        return nombre in self._herramientas
