#!/usr/bin/env python3
"""The app keeps the Make app review rules that a reviewer checks in the files.

Sentence-case labels, help text on every input, the standard Limit field, Make's pagination,
error messages and log sanitization. Run: python3 scripts/test_review_rules.py
"""

from __future__ import annotations

import json
import pathlib
import re
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


def module_files(name: str) -> list[pathlib.Path]:
    files = sorted(MODULES.glob(f"*/{name}"))
    assert len(files) >= 16, f"only {len(files)} modules/*/{name} files found"
    return files


class ReviewRulesTest(unittest.TestCase):
    def test_labels_are_sentence_case(self) -> None:
        files = module_files("expect.imljson") + module_files("interface.imljson") + module_files("metadata.json")
        files += [APP_ROOT / "connections/api-key/parameters.imljson", APP_ROOT / "metadata.json"]
        for path in files:
            found = labels(load(path), [])
            self.assertTrue(found, f"{path.relative_to(APP_ROOT)} has no labels")
            for label in found:
                for word in label.split()[1:]:
                    word = word.strip("()")
                    self.assertFalse(word[:1].isupper() and word not in PROPER, f"{path.relative_to(APP_ROOT)}: {label!r}")

    def test_every_input_has_help(self) -> None:
        for path in module_files("expect.imljson") + [APP_ROOT / "connections/api-key/parameters.imljson"]:
            for field in load(path):
                help_text = field.get("help", "")
                self.assertTrue(help_text, f"{path.relative_to(APP_ROOT)}: {field['name']} has no help")
                for jargon in ("e.g.", "Does NOT", "UUID", "BFS", "Scraper API"):
                    self.assertNotIn(jargon, help_text, f"{path.relative_to(APP_ROOT)}: {field['name']}")

    def test_search_modules_have_the_standard_limit(self) -> None:
        searches = [path for path in module_files("metadata.json") if load(path)["typeId"] == 9]
        self.assertEqual(len(searches), 2)
        for path in searches:
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

    def test_empty_dates_are_left_out(self) -> None:
        # The API answers 422 to `start_date=`, so an empty date must not be sent at all.
        for module in ("extract-list-jobs", "get-statistics"):
            qs = load(MODULES / module / "api.imljson")["qs"]
            for name in ("start_date", "end_date"):
                self.assertEqual(qs[name], f"{{{{if(parameters.{name}, formatDate(parameters.{name}, 'YYYY-MM-DDTHH:mm:ssZ', 'UTC'), undefined)}}}}", module)

    def test_errors_show_the_api_message(self) -> None:
        message = load(APP_ROOT / "base.imljson")["response"]["error"]["message"]
        # A failed sync extraction wraps its error: {"error": {"code", "message"}, "tokens_charged"}.
        for path in ("body.error.message", "body.error.code", "body.message", "body.code", "body.detail[1].msg"):
            self.assertIn(path, message)
        self.assertNotIn("'ERROR'", message)  # no made-up code when the API sends none

    def test_error_types_are_set_per_status(self) -> None:
        # Make wants `type` as one string; a type for one status goes under that status with its own message.
        expected = {
            "base.imljson": {"400": "DataError", "401": "InvalidAccessTokenError", "408": "ConnectionError", "422": "DataError"},
            "connections/api-key/api.imljson": {"401": "InvalidAccessTokenError", "403": "InvalidAccessTokenError"},
        }
        for relative, types in expected.items():
            error = load(APP_ROOT / relative)["response"]["error"]
            self.assertNotIn("type", error, relative)
            self.assertEqual({code: error[code]["type"] for code in types}, types, relative)
            for code in types:
                self.assertEqual(error[code]["message"], error["message"], f"{relative}: {code}")

    def test_job_ids_in_paths_are_checked(self) -> None:
        # A job ID goes into the URL path, so "../statistics" must not reach another route.
        def requests(path):  # api.imljson is one request or a list of them
            api = load(path)
            return api if isinstance(api, list) else [api]

        modules = [path.parent for path in module_files("api.imljson")
                   if any("{{parameters.job_id}}" in r.get("url", "") for r in requests(path))]
        self.assertEqual(len(modules), 5)
        for module in modules:
            job_id = next(f for f in load(module / "expect.imljson") if f["name"] == "job_id")
            pattern = re.compile(job_id["validate"]["pattern"])
            self.assertTrue(pattern.fullmatch("01a21393-fafa-75e6-a79a-df792e21ccab"), module.name)
            for bad in ("../statistics", "a/b", "a?b", "a#b", ""):
                self.assertIsNone(pattern.fullmatch(bad), f"{module.name}: {bad!r}")

    def test_api_key_is_sanitized(self) -> None:
        for relative in ("base.imljson", "connections/api-key/api.imljson"):
            self.assertIn("request.headers.x-api-key", load(APP_ROOT / relative)["log"]["sanitize"], relative)


if __name__ == "__main__":
    unittest.main()
