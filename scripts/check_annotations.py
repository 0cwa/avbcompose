"""Enforce a minimal public-function annotation policy before mypy integration."""

from __future__ import annotations

import ast
from pathlib import Path


def _missing_annotations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    failures: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if node.name.startswith("_"):
            continue
        if node.returns is None:
            failures.append(f"{path}:{node.lineno}: public function {node.name!r} lacks return type")
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        for argument in arguments:
            if argument.arg in {"self", "cls"}:
                continue
            if argument.annotation is None:
                failures.append(
                    f"{path}:{node.lineno}: argument {argument.arg!r} of {node.name!r} lacks type"
                )
        if node.args.vararg is not None and node.args.vararg.annotation is None:
            failures.append(f"{path}:{node.lineno}: *{node.args.vararg.arg} lacks type")
        if node.args.kwarg is not None and node.args.kwarg.annotation is None:
            failures.append(f"{path}:{node.lineno}: **{node.args.kwarg.arg} lacks type")

    return failures


def main() -> int:
    """Check public functions under ``src`` for explicit annotations."""

    failures: list[str] = []
    for path in sorted((Path.cwd() / "src").rglob("*.py")):
        failures.extend(_missing_annotations(path))

    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
