PYTHON ?= python3
PIP ?= pip3

.PHONY: install lint test format

install:
	$(PIP) install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

test:
	$(PYTHON) -m pytest -vv --maxfail=1
