"""Tests de la validación offline de configuración (`dm_agent.config.validacion`)."""

import json

from dm_agent.config.validacion import validar_config, validar_directorio_config


def _config_valida():
    modelos = {
        "endpoints": {
            "local": {
                "base_url": "http://localhost:8000/v1",
                "tipo": "openai-compatible",
                "backend": "vllm",
            }
        }
    }
    perfiles = {"perfiles": {"rapido": {"endpoint": "local", "modelo": "X"}}}
    proyecto = {"perfil_por_defecto": "rapido", "permitir_cloud": False}
    return modelos, perfiles, proyecto


def test_config_valida_sin_errores():
    assert validar_config(*_config_valida()) == []


def test_perfil_apunta_a_endpoint_inexistente():
    modelos, perfiles, proyecto = _config_valida()
    perfiles["perfiles"]["rapido"]["endpoint"] = "fantasma"
    errores = validar_config(modelos, perfiles, proyecto)
    assert any("fantasma" in e for e in errores)


def test_endpoint_sin_clave_requerida():
    modelos, perfiles, proyecto = _config_valida()
    del modelos["endpoints"]["local"]["backend"]
    errores = validar_config(modelos, perfiles, proyecto)
    assert any("backend" in e for e in errores)


def test_tipo_distinto_de_openai_compatible():
    modelos, perfiles, proyecto = _config_valida()
    modelos["endpoints"]["local"]["tipo"] = "otro"
    errores = validar_config(modelos, perfiles, proyecto)
    assert any("tipo" in e for e in errores)


def test_perfil_por_defecto_inexistente():
    modelos, perfiles, proyecto = _config_valida()
    proyecto["perfil_por_defecto"] = "no_existe"
    errores = validar_config(modelos, perfiles, proyecto)
    assert any("perfil_por_defecto" in e for e in errores)


def test_base_url_vacia():
    modelos, perfiles, proyecto = _config_valida()
    modelos["endpoints"]["local"]["base_url"] = "  "
    errores = validar_config(modelos, perfiles, proyecto)
    assert any("base_url" in e for e in errores)


def test_endpoint_cloud_con_permitir_cloud_false_falla():
    modelos, perfiles, proyecto = _config_valida()
    modelos["endpoints"]["local"]["base_url"] = "https://api.openai.com/v1"
    errores = validar_config(modelos, perfiles, proyecto)
    assert any("cloud" in e for e in errores)


def test_endpoint_cloud_permitido_si_desactivado():
    modelos, perfiles, proyecto = _config_valida()
    modelos["endpoints"]["local"]["base_url"] = "https://api.openai.com/v1"
    modelos["endpoints"]["local"]["desactivado"] = True
    errores = validar_config(modelos, perfiles, proyecto)
    assert errores == []


def test_endpoint_cloud_permitido_si_permitir_cloud_true():
    modelos, perfiles, proyecto = _config_valida()
    modelos["endpoints"]["local"]["base_url"] = "https://api.openai.com/v1"
    proyecto["permitir_cloud"] = True
    errores = validar_config(modelos, perfiles, proyecto)
    assert errores == []


def test_host_privado_es_local():
    modelos, perfiles, proyecto = _config_valida()
    modelos["endpoints"]["local"]["base_url"] = "http://192.168.1.50:8000/v1"
    assert validar_config(modelos, perfiles, proyecto) == []


def test_validar_directorio_config_real():
    """La configuración real del repo debe validar sin errores."""
    from pathlib import Path

    config_dir = Path(__file__).resolve().parent.parent / "config"
    assert validar_directorio_config(config_dir) == []


def test_validar_directorio_config_fichero_ausente(tmp_path):
    errores = validar_directorio_config(tmp_path)
    assert any("modelos.json" in e for e in errores)


def test_validar_directorio_config_json_invalido(tmp_path):
    (tmp_path / "modelos.json").write_text("{ no es json", encoding="utf-8")
    (tmp_path / "perfiles.json").write_text(json.dumps({"perfiles": {}}), encoding="utf-8")
    (tmp_path / "proyecto.json").write_text(json.dumps({}), encoding="utf-8")
    errores = validar_directorio_config(tmp_path)
    assert any("JSON inválido" in e for e in errores)
