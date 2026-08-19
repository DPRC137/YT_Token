.PHONY: help install install-dev run test lint format clean

help:
	@echo "YT_Token - Quantitative Yield Token Valuation Suite"
	@echo "--------------------------------------------------"
	@echo "make install      : Install production dependencies"
	@echo "make install-dev  : Install development dependencies"
	@echo "make run          : Launch Streamlit web application"
	@echo "make test         : Run full test suite with pytest"
	@echo "make lint         : Run code quality linter (ruff & mypy)"
	@echo "make format       : Format code with ruff"
	@echo "make clean        : Remove build artifacts and caches"

install:
	pip install -r requirements.txt

install-dev:
	pip install -e ".[dev]"

run:
	streamlit run app.py

test:
	pytest -v --durations=10

lint:
	ruff check .
	mypy src

format:
	ruff format .

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
