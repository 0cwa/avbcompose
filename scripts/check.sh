#!/usr/bin/env bash
set -euo pipefail

uv sync --locked
export PYTHONPATH="${PWD}/src${PYTHONPATH:+:${PYTHONPATH}}"
uv run --locked python scripts/check_style.py
uv run --locked python -m compileall -q src tests scripts
uv run --locked python scripts/check_annotations.py
uv run --locked python -m unittest discover -s tests -p 'test_*.py' -v
