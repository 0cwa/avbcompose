"""Small dependency-free style checks used before issue #6 lands."""

from __future__ import annotations

from pathlib import Path

from text_files import iter_text_files


def main() -> int:
    """Check UTF-8, final newline, and trailing whitespace."""

    failures: list[str] = []
    for path in iter_text_files(Path.cwd()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(f"{path}: is not valid UTF-8")
            continue

        if text and not text.endswith("\n"):
            failures.append(f"{path}: missing final newline")

        for line_number, line in enumerate(text.splitlines(), start=1):
            if line != line.rstrip():
                failures.append(f"{path}:{line_number}: trailing whitespace")

    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
