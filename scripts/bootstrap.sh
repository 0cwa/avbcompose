#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv 0.10.0 is required: https://docs.astral.sh/uv/" >&2
  exit 2
fi

uv sync --locked
