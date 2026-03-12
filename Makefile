.PHONY: run lint install test

run:
	PYTHONPATH=src python -m quantum_collider_sandbox

lint:
	PYTHONPATH=src pylint src/quantum_collider_sandbox

install:
	pip install -e ".[dev]"

test:
	PYTHONPATH=src python -m pytest tests/ -v
