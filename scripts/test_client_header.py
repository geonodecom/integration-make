#!/usr/bin/env python3
"""Every request the Make app sends names it as `X-Geonode-Client: make/<app version>` (scraper-api#674).

Make owns the User-Agent, so the app names itself in this header. Make app versions are majors,
which is all the API keeps. Run: python3 scripts/test_client_header.py
"""

from __future__ import annotations

import json
import pathlib
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((APP_ROOT / relative).read_text(encoding="utf-8-sig"))


class ClientHeaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.expected = f"make/{load('metadata.json')['version']}"

    def test_module_requests_carry_the_header(self) -> None:
        # base.imljson headers apply to every module request.
        self.assertEqual(load("base.imljson")["headers"]["X-Geonode-Client"], self.expected)

    def test_connection_check_carries_the_header(self) -> None:
        self.assertEqual(load("connections/api-key/api.imljson")["headers"]["X-Geonode-Client"], self.expected)

    def test_no_module_replaces_the_base_headers(self) -> None:
        for path in sorted((APP_ROOT / "modules").glob("*/api.imljson")):
            spec = json.loads(path.read_text(encoding="utf-8-sig"))
            for request in spec if isinstance(spec, list) else [spec]:
                self.assertNotIn("headers", request, f"{path.relative_to(APP_ROOT)} sets its own headers")


if __name__ == "__main__":
    unittest.main()
