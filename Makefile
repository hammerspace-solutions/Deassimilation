.PHONY: test test-cov clean

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=html

clean:
	rm -rf .pytest_cache .coverage htmlcov
