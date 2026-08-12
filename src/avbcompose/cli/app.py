"""Foundation CLI.

The scaffold deliberately exposes only project-orientation commands. Android
composition commands are introduced by their owning roadmap issues.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from avbcompose import __version__

_REPOSITORY = "https://github.com/0cwa/avbcompose"
_ROADMAP = f"{_REPOSITORY}/issues/1"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="avbcompose",
        description="Security-first reproducible Android binary composition",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("roadmap", help="print the canonical roadmap URL")

    context = subparsers.add_parser("context", help="print machine-readable project context")
    context.add_argument("--pretty", action="store_true", help="indent the JSON output")

    return parser


def _context() -> dict[str, object]:
    return {
        "project": "avbcompose",
        "repository": _REPOSITORY,
        "roadmap": _ROADMAP,
        "agent_instructions": "AGENTS.md",
        "quality_gate": "./scripts/check.sh",
        "implementation_status": "foundation-scaffold",
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the foundation CLI and return a process exit code."""

    parser = _parser()
    args = parser.parse_args(argv)

    if args.command == "roadmap":
        print(_ROADMAP)
        return 0

    if args.command == "context":
        indent = 2 if args.pretty else None
        print(json.dumps(_context(), indent=indent, sort_keys=True))
        return 0

    parser.print_help()
    return 0
