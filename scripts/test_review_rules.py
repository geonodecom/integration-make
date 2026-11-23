#!/usr/bin/env python3
"""The app keeps the Make app review rules that a reviewer checks in the files.

Sentence-case labels, help text on every input, the standard Limit field, Make's pagination,
error messages and log sanitization. Run: python3 scripts/test_review_rules.py
"""

from __future__ import annotations

import json
import pathlib
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULES = APP_ROOT / "modules"
# Words that keep their capitals inside a label.
PROPER = {"API", "CSS", "DOM", "HTML", "HTTP", "ID", "JavaScript", "Markdown", "URL", "URLs", "XPath",
          "GET", "POST", "PUT", "PATCH", "DELETE", "String"}  # "Query String" is Make's universal module label.
LIMIT_HELP = ("Maximum number of results to return and work with during one execution cycle. "
              "For information about setting limits, see [our Help Center](https://help.make.com/types-of-modules#b3ZEQ).")


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def labels(node, found):
    if isinstance(node, dict):
        if isinstance(node.get("label"), str):
            found.append(node["label"])
        for key in ("spec", "options"):
            labels(node.get(key), found)
    elif isinstance(node, list):
        for item in node:
            labels(item, found)
    return found


class ReviewRulesTest(unittest.TestCase):
    def test_labels_are_sentence_case(self) -> None:
        files = sorted(MODULES.glob("*/expect.imljson")) + sorted(MODULES.glob("*/interface.imljson"))
        files.append(APP_ROOT / "connections/api-key/parameters.imljson")
        for path in files:
            for label in labels(load(path), []):
                for word in label.split()[1:]:
                    word = word.strip("()")
                    self.assertFalse(word[:1].isupper() and word not in PROPER, f"{path.relative_to(APP_ROOT)}: {label!r}")

    def test_every_input_has_help(self) -> None:
        for path in sorted(MODULES.glob("*/expect.imljson")) + [APP_ROOT / "connections/api-key/parameters.imljson"]:
            for field in load(path):
                help_text = field.get("help", "")
                self.assertTrue(help_text, f"{path.relative_to(APP_ROOT)}: {field['name']} has no help")
                for jargon in ("e.g.", "Does NOT", "UUID", "BFS", "Scraper API"):
                    self.assertNotIn(jargon, help_text, f"{path.relative_to(APP_ROOT)}: {field['name']}")

    def test_search_modules_have_the_standard_limit(self) -> None:
        for path in sorted(MODULES.glob("*/metadata.json")):
            if load(path)["typeId"] != 9:
                continue
            fields = load(path.with_name("expect.imljson"))
            limit = fields[-1]
            self.assertEqual((limit["name"], limit["label"], limit["type"], limit.get("default")), ("limit", "Limit", "uinteger", 10), path.parent.name)
            self.assertEqual(limit["help"], LIMIT_HELP, path.parent.name)
            self.assertEqual(load(path.with_name("api.imljson"))["response"]["limit"], "{{parameters.limit}}", path.parent.name)

    def test_removed_list_filters_are_not_offered(self) -> None:
        # The API answers 400 to a set `url` filter on job lists (and `query` on search).
        fields = {field["name"] for field in load(MODULES / "extract-list-jobs/expect.imljson")}
        self.assertNotIn("url", fields)
        self.assertNotIn("url", load(MODULES / "extract-list-jobs/api.imljson")["qs"])

    def test_job_list_uses_make_pagination(self) -> None:
        api = load(MODULES / "extract-list-jobs/api.imljson")
        self.assertEqual(api["pagination"], {"qs": {"page": "{{pagination.page}}"}, "condition": "{{body.page < body.page_count}}"})
        self.assertEqual(api["qs"]["page_size"], 100)

    def test_errors_show_the_api_message(self) -> None:
        message = load(APP_ROOT / "base.imljson")["response"]["error"]["message"]
        # A failed sync extraction wraps its error: {"error": {"code", "message"}, "tokens_charged"}.
        for path in ("body.error.message", "body.error.code", "body.message", "body.code", "body.detail[1].msg"):
            self.assertIn(path, message)

    def test_api_key_is_sanitized(self) -> None:
        for relative in ("base.imljson", "connections/api-key/api.imljson"):
            self.assertIn("request.headers.x-api-key", load(APP_ROOT / relative)["log"]["sanitize"], relative)


if __name__ == "__main__":
    unittest.main()
