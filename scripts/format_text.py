"""Normalize simple text invariants without third-party dependencies."""

from __future__ import annotations

from pathlib import Path

from text_files import iter_text_files


def main() -> int:
    """Remove trailing whitespace and ensure one final newline."""

    for path in iter_text_files(Path.cwd()):
        text = path.read_text(encoding="utf-8")
        normalized = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
        if normalized != text:
            path.write_text(normalized, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
