"""Sanidad de los archivos de configuración bajo `config/`."""

import json
from pathlib import Path


def _cargar(raiz_proyecto: Path, nombre: str) -> dict:
    return json.loads((raiz_proyecto / "config" / nombre).read_text(encoding="utf-8"))


def test_proyecto_json_tiene_campos_clave(raiz_proyecto: Path):
    cfg = _cargar(raiz_proyecto, "proyecto.json")
    assert cfg["version"] == 1
    for c in ("nombre_proyecto", "perfil_por_defecto", "max_iter_turno", "rutas"):
        assert c in cfg


def test_modelos_json_define_endpoints(raiz_proyecto: Path):
    cfg = _cargar(raiz_proyecto, "modelos.json")
    assert "endpoints" in cfg and cfg["endpoints"]
    for nombre, ep in cfg["endpoints"].items():
        assert ep["tipo"] == "openai-compatible", f"{nombre} debe ser openai-compatible"
        assert ep["base_url"].startswith("http"), nombre


def test_perfiles_json_referencia_endpoints_validos(raiz_proyecto: Path):
    modelos = _cargar(raiz_proyecto, "modelos.json")
    perfiles = _cargar(raiz_proyecto, "perfiles.json")
    endpoints = set(modelos["endpoints"].keys())
    for nombre, perfil in perfiles["perfiles"].items():
        assert perfil["endpoint"] in endpoints, (
            f"perfil {nombre} apunta a endpoint inexistente {perfil['endpoint']}"
        )
