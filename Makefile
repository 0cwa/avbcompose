.PHONY: bootstrap check format lint typecheck test

bootstrap:
	./scripts/bootstrap.sh

check:
	./scripts/check.sh

format:
	PYTHONPATH=src uv run --locked python scripts/format_text.py

lint:
	PYTHONPATH=src uv run --locked python scripts/check_style.py
	PYTHONPATH=src uv run --locked python -m compileall -q src tests scripts

typecheck:
	PYTHONPATH=src uv run --locked python scripts/check_annotations.py

test:
	PYTHONPATH=src uv run --locked python -m unittest discover -s tests -p 'test_*.py' -v
