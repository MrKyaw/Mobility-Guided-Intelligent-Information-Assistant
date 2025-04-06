. PHONY: install test coverage demo check clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest

coverage:
	pytest --cov=mobility_guidance --cov-branch --cov-report=term-missing --cov-report=html

demo:
	python -m mobility_guidance --demo

check: coverage

clean:
	rm -rf .pytest_cache .coverage htmlcov coverage.xml build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
