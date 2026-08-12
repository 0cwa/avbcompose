"""Shared text-file discovery for the dependency-free foundation quality gate."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

_EXTENSIONS = {".json", ".md", ".py", ".sh", ".toml", ".yaml", ".yml"}
_EXCLUDED_PARTS = {".git", ".venv", "__pycache__"}


def iter_text_files(root: Path) -> Iterator[Path]:
    """Yield repository text files in deterministic path order."""

    candidates = (
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in _EXTENSIONS
        and not _EXCLUDED_PARTS.intersection(path.parts)
    )
    yield from sorted(candidates)
