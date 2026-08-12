"""Dependency-direction conformance checks for the source package graph.

The repository policy is deliberately small and dependency-free: it is a JSON
object with ``version == 1`` and a ``packages`` mapping whose values are the
allowed internal top-level package imports.  Imports within one package are
always allowed.

The scanner understands ordinary absolute and relative imports and tracks real
``importlib``/``builtins`` bindings for their dynamic import functions.  A
recognized dynamic import must use a literal module name.  Indirect helper
calls, subprocess behavior, and non-Python execution remain outside this
static scanner; issue #6 owns enforcement at the audited process boundary.

Diagram checks validate declared topology, roles, path geometry metadata, and
visible edge presentation metadata.  They do not claim to test pixel rendering.
"""

from __future__ import annotations

import ast
import json
import re
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REPOSITORY_ROOT = Path(__file__).parents[2]
_SOURCE_ROOT = _REPOSITORY_ROOT / "src" / "avbcompose"
_POLICY_PATH = _REPOSITORY_ROOT / "docs" / "architecture" / "dependency-policy.json"
_MERMAID_PATH = _REPOSITORY_ROOT / "docs" / "architecture" / "dependency-graph.mmd"
_SVG_PATH = _REPOSITORY_ROOT / "docs" / "architecture" / "dependency-graph.svg"
_PACKAGE_MAP_PATH = _REPOSITORY_ROOT / "docs" / "architecture" / "package-map.md"
_PACKAGE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_MERMAID_EDGE = re.compile(r"^([a-z][a-z0-9_]*)\s*-->\s*([a-z][a-z0-9_]*)$")
_MERMAID_NODE = re.compile(
    r'^([a-z][a-z0-9_]*)\["([a-z][a-z0-9_]*)<br/>([^"\r\n]+)"\]$'
)
_PACKAGE_CELL = re.compile(r"^`([a-z][a-z0-9_]*)`$")


class _PolicyError(ValueError):
    """Raised when the dependency policy cannot be trusted."""


class _SourceError(ValueError):
    """Raised when a source file cannot be scanned safely."""


class _DocumentationError(ValueError):
    """Raised when architecture documentation cannot be trusted."""


@dataclass(frozen=True)
class _ImportEdge:
    """One internal import discovered in a source file."""

    path: Path
    line: int
    source: str
    target: str


@dataclass(frozen=True)
class _DynamicImportBindings:
    """Names proven by import statements to bind Python import functions."""

    importlib_modules: frozenset[str]
    builtins_modules: frozenset[str]
    import_functions: frozenset[str]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _PolicyError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _discover_packages(package_root: Path) -> set[str]:
    """Return direct Python package directories below ``package_root``."""

    if not package_root.is_dir():
        raise _PolicyError(f"package root does not exist: {package_root}")

    packages = {
        path.name
        for path in package_root.iterdir()
        if path.is_dir() and (path / "__init__.py").is_file()
    }
    invalid = sorted(name for name in packages if _PACKAGE_NAME.fullmatch(name) is None)
    if invalid:
        raise _PolicyError(f"invalid source package name(s): {', '.join(invalid)}")
    return packages


def _load_policy(policy_path: Path, package_root: Path) -> dict[str, frozenset[str]]:
    """Load and validate the version-1 dependency policy."""

    try:
        raw = json.loads(
            policy_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except FileNotFoundError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, _PolicyError) as error:
        raise _PolicyError(f"{policy_path}: malformed JSON: {error}") from error

    if not isinstance(raw, dict):
        raise _PolicyError(f"{policy_path}: policy root must be an object")
    if set(raw) != {"version", "packages"}:
        unknown = sorted(set(raw) - {"version", "packages"})
        missing = sorted({"version", "packages"} - set(raw))
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unknown:
            details.append(f"unknown {', '.join(unknown)}")
        raise _PolicyError(f"{policy_path}: invalid policy shape ({'; '.join(details)})")
    if raw["version"] != 1 or isinstance(raw["version"], bool):
        raise _PolicyError(f"{policy_path}: unsupported policy version {raw['version']!r}")
    if not isinstance(raw["packages"], dict) or not raw["packages"]:
        raise _PolicyError(f"{policy_path}: packages must be a non-empty object")

    source_packages = _discover_packages(package_root)
    policy_packages = set(raw["packages"])
    invalid_policy_names = sorted(
        name
        for name in policy_packages
        if not isinstance(name, str) or _PACKAGE_NAME.fullmatch(name) is None
    )
    if invalid_policy_names:
        raise _PolicyError(
            f"{policy_path}: invalid policy package name(s): {', '.join(map(repr, invalid_policy_names))}"
        )
    if policy_packages != source_packages:
        missing = sorted(source_packages - policy_packages)
        extra = sorted(policy_packages - source_packages)
        details = []
        if missing:
            details.append(f"missing source package(s): {', '.join(missing)}")
        if extra:
            details.append(f"unknown policy package(s): {', '.join(extra)}")
        raise _PolicyError(f"{policy_path}: package completeness failure ({'; '.join(details)})")

    allowed: dict[str, frozenset[str]] = {}
    for package, imports in raw["packages"].items():
        if not isinstance(imports, list):
            raise _PolicyError(f"{policy_path}: allowlist for {package!r} must be an array")
        if any(not isinstance(item, str) or _PACKAGE_NAME.fullmatch(item) is None for item in imports):
            raise _PolicyError(f"{policy_path}: allowlist for {package!r} contains invalid package names")
        if len(imports) != len(set(imports)):
            raise _PolicyError(f"{policy_path}: allowlist for {package!r} contains duplicate entries")
        if package in imports:
            raise _PolicyError(
                f"{policy_path}: allowlist for {package!r} contains an explicit self-package entry; "
                "same-package imports are implicit"
            )
        unknown_imports = sorted(set(imports) - source_packages)
        if unknown_imports:
            raise _PolicyError(
                f"{policy_path}: {package!r} allows unknown package(s): {', '.join(unknown_imports)}"
            )
        allowed[package] = frozenset(imports)

    if "model" in allowed and allowed["model"]:
        raise _PolicyError(
            f"{policy_path}: ADR 0003 forbids model from importing internal packages: "
            f"{', '.join(sorted(allowed['model']))}"
        )
    cli_importers = sorted(package for package, imports in allowed.items() if "cli" in imports)
    if cli_importers:
        raise _PolicyError(
            f"{policy_path}: ADR 0003 forbids lower packages from importing cli: "
            f"{', '.join(cli_importers)}"
        )
    if "image" in allowed:
        image_extras = sorted(allowed["image"] - {"model"})
        if image_extras:
            raise _PolicyError(
                f"{policy_path}: ADR 0003 permits image to import only model; forbidden: "
                f"{', '.join(image_extras)}"
            )
    release_importers = sorted(
        package
        for package, imports in allowed.items()
        if "release" in imports and package not in {"cli", "release"}
    )
    if release_importers:
        raise _PolicyError(
            f"{policy_path}: ADR 0003 permits imports of release only from cli/release; "
            f"forbidden importer(s): {', '.join(release_importers)}"
        )
    return allowed


