.PHONY: ui install dev-install lint format typecheck test run

UI_DIR := src/electric_component_check/ui

ui:
	pyside6-uic $(UI_DIR)/form.ui -o $(UI_DIR)/form_ui.py
	pyside6-uic $(UI_DIR)/calibration.ui -o $(UI_DIR)/calibration_ui.py

install:
	pip install .

dev-install:
	pip install -e . --group dev

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src

test:
	pytest

run:
	python -m electric_component_check
