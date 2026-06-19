"""Tests del cargador de skills."""

from pathlib import Path

import pytest

from dm_agent.skills.cargador import CargadorSkills, SkillInvalida


def test_descubre_skill_de_ejemplo(raiz_skills: Path):
    cargador = CargadorSkills(raiz_skills)
    skills = cargador.descubrir()
    assert "ejemplo-escena-social" in skills
    meta = skills["ejemplo-escena-social"]
    assert meta.nombre == "ejemplo-escena-social"
    assert meta.modo == "social"
    assert "dados.tirar" in meta.requiere_tools
    assert meta.cuerpo.startswith("# Cuándo usar")


def test_obtener_y_listar(raiz_skills: Path):
    cargador = CargadorSkills(raiz_skills)
    cargador.descubrir()
    assert any(m.slug == "ejemplo-escena-social" for m in cargador.listar())
    meta = cargador.obtener("ejemplo-escena-social")
    assert meta.version == "0.1.0"


def test_raiz_inexistente_no_revienta(tmp_path: Path):
    cargador = CargadorSkills(tmp_path / "no-existe")
    assert cargador.descubrir() == {}
    assert cargador.listar() == []


def test_skill_sin_frontmatter_es_invalida(tmp_path: Path):
    skill_dir = tmp_path / "mala"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# sin frontmatter\n", encoding="utf-8")
    with pytest.raises(SkillInvalida):
        CargadorSkills(tmp_path).descubrir()


def test_skill_sin_campo_requerido_es_invalida(tmp_path: Path):
    skill_dir = tmp_path / "incompleta"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: x\ndescription: y\nversion: 0.1.0\n---\nbody\n",
        encoding="utf-8",
    )
    with pytest.raises(SkillInvalida):
        CargadorSkills(tmp_path).descubrir()
