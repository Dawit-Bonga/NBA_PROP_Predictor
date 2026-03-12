from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class ApiContractTests(unittest.TestCase):
    def test_api_module_imports_when_dependency_available(self):
        try:
            import fastapi  # noqa: F401
        except ImportError:
            self.skipTest("fastapi is not installed in the current environment")

        import api

        self.assertEqual(api.app.title, "NBA Prop Predictor API")


if __name__ == "__main__":
    unittest.main()
