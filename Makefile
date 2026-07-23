.PHONY: help install test test-cov quality typecheck run dashboard demo clean docs docs-serve docs-pdf lint security

help:
	@echo "AIOS Makefile"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make test        - Run all tests"
	@echo "  make test-cov    - Run tests with coverage report"
	@echo "  make quality     - Run automatic pre-commit quality checks"
	@echo "  make typecheck   - Run the manual mypy type-check gate"
	@echo "  make lint        - Lint all Python sources"
	@echo "  make security    - Scan for secrets"
	@echo "  make run         - Run REST API"
	@echo "  make dashboard   - Run Web Dashboard"
	@echo "  make demo        - Run v4.1 demo"
	@echo "  make docs-serve  - Serve MkDocs site locally"
	@echo "  make docs        - Build MkDocs site"
	@echo "  make docs-pdf    - Build Sphinx PDF"
	@echo "  make clean       - Clean cache and build files"

install:
	pip install -r requirements.txt

test:
	python -m pytest -q

test-cov:
	python -m pytest --cov=aios_core --cov-report=term --cov-report=html

quality:
	pre-commit run --all-files

typecheck:
	pre-commit run mypy --all-files --hook-stage manual

lint:
	python -m flake8 aios_core/ --max-line-length=100 --extend-ignore=E203,W503

security:
	python -m pip install --quiet gitleaks 2>/dev/null || true
	gitleaks detect --source . 2>/dev/null || echo "gitleaks not available — run 'brew install gitleaks'"

run:
	python run_rest_api.py

dashboard:
	python aios_cli.py dashboard

demo:
	python aios_cli.py demo

docs-serve:
	mkdocs serve

docs:
	mkdocs build

docs-pdf:
	cd docs/source && sphinx-build -b latex . _build/latex
	cd docs/source/_build/latex && make

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf site/ docs/source/_build/ build/ dist/ *.egg-info/
