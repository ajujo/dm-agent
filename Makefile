.PHONY: help install test lint format check check-config clean

help:
	@echo "Targets: install | test | lint | format | check | check-config | clean"

install:
	@echo "Recuerda: conda activate rpg"
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check .

format:
	ruff format src tests scripts

check-config:
	python scripts/check_perfil.py

check: lint test check-config

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
