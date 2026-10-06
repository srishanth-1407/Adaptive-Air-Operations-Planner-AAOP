.PHONY: test generate lint clean

test:
	python -m pytest

generate:
	python -m generator.cli --config configs/small.yaml --output data/scenarios/run_001

lint:
	python -m ruff check .

clean:
	rm -rf data/scenarios/* __pycache__ .pytest_cache *.egg-info
