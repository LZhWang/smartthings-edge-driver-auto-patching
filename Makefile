PYTHON ?= python3
PIP ?= pip3
DOCKER ?= docker
COMPOSE ?= docker compose
IMAGE ?= edge-patcher-dev

.PHONY: install lint test format docker-build docker-shell docker-test

install:
	$(PIP) install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

test:
	$(PYTHON) -m pytest -vv --maxfail=1

docker-build:
	$(DOCKER) build -t $(IMAGE) .

docker-shell: docker-build
	$(COMPOSE) run --rm dev bash

docker-test: docker-build
	$(DOCKER) run --rm -v $(PWD):/workspace -w /workspace $(IMAGE) make lint test
