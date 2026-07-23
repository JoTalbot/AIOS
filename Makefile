.PHONY: help install test run dashboard demo clean docs docs-serve docs-pdf

help:
	@echo "AIOS Makefile"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make test        - Run all tests"
	@echo "  make run         - Run REST API"
	@echo "  make dashboard   - Run Web Dashboard"
	@echo "  make demo        - Run v4.1 demo"
	@echo "  make docs-serve  - Serve MkDocs site locally"
	@echo "  make docs        - Build MkDocs site"
	@echo "  make docs-pdf    - Build Sphinx PDF"
	@echo "  make clean       - Clean cache files"

install:
	pip install -r requirements.txt

test:
	python -m pytest -q

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
	rm -rf site/ docs/source/_build/
