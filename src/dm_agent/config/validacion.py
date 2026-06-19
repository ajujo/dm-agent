"""Validación offline de la configuración de modelos/perfiles/proyecto.

No realiza llamadas de red. Comprueba coherencia estructural entre
`config/modelos.json`, `config/perfiles.json` y `config/proyecto.json`.

La validación en vivo de los endpoints (resolver `/models`, comprobar que el
servidor responde) corresponde a Fase 2.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from urllib.parse import urlparse

_TIPO_ESPERADO = "openai-compatible"
_CLAVES_ENDPOINT_REQUERIDAS = ("base_url", "tipo", "backend")


def _host_es_local(host: str) -> bool:
    """Heurística: ¿el host parece local (no cloud)?"""
    if not host:
        return False
    host = host.lower()
    if host in {"localhost", "0.0.0.0", "::1"}:
        return True
    if host.endswith(".local") or host.endswith(".lan") or host.endswith(".home.arpa"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # No es una IP literal y no es un nombre local conocido -> parece cloud.
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local


def _endpoint_parece_cloud(endpoint: dict) -> bool:
    base_url = endpoint.get("base_url") or ""
    host = urlparse(base_url).hostname or ""
    return not _host_es_local(host)


def validar_config(modelos: dict, perfiles: dict, proyecto: dict) -> list[str]:
    """Valida los tres documentos de configuración ya cargados.

    Devuelve una lista de mensajes de error. Lista vacía = todo correcto.
    """
    errores: list[str] = []

    endpoints = modelos.get("endpoints")
    if not isinstance(endpoints, dict) or not endpoints:
        errores.append("modelos.json: falta 'endpoints' o está vacío")
        endpoints = {}

    perfiles_map = perfiles.get("perfiles")
    if not isinstance(perfiles_map, dict) or not perfiles_map:
        errores.append("perfiles.json: falta 'perfiles' o está vacío")
        perfiles_map = {}

    permitir_cloud = bool(proyecto.get("permitir_cloud", False))

    # --- Endpoints ---
    for nombre, ep in endpoints.items():
        if not isinstance(ep, dict):
            errores.append(f"endpoint '{nombre}': debe ser un objeto")
            continue
        for clave in _CLAVES_ENDPOINT_REQUERIDAS:
            if clave not in ep:
                errores.append(f"endpoint '{nombre}': falta '{clave}'")
        base_url = ep.get("base_url")
        if not (isinstance(base_url, str) and base_url.strip()):
            errores.append(f"endpoint '{nombre}': 'base_url' vacío o no es string")
        tipo = ep.get("tipo")
        if tipo is not None and tipo != _TIPO_ESPERADO:
            errores.append(
                f"endpoint '{nombre}': 'tipo' = {tipo!r}, se esperaba {_TIPO_ESPERADO!r}"
            )
        if (
            not permitir_cloud
            and not ep.get("desactivado", False)
            and _endpoint_parece_cloud(ep)
        ):
            errores.append(
                f"endpoint '{nombre}': parece cloud ({ep.get('base_url')!r}) "
                "pero 'permitir_cloud' es false y no está marcado 'desactivado': true"
            )

    # --- Perfiles ---
    for nombre, perfil in perfiles_map.items():
        if not isinstance(perfil, dict):
            errores.append(f"perfil '{nombre}': debe ser un objeto")
            continue
        ep_ref = perfil.get("endpoint")
        if not ep_ref:
            errores.append(f"perfil '{nombre}': falta 'endpoint'")
        elif ep_ref not in endpoints:
            errores.append(
                f"perfil '{nombre}': apunta a endpoint inexistente {ep_ref!r}"
            )

    # --- Proyecto ---
    por_defecto = proyecto.get("perfil_por_defecto")
    if not por_defecto:
        errores.append("proyecto.json: falta 'perfil_por_defecto'")
    elif por_defecto not in perfiles_map:
        errores.append(
            f"proyecto.json: 'perfil_por_defecto' = {por_defecto!r} no existe en perfiles"
        )

    return errores


def _cargar_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validar_directorio_config(config_dir: Path) -> list[str]:
    """Carga modelos/perfiles/proyecto desde `config_dir` y los valida.

    Devuelve una lista de errores (vacía = todo correcto). Errores de carga
    (fichero ausente o JSON inválido) se devuelven también como mensajes.
    """
    errores: list[str] = []
    docs: dict[str, dict] = {}
    for clave, fichero in (
        ("modelos", "modelos.json"),
        ("perfiles", "perfiles.json"),
        ("proyecto", "proyecto.json"),
    ):
        path = config_dir / fichero
        try:
            docs[clave] = _cargar_json(path)
        except FileNotFoundError:
            errores.append(f"no se encuentra {path}")
            docs[clave] = {}
        except json.JSONDecodeError as e:
            errores.append(f"{path}: JSON inválido ({e})")
            docs[clave] = {}

    errores.extend(validar_config(docs["modelos"], docs["perfiles"], docs["proyecto"]))
    return errores
