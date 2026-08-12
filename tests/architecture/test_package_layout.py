from __future__ import annotations

import unittest
from pathlib import Path

EXPECTED_PACKAGES = {
    "artifacts",
    "baseline",
    "build",
    "cli",
    "compatibility",
    "contribution",
    "graph",
    "image",
    "integration",
    "model",
    "plan",
    "release",
    "source",
    "update",
}


class PackageLayoutTests(unittest.TestCase):
    def test_expected_subsystems_exist(self) -> None:
        package_root = Path(__file__).parents[2] / "src" / "avbcompose"
        actual = {
            path.name
            for path in package_root.iterdir()
            if path.is_dir() and (path / "__init__.py").is_file()
        }
        self.assertEqual(actual, EXPECTED_PACKAGES)

    def test_no_legacy_feature_specific_core_packages(self) -> None:
        package_root = Path(__file__).parents[2] / "src" / "avbcompose"
        forbidden = {"bcr", "custota", "msd", "oemunlockonboot", "alterinstaller"}
        names = {path.name.lower() for path in package_root.iterdir()}
        self.assertTrue(forbidden.isdisjoint(names))


if __name__ == "__main__":
    unittest.main()
