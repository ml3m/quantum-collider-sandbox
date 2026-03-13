.PHONY: run lint install test test-cov format-check format prod-ready

run:
	PYTHONPATH=src python -m quantum_collider_sandbox

lint:
	PYTHONPATH=src pylint --fail-on=C,R,W src/quantum_collider_sandbox

install:
	pip install -e ".[dev]"

test:
	PYTHONPATH=src python -m pytest tests/ -v

test-cov:
	PYTHONPATH=src python -m pytest tests/ -v --cov=quantum_collider_sandbox --cov-report=term-missing

format-check:
	ruff check src/ tests/
	black --check src/ tests/

format:
	ruff check --fix src/ tests/
	black src/ tests/

prod-ready: format-check lint test-cov
