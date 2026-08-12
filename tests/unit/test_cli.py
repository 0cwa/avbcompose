from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from avbcompose.cli.app import main


class CliTests(unittest.TestCase):
    def test_roadmap_command(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["roadmap"])
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().strip(), "https://github.com/0cwa/avbcompose/issues/1")

    def test_context_command(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["context"])
        self.assertEqual(result, 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["project"], "avbcompose")
        self.assertEqual(data["implementation_status"], "foundation-scaffold")


if __name__ == "__main__":
    unittest.main()