def _module_name(path: Path, package_root: Path) -> tuple[str, bool]:
    relative = path.relative_to(package_root).with_suffix("")
    parts = ("avbcompose", *relative.parts)
    is_package = path.name == "__init__.py"
    if is_package:
        parts = parts[:-1]
    return ".".join(parts), is_package


def _source_package(path: Path, package_root: Path) -> str | None:
    relative = path.relative_to(package_root)
    if len(relative.parts) < 2:
        return None
    return relative.parts[0]


def _relative_base(module_name: str, is_package: bool, level: int) -> list[str]:
    if level < 1:
        raise _SourceError(f"relative import has invalid level {level}")
    current = module_name.split(".")
    package = current if is_package else current[:-1]
    if level > len(package):
        raise _SourceError(f"relative import escapes package root from {module_name}")
    return package[: len(package) - level + 1]


def _dynamic_import_bindings(tree: ast.AST) -> _DynamicImportBindings:
    importlib_modules: set[str] = set()
    builtins_modules: set[str] = set()
    import_functions = {"__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound_name = alias.asname or alias.name.split(".", 1)[0]
                if alias.name == "importlib":
                    importlib_modules.add(bound_name)
                elif alias.name == "builtins":
                    builtins_modules.add(bound_name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            for alias in node.names:
                bound_name = alias.asname or alias.name
                if node.module == "importlib" and alias.name == "import_module":
                    import_functions.add(bound_name)
                elif node.module == "builtins" and alias.name == "__import__":
                    import_functions.add(bound_name)
    return _DynamicImportBindings(
        frozenset(importlib_modules),
        frozenset(builtins_modules),
        frozenset(import_functions),
    )


def _is_dynamic_import_call(node: ast.Call, bindings: _DynamicImportBindings) -> bool:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id in bindings.import_functions
    if not isinstance(function, ast.Attribute) or not isinstance(function.value, ast.Name):
        return False
    owner = function.value.id
    return (function.attr == "import_module" and owner in bindings.importlib_modules) or (
        function.attr == "__import__" and owner in bindings.builtins_modules
    )


def _dynamic_import_name(node: ast.Call) -> str:
    arguments = list(node.args[:1])
    arguments.extend(keyword.value for keyword in node.keywords if keyword.arg == "name")
    if len(arguments) != 1:
        raise _SourceError(
            f"line {node.lineno}: recognized dynamic import must provide exactly one module name"
        )
    argument = arguments[0]
    if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
        raise _SourceError(
            f"line {node.lineno}: recognized dynamic import requires a literal string module name"
        )
    if not argument.value or argument.value.startswith("."):
        raise _SourceError(
            f"line {node.lineno}: recognized dynamic import requires a non-relative module name"
        )
    return argument.value


def _import_targets(
    node: ast.AST,
    module_name: str,
    is_package: bool,
    bindings: _DynamicImportBindings,
) -> list[tuple[str, int]]:
    if isinstance(node, ast.Import):
        return [(alias.name, alias.lineno) for alias in node.names]

    if isinstance(node, ast.ImportFrom):
        if node.level:
            prefix = _relative_base(module_name, is_package, node.level)
            if node.module:
                prefix.extend(node.module.split("."))
        else:
            prefix = node.module.split(".") if node.module else []

        if node.module == "avbcompose" and not node.level:
            if any(alias.name == "*" for alias in node.names):
                raise _SourceError(
                    f"line {node.lineno}: ambiguous 'from avbcompose import *' is forbidden"
                )
            return [
                (".".join([*prefix, alias.name]), alias.lineno)
                for alias in node.names
                if _PACKAGE_NAME.fullmatch(alias.name) is not None
            ]
        if node.module:
            return [(".".join(prefix), node.lineno)]
        return [(".".join([*prefix, alias.name]), alias.lineno) for alias in node.names]

    if isinstance(node, ast.Call) and _is_dynamic_import_call(node, bindings):
        return [(_dynamic_import_name(node), node.lineno)]
    return []


def _internal_target(target: str, packages: set[str]) -> str | None:
    parts = target.split(".")
    if len(parts) < 2 or parts[0] != "avbcompose":
        return None
    package = parts[1]
    return package if package in packages else f"<unknown:{package}>"


def _scan_imports(package_root: Path, packages: set[str]) -> list[_ImportEdge]:
    """Scan Python imports and return only policy-relevant internal edges."""

    edges: list[_ImportEdge] = []
    for path in sorted(package_root.rglob("*.py")):
        source = _source_package(path, package_root)
        if source is None and path.name not in {"__init__.py", "__main__.py"}:
            raise _SourceError(
                f"{path}: unassigned avbcompose root module {path.name!r}; "
                "only __init__.py and __main__.py are permitted"
            )
        if source not in packages:
            if source is not None:
                raise _SourceError(f"{path}: source package {source!r} is not in the policy")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            module_name, is_package = _module_name(path, package_root)
            bindings = _dynamic_import_bindings(tree)
            nodes: list[ast.AST] = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
            nodes.extend(node for node in ast.walk(tree) if isinstance(node, ast.Call))
            for node in nodes:
                for target, line in _import_targets(node, module_name, is_package, bindings):
                    target_package = _internal_target(target, packages)
                    if target_package is None:
                        continue
                    if source is None:
                        allowed_root_target = path.name == "__main__.py" and target_package == "cli"
                        if not allowed_root_target:
                            raise _SourceError(
                                f"line {line}: root module {path.name} may import "
                                f"{'only cli' if path.name == '__main__.py' else 'no internal packages'}; "
                                f"found {target_package}"
                            )
                    elif source != target_package:
                        edges.append(_ImportEdge(path, line, source, target_package))
        except (OSError, UnicodeDecodeError, SyntaxError, _SourceError) as error:
            raise _SourceError(f"{path}: unable to scan imports: {error}") from error
    return edges


def _violations(
    edges: list[_ImportEdge], allowed: dict[str, frozenset[str]], policy_path: Path
) -> list[str]:
    diagnostics: list[str] = []
    for edge in edges:
        target = edge.target
        if target.startswith("<unknown:"):
            diagnostics.append(
                f"{edge.path}:{edge.line}: {edge.source} -> {target}; "
                f"import targets an unknown package (policy: {policy_path})"
            )
        elif target not in allowed[edge.source]:
            diagnostics.append(
                f"{edge.path}:{edge.line}: {edge.source} -> {target}; "
                f"internal dependency is not allowed (policy: {policy_path})"
            )
    return diagnostics


def _policy_edges(allowed: dict[str, frozenset[str]]) -> set[tuple[str, str]]:
    return {
        (source, target)
        for source, targets in allowed.items()
        for target in targets
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise _DocumentationError(f"{path}: unable to read UTF-8 text: {error}") from error


def _format_edges(edges: set[tuple[str, str]]) -> str:
    return ", ".join(f"{source} -> {target}" for source, target in sorted(edges))


def _parse_mermaid_edges(path: Path, packages: set[str]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for line_number, raw_line in enumerate(_read_text(path).splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("%%") or "-->" not in line:
            continue
        match = _MERMAID_EDGE.fullmatch(line)
        if match is None:
            raise _DocumentationError(
                f"{path}:{line_number}: malformed Mermaid edge; expected 'from --> to': {line!r}"
            )
        edge = match.group(1), match.group(2)
        unknown = sorted(set(edge) - packages)
        if unknown:
            raise _DocumentationError(
                f"{path}:{line_number}: Mermaid edge {_format_edges({edge})} "
                f"references unknown package(s): {', '.join(unknown)}"
            )
        if edge in edges:
            raise _DocumentationError(
                f"{path}:{line_number}: duplicate Mermaid edge metadata: {_format_edges({edge})}"
            )
        edges.add(edge)
    return edges


def _parse_mermaid_nodes(path: Path, packages: set[str]) -> dict[str, str]:
    nodes: dict[str, str] = {}
    for line_number, raw_line in enumerate(_read_text(path).splitlines(), start=1):
        line = raw_line.strip()
        if '["' not in line:
            continue
        match = _MERMAID_NODE.fullmatch(line)
        if match is None:
            raise _DocumentationError(
                f"{path}:{line_number}: malformed Mermaid node metadata: {line!r}"
            )
        identifier, package, role = match.groups()
        if identifier != package:
            raise _DocumentationError(
                f"{path}:{line_number}: Mermaid node id {identifier!r} "
                f"does not match package {package!r}"
            )
        if package not in packages:
            raise _DocumentationError(
                f"{path}:{line_number}: Mermaid node references unknown package {package!r}"
            )
        if package in nodes:
            raise _DocumentationError(
                f"{path}:{line_number}: duplicate Mermaid node metadata for {package!r}"
            )
        if not role.strip():
            raise _DocumentationError(f"{path}:{line_number}: Mermaid role for {package!r} is empty")
        nodes[package] = role.strip()
    return nodes


def _is_svg_edge_group(element: ElementTree.Element) -> bool:
    return "edge" in element.attrib.get("class", "").split()


def _parse_css_declarations(text: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for item in text.split(";"):
        if not item.strip():
            continue
        if ":" not in item:
            raise _DocumentationError(f"malformed SVG presentation declaration: {item.strip()!r}")
        name, value = item.split(":", 1)
        declarations[name.strip()] = value.strip()
    return declarations


def _edge_group_presentation(root: ElementTree.Element, group: ElementTree.Element) -> None:
    style_text = "\n".join(
        element.text or ""
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "style"
    )
    match = re.search(r"\.edge\s*\{([^}]*)\}", style_text, flags=re.DOTALL)
    presentation = _parse_css_declarations(match.group(1)) if match else {}
    if "style" in group.attrib:
        presentation.update(_parse_css_declarations(group.attrib["style"]))
    presentation.update(
        (name, value)
        for name, value in group.attrib.items()
        if name in {"display", "marker-end", "opacity", "stroke", "visibility"}
    )
    stroke = presentation.get("stroke", "").strip().lower()
    marker = presentation.get("marker-end", "").strip().lower()
    hidden = (
        stroke in {"", "none", "transparent"}
        or marker in {"", "none"}
        or presentation.get("display", "").strip().lower() == "none"
        or presentation.get("visibility", "").strip().lower() == "hidden"
        or presentation.get("opacity", "").strip() in {"0", "0.0"}
    )
    if hidden:
        raise _DocumentationError(
            "SVG class='edge' group lacks visible stroke/marker presentation metadata"
        )


def _parse_svg_edges(path: Path, packages: set[str]) -> set[tuple[str, str]]:
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as error:
        raise _DocumentationError(f"{path}: malformed SVG XML: {error}") from error

    edge_groups = [
        group
        for group in root.iter()
        if group.tag.rsplit("}", 1)[-1] == "g" and _is_svg_edge_group(group)
    ]
    if len(edge_groups) != 1:
        raise _DocumentationError(
            f"{path}: expected exactly one SVG class='edge' group; found {len(edge_groups)}"
        )
    edge_group = edge_groups[0]
    edge_paths = [
        child
        for child in edge_group.iter()
        if child.tag.rsplit("}", 1)[-1] == "path"
    ]
    if not edge_paths:
        raise _DocumentationError(f"{path}: no SVG edge paths found under a class='edge' group")

    edges: set[tuple[str, str]] = set()
    for index, edge_path in enumerate(edge_paths, start=1):
        source = edge_path.attrib.get("data-from")
        target = edge_path.attrib.get("data-to")
        if source is None or target is None:
            missing = [
                attribute
                for attribute, value in (("data-from", source), ("data-to", target))
                if value is None
            ]
            raise _DocumentationError(
                f"{path}: SVG edge path {index} missing metadata: {', '.join(missing)}"
            )
        if _PACKAGE_NAME.fullmatch(source) is None or _PACKAGE_NAME.fullmatch(target) is None:
            raise _DocumentationError(
                f"{path}: SVG edge path {index} has malformed metadata: {source!r} -> {target!r}"
            )
        if not edge_path.attrib.get("d", "").strip():
            raise _DocumentationError(f"{path}: SVG edge path {index} has empty path geometry")
        edge = source, target
        unknown = sorted(set(edge) - packages)
        if unknown:
            raise _DocumentationError(
                f"{path}: SVG edge path {index} {_format_edges({edge})} "
                f"references unknown package(s): {', '.join(unknown)}"
            )
        if edge in edges:
            raise _DocumentationError(
                f"{path}: SVG edge path {index} duplicates metadata: {_format_edges({edge})}"
            )
        edges.add(edge)
    try:
        _edge_group_presentation(root, edge_group)
    except _DocumentationError as error:
        raise _DocumentationError(f"{path}: {error}") from error
    return edges


def _parse_svg_nodes(path: Path, packages: set[str]) -> dict[str, str]:
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as error:
        raise _DocumentationError(f"{path}: malformed SVG XML: {error}") from error

    metadata_elements = [
        element
        for element in root.iter()
        if "data-package" in element.attrib or "data-role" in element.attrib
    ]
    visible_text: dict[int, list[ElementTree.Element]] = {
        id(element): [
            descendant
            for descendant in element.iter()
            if descendant is not element and descendant.tag.rsplit("}", 1)[-1] == "text"
        ]
        for element in metadata_elements
    }
    for parent in root.iter():
        children = list(parent)
        for index, element in enumerate(children):
            if element not in metadata_elements or visible_text[id(element)]:
                continue
            for sibling in children[index + 1 :]:
                if sibling in metadata_elements:
                    break
                if sibling.tag.rsplit("}", 1)[-1] == "text":
                    visible_text[id(element)].append(sibling)

    nodes: dict[str, str] = {}
    for element in metadata_elements:
        package = element.attrib.get("data-package")
        role = element.attrib.get("data-role")
        if package is None or role is None:
            raise _DocumentationError(
                f"{path}: SVG node metadata must include both data-package and data-role"
            )
        if _PACKAGE_NAME.fullmatch(package) is None or package not in packages:
            raise _DocumentationError(f"{path}: SVG node has invalid package {package!r}")
        if not role.strip():
            raise _DocumentationError(f"{path}: SVG role for {package!r} is empty")
        if package in nodes:
            raise _DocumentationError(f"{path}: duplicate SVG node metadata for {package!r}")

        labels: dict[str, list[str]] = {"label": [], "small": []}
        for text_element in visible_text[id(element)]:
            text = "".join(text_element.itertext()).strip()
            classes = text_element.attrib.get("class", "").split()
            for label_class in labels:
                if label_class in classes and text:
                    labels[label_class].append(text)
        if len(labels["label"]) != 1 or len(labels["small"]) != 1:
            raise _DocumentationError(
                f"{path}: SVG node {package!r} must have exactly one visible class='label' "
                f"package text and one class='small' role text; found "
                f"{len(labels['label'])} package and {len(labels['small'])} role labels"
            )
        visible_package = labels["label"][0]
        visible_role = labels["small"][0]
        if visible_package != package:
            raise _DocumentationError(
                f"{path}: SVG node {package!r} visible package text mismatch: "
                f"metadata {package!r}, visible {visible_package!r}"
            )
        if visible_role != role:
            raise _DocumentationError(
                f"{path}: SVG node {package!r} visible role text mismatch: "
                f"metadata {role!r}, visible {visible_role!r}"
            )
        nodes[package] = role.strip()
    return nodes


def _parse_allowed_imports(path: Path, line_number: int, cell: str) -> frozenset[str]:
    if cell == "none":
        return frozenset()
    parts = cell.split(", ")
    packages: list[str] = []
    for part in parts:
        match = _PACKAGE_CELL.fullmatch(part)
        if match is None:
            raise _DocumentationError(
                f"{path}:{line_number}: allowed-import cell must be 'none' or an explicit "
                f"sorted backticked package list: {cell!r}"
            )
        packages.append(match.group(1))
    if packages != sorted(packages):
        raise _DocumentationError(
            f"{path}:{line_number}: allowed-import packages are not sorted: {cell!r}"
        )
    if len(packages) != len(set(packages)):
        raise _DocumentationError(
            f"{path}:{line_number}: allowed-import cell contains duplicate packages: {cell!r}"
        )
    return frozenset(packages)


def _parse_package_map(path: Path) -> dict[str, frozenset[str]]:
    lines = _read_text(path).splitlines()
    heading = "## Package responsibilities and ownership"
    try:
        start = lines.index(heading) + 1
    except ValueError as error:
        raise _DocumentationError(f"{path}: missing {heading!r} section") from error

    packages: dict[str, frozenset[str]] = {}
    found_table = False
    for line_number, raw_line in enumerate(lines[start:], start=start + 1):
        line = raw_line.strip()
        if line.startswith("## "):
            break
        if not line.startswith("|"):
            continue
        found_table = True
        if line.startswith("| Package ") or re.fullmatch(r"\|[-|]+\|", line.replace(" ", "")):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) != 5:
            raise _DocumentationError(
                f"{path}:{line_number}: malformed package-map row; expected five columns"
            )
        match = _PACKAGE_CELL.fullmatch(cells[0])
        if match is None:
            raise _DocumentationError(
                f"{path}:{line_number}: malformed package-map row; expected backticked package name"
            )
        package = match.group(1)
        if package in packages:
            raise _DocumentationError(
                f"{path}:{line_number}: duplicate package-map row for {package!r}"
            )
        packages[package] = _parse_allowed_imports(path, line_number, cells[3])
    if not found_table or not packages:
        raise _DocumentationError(f"{path}: package responsibility table is missing or empty")
    return packages


def _edge_set_diagnostics(
    label: str, actual: set[tuple[str, str]], expected: set[tuple[str, str]]
) -> list[str]:
    diagnostics: list[str] = []
    missing = expected - actual
    extra = actual - expected
    if missing:
        diagnostics.append(f"{label} missing edge(s): {_format_edges(missing)}")
    if extra:
        diagnostics.append(f"{label} extra edge(s): {_format_edges(extra)}")
    return diagnostics


def _package_set_diagnostics(label: str, actual: set[str], expected: set[str]) -> list[str]:
    diagnostics: list[str] = []
    missing = expected - actual
    extra = actual - expected
    if missing:
        diagnostics.append(f"{label} missing package(s): {', '.join(sorted(missing))}")
    if extra:
        diagnostics.append(f"{label} extra package(s): {', '.join(sorted(extra))}")
    return diagnostics


def _role_diagnostics(
    label: str, actual: dict[str, str], expected: dict[str, str]
) -> list[str]:
    diagnostics = _package_set_diagnostics(label, set(actual), set(expected))
    for package in sorted(set(actual) & set(expected)):
        if actual[package] != expected[package]:
            diagnostics.append(
                f"{label} role mismatch for {package}: "
                f"expected {expected[package]!r}, found {actual[package]!r}"
            )
    return diagnostics


def _write_fixture(root: Path, files: dict[str, str]) -> Path:
    package_root = root / "avbcompose"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    for relative, contents in files.items():
        path = package_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    return package_root


def _write_policy(root: Path, packages: dict[str, list[str]]) -> Path:
    path = root / "dependency-policy.json"
    path.write_text(json.dumps({"version": 1, "packages": packages}), encoding="utf-8")
    return path


class DependencyDirectionTests(unittest.TestCase):
    def test_allowed_model_contract_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "model/__init__.py": "",
                    "source/__init__.py": "",
                    "source/adapter.py": "from avbcompose.model import Contract\n",
                    "source/relative.py": "from ..model import Contract\n",
                    "source/package_import.py": "from avbcompose import model\n",
                },
            )
            policy_path = _write_policy(root, {"model": [], "source": ["model"]})
            allowed = _load_policy(policy_path, package_root)
            diagnostics = _violations(_scan_imports(package_root, set(allowed)), allowed, policy_path)
            self.assertEqual(diagnostics, [])

    def test_image_backend_cannot_import_policy_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "image/__init__.py": "",
                    "image/backend.py": "from avbcompose.integration import PolicyCompiler\n",
                    "integration/__init__.py": "",
                },
            )
            policy_path = _write_policy(root, {"image": [], "integration": []})
            allowed = _load_policy(policy_path, package_root)
            diagnostics = _violations(_scan_imports(package_root, set(allowed)), allowed, policy_path)
            self.assertEqual(len(diagnostics), 1)
            self.assertIn("backend.py:1: image -> integration", diagnostics[0])

    def test_policy_cannot_override_adr_0003_major_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "cli/__init__.py": "",
                    "image/__init__.py": "",
                    "model/__init__.py": "",
                    "release/__init__.py": "",
                    "source/__init__.py": "",
                },
            )
            cases = [
                (
                    {"cli": [], "image": [], "model": ["source"], "release": [], "source": []},
                    "forbids model from importing",
                ),
                (
                    {"cli": [], "image": [], "model": [], "release": [], "source": ["cli"]},
                    "forbids lower packages from importing cli",
                ),
                (
                    {
                        "cli": [],
                        "image": ["model", "release"],
                        "model": [],
                        "release": [],
                        "source": [],
                    },
                    "permits image to import only model",
                ),
                (
                    {
                        "cli": [],
                        "image": [],
                        "model": [],
                        "release": [],
                        "source": ["release"],
                    },
                    "permits imports of release only from cli/release",
                ),
            ]
            for index, (packages, message) in enumerate(cases):
                with self.subTest(message=message):
                    policy_path = root / f"policy-{index}.json"
                    policy_path.write_text(
                        json.dumps({"version": 1, "packages": packages}),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(_PolicyError, message):
                        _load_policy(policy_path, package_root)

    def test_root_import_of_unknown_internal_package_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "model/__init__.py": "",
                    "source/__init__.py": "",
                    "source/adapter.py": (
                        "from avbcompose.model import Contract\n"
                        "from avbcompose import unknown_package\n"
                    ),
                },
            )
            policy_path = _write_policy(root, {"model": [], "source": ["model"]})
            allowed = _load_policy(policy_path, package_root)
            diagnostics = _violations(_scan_imports(package_root, set(allowed)), allowed, policy_path)
            self.assertEqual(len(diagnostics), 1)
            self.assertIn(
                "adapter.py:2: source -> <unknown:unknown_package>",
                diagnostics[0],
            )
            self.assertIn("import targets an unknown package", diagnostics[0])

    def test_build_and_artifact_producers_cannot_reach_release_signing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "build/__init__.py": "",
                    "build/producer.py": "from avbcompose.release import signer\n",
                    "artifacts/__init__.py": "",
                    "artifacts/normalizer.py": "from avbcompose.release import signer\n",
                    "release/__init__.py": "",
                },
            )
            policy_path = _write_policy(root, {"artifacts": [], "build": [], "release": []})
            allowed = _load_policy(policy_path, package_root)
            diagnostics = _violations(_scan_imports(package_root, set(allowed)), allowed, policy_path)
            self.assertEqual(len(diagnostics), 2)
            self.assertTrue(any("build/producer.py:1: build -> release" in item for item in diagnostics))
            self.assertTrue(any("artifacts/normalizer.py:1: artifacts -> release" in item for item in diagnostics))

    def test_lower_layer_cannot_import_cli_orchestrator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "model/__init__.py": "",
                    "model/types.py": "from avbcompose.cli import app\n",
                    "cli/__init__.py": "",
                },
            )
            policy_path = _write_policy(root, {"cli": [], "model": []})
            allowed = _load_policy(policy_path, package_root)
            diagnostics = _violations(_scan_imports(package_root, set(allowed)), allowed, policy_path)
            self.assertEqual(len(diagnostics), 1)
            self.assertIn("types.py:1: model -> cli", diagnostics[0])

    def test_literal_dynamic_import_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "image/__init__.py": "",
                    "image/backend.py": (
                        "import importlib\n"
                        "importlib.import_module('avbcompose.integration')\n"
                    ),
                    "integration/__init__.py": "",
                },
            )
            policy_path = _write_policy(root, {"image": [], "integration": []})
            allowed = _load_policy(policy_path, package_root)
            diagnostics = _violations(_scan_imports(package_root, set(allowed)), allowed, policy_path)
            self.assertEqual(len(diagnostics), 1)
            self.assertIn("backend.py:2: image -> integration", diagnostics[0])

    def test_dynamic_import_bindings_and_aliases_are_tracked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "model/__init__.py": "",
                    "source/__init__.py": "",
                    "source/adapter.py": (
                        "import importlib as loader\n"
                        "from importlib import import_module as load_module\n"
                        "import builtins\n"
                        "import builtins as builtin_alias\n"
                        "from builtins import __import__ as load_builtin\n"
                        "import helper\n"
                        "loader.import_module('avbcompose.model')\n"
                        "load_module('avbcompose.model')\n"
                        "builtins.__import__('avbcompose.model')\n"
                        "builtin_alias.__import__('avbcompose.model')\n"
                        "load_builtin('avbcompose.model')\n"
                        "__import__('avbcompose.model')\n"
                        "helper.import_module(runtime_module)\n"
                    ),
                },
            )
            policy_path = _write_policy(root, {"model": [], "source": ["model"]})
            allowed = _load_policy(policy_path, package_root)
            diagnostics = _violations(_scan_imports(package_root, set(allowed)), allowed, policy_path)
            self.assertEqual(diagnostics, [])

    def test_recognized_dynamic_import_rejects_nonliteral_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "model/__init__.py": "",
                    "source/__init__.py": "",
                    "source/adapter.py": (
                        "import importlib as loader\n"
                        "loader.import_module(runtime_module)\n"
                    ),
                },
            )
            with self.assertRaisesRegex(_SourceError, "literal string module name"):
                _scan_imports(package_root, {"model", "source"})

    def test_root_modules_are_explicitly_constrained(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "__main__.py": "from avbcompose.cli import app\n",
                    "cli/__init__.py": "",
                    "model/__init__.py": "",
                },
            )
            self.assertEqual(_scan_imports(package_root, {"cli", "model"}), [])

            (package_root / "helper.py").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(_SourceError, "unassigned avbcompose root module 'helper.py'"):
                _scan_imports(package_root, {"cli", "model"})

            (package_root / "helper.py").unlink()
            (package_root / "__init__.py").write_text(
                "from avbcompose.model import Contract\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(_SourceError, "__init__.py may import no internal packages"):
                _scan_imports(package_root, {"cli", "model"})

            (package_root / "__init__.py").write_text("", encoding="utf-8")
            (package_root / "__main__.py").write_text(
                "from avbcompose.model import Contract\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(_SourceError, "__main__.py may import only cli"):
                _scan_imports(package_root, {"cli", "model"})

    def test_ambiguous_root_package_star_import_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(
                root,
                {
                    "model/__init__.py": "",
                    "source/__init__.py": "",
                    "source/adapter.py": "from avbcompose import *\n",
                },
            )
            with self.assertRaisesRegex(_SourceError, "ambiguous 'from avbcompose import \\*'"):
                _scan_imports(package_root, {"model", "source"})

    def test_policy_must_be_complete_and_reject_unknown_allowlist_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(root, {"model/__init__.py": "", "source/__init__.py": ""})
            incomplete = _write_policy(root, {"model": []})
            with self.assertRaisesRegex(_PolicyError, "package completeness failure"):
                _load_policy(incomplete, package_root)

            unknown_target = _write_policy(root, {"model": ["missing"], "source": []})
            with self.assertRaisesRegex(_PolicyError, "allows unknown package"):
                _load_policy(unknown_target, package_root)

    def test_policy_rejects_duplicate_keys_and_unknown_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_root = _write_fixture(root, {"model/__init__.py": ""})
            duplicate = root / "duplicate.json"
            duplicate.write_text(
                '{"version": 1, "version": 1, "packages": {"model": []}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_PolicyError, "duplicate JSON object key"):
                _load_policy(duplicate, package_root)

            invalid_name = _write_policy(root, {"model": [], "Not-a-package": []})
            with self.assertRaisesRegex(_PolicyError, "invalid policy package name"):
                _load_policy(invalid_name, package_root)

            self_entry = _write_policy(root, {"model": ["model"]})
            with self.assertRaisesRegex(_PolicyError, "explicit self-package entry"):
                _load_policy(self_entry, package_root)

            unknown_shape = root / "unknown-shape.json"
            unknown_shape.write_text(
                json.dumps({"version": 1, "packages": {"model": []}, "layers": {}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_PolicyError, "unknown layers"):
                _load_policy(unknown_shape, package_root)

    def test_document_parsers_reject_malformed_and_duplicate_edge_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packages = {"model", "source"}

            malformed_mermaid = root / "malformed.mmd"
            malformed_mermaid.write_text("source --> model --> source\n", encoding="utf-8")
            with self.assertRaisesRegex(_DocumentationError, "malformed Mermaid edge"):
                _parse_mermaid_edges(malformed_mermaid, packages)

            duplicate_mermaid = root / "duplicate.mmd"
            duplicate_mermaid.write_text("source --> model\nsource --> model\n", encoding="utf-8")
            with self.assertRaisesRegex(_DocumentationError, "duplicate Mermaid edge metadata"):
                _parse_mermaid_edges(duplicate_mermaid, packages)

            missing_svg_metadata = root / "missing.svg"
            missing_svg_metadata.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><style>'
                '.edge { stroke:#000; marker-end:url(#arrow); }</style>'
                '<g class="edge"><path d="M0 0 L1 1"/></g></svg>\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_DocumentationError, "missing metadata"):
                _parse_svg_edges(missing_svg_metadata, packages)

            duplicate_svg = root / "duplicate.svg"
            duplicate_svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><style>'
                '.edge { stroke:#000; marker-end:url(#arrow); }</style><g class="edge">'
                '<path data-from="source" data-to="model" d="M0 0 L1 1"/>'
                '<path data-from="source" data-to="model" d="M1 1 L2 2"/>'
                "</g></svg>\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_DocumentationError, "duplicates metadata"):
                _parse_svg_edges(duplicate_svg, packages)

    def test_package_map_requires_exact_explicit_sorted_allowlists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_map = root / "package-map.md"
            prefix = (
                "## Package responsibilities and ownership\n\n"
                "| Package | One responsibility | Public-model owner | Allowed internal imports | Tracker / ADR |\n"
                "|---|---|---|---|---|\n"
            )
            package_map.write_text(
                prefix
                + "| `model` | contracts | `model` | none | ADR |\n"
                + "| `source` | sources | `model` | `model` | ADR |\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _parse_package_map(package_map),
                {"model": frozenset(), "source": frozenset({"model"})},
            )

            package_map.write_text(
                prefix + "| `source` | sources | `model` | all other packages | ADR |\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_DocumentationError, "explicit sorted backticked"):
                _parse_package_map(package_map)

            package_map.write_text(
                prefix + "| `source` | sources | `model` | `source`, `model` | ADR |\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_DocumentationError, "not sorted"):
                _parse_package_map(package_map)

    def test_diagram_node_and_svg_presentation_metadata_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packages = {"model", "source"}
            mermaid = root / "graph.mmd"
            mermaid.write_text(
                'model["model<br/>canonical contracts"]\n'
                'source["source<br/>source closure"]\n'
                "source --> model\n",
                encoding="utf-8",
            )
            expected_roles = {"model": "canonical contracts", "source": "source closure"}
            self.assertEqual(_parse_mermaid_nodes(mermaid, packages), expected_roles)

            mermaid.write_text(
                'model["model<br/>canonical contracts"]\n'
                'model["model<br/>duplicate"]\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_DocumentationError, "duplicate Mermaid node metadata"):
                _parse_mermaid_nodes(mermaid, packages)

            self.assertEqual(
                _package_set_diagnostics("Mermaid", {"model"}, packages),
                ["Mermaid missing package(s): source"],
            )
            self.assertEqual(
                _role_diagnostics(
                    "SVG",
                    {"model": "wrong role", "source": "source closure"},
                    expected_roles,
                ),
                ["SVG role mismatch for model: expected 'canonical contracts', found 'wrong role'"],
            )

            svg = root / "graph.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><style>'
                '.edge { stroke:#000; marker-end:url(#arrow); }</style>'
                '<g class="edge"><path data-from="source" data-to="model" '
                'd="M0 0 L1 1"/></g>'
                '<g data-package="model" data-role="canonical contracts">'
                '<text class="label">model</text>'
                '<text class="small">canonical contracts</text></g>'
                '<g data-package="source" data-role="source closure">'
                '<text class="label">source</text>'
                '<text class="small">source closure</text></g>'
                "</svg>\n",
                encoding="utf-8",
            )
            self.assertEqual(_parse_svg_edges(svg, packages), {("source", "model")})
            self.assertEqual(_parse_svg_nodes(svg, packages), expected_roles)

            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><style>'
                '.edge { stroke:#000; marker-end:url(#arrow); }</style>'
                '<g class="edge"><path data-from="source" data-to="model" d=""/></g></svg>\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_DocumentationError, "empty path geometry"):
                _parse_svg_edges(svg, packages)

            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><style>'
                '.edge { stroke:none; marker-end:none; }</style>'
                '<g class="edge"><path data-from="source" data-to="model" '
                'd="M0 0 L1 1"/></g></svg>\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_DocumentationError, "lacks visible stroke/marker"):
                _parse_svg_edges(svg, packages)

            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<g data-package="model" data-role="canonical contracts">'
                '<text class="label">model</text>'
                '<text class="small">canonical contracts</text></g>'
                '<g data-package="model" data-role="duplicate">'
                '<text class="label">model</text>'
                '<text class="small">duplicate</text></g></svg>\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(_DocumentationError, "duplicate SVG node metadata"):
                _parse_svg_nodes(svg, packages)

    def test_svg_visible_node_text_must_match_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            svg = Path(temporary) / "graph.svg"
            packages = {"model"}
            mutations = [
                (
                    "renamed-model",
                    "canonical contracts",
                    "visible package text mismatch.*metadata 'model', visible 'renamed-model'",
                ),
                (
                    "model",
                    "mutated visible role",
                    "visible role text mismatch.*metadata 'canonical contracts', "
                    "visible 'mutated visible role'",
                ),
            ]
            for visible_package, visible_role, message in mutations:
                with self.subTest(visible_package=visible_package, visible_role=visible_role):
                    svg.write_text(
                        '<svg xmlns="http://www.w3.org/2000/svg">'
                        '<g data-package="model" data-role="canonical contracts">'
                        f'<text class="label">{visible_package}</text>'
                        f'<text class="small">{visible_role}</text>'
                        "</g></svg>\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(_DocumentationError, message):
                        _parse_svg_nodes(svg, packages)

    def test_repository_policy_and_imports(self) -> None:
        try:
            allowed = _load_policy(_POLICY_PATH, _SOURCE_ROOT)
            edges = _scan_imports(_SOURCE_ROOT, set(allowed))
        except (FileNotFoundError, _PolicyError, _SourceError) as error:
            self.fail(str(error))
        diagnostics = _violations(edges, allowed, _POLICY_PATH)
        self.assertEqual(diagnostics, [], "\n".join(diagnostics))

    def test_repository_architecture_documents_match_policy(self) -> None:
        try:
            allowed = _load_policy(_POLICY_PATH, _SOURCE_ROOT)
            packages = set(allowed)
            expected_edges = _policy_edges(allowed)
            mermaid_edges = _parse_mermaid_edges(_MERMAID_PATH, packages)
            mermaid_nodes = _parse_mermaid_nodes(_MERMAID_PATH, packages)
            svg_edges = _parse_svg_edges(_SVG_PATH, packages)
            svg_nodes = _parse_svg_nodes(_SVG_PATH, packages)
            package_map = _parse_package_map(_PACKAGE_MAP_PATH)
        except (FileNotFoundError, _PolicyError, _DocumentationError) as error:
            self.fail(str(error))

        diagnostics = [
            *_edge_set_diagnostics(str(_MERMAID_PATH), mermaid_edges, expected_edges),
            *_edge_set_diagnostics(str(_SVG_PATH), svg_edges, expected_edges),
            *_package_set_diagnostics(str(_MERMAID_PATH), set(mermaid_nodes), packages),
            *_package_set_diagnostics(str(_SVG_PATH), set(svg_nodes), packages),
            *_role_diagnostics(str(_SVG_PATH), svg_nodes, mermaid_nodes),
            *_package_set_diagnostics(str(_PACKAGE_MAP_PATH), set(package_map), packages),
            *_edge_set_diagnostics(
                f"{_PACKAGE_MAP_PATH} allowed-import columns",
                _policy_edges(package_map),
                expected_edges,
            ),
        ]
        self.assertEqual(diagnostics, [], "\n".join(diagnostics))


if __name__ == "__main__":
    unittest.main()
