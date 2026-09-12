.PHONY: test coverage preflight

test:
	python -m pytest

coverage:
	python -m pytest --cov=dynacapa --cov-report=term-missing

preflight:
	python scripts/preflight_server.py

