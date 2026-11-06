#!/usr/bin/env python3
"""publish.py never creates a Make app unless asked to, and a dry run never writes.

Runs against a fake Make API; nothing is sent over the network. Run: python3 scripts/test_publish_safety.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import publish  # noqa: E402

TOKEN = "fake-token-for-tests"


class FakeResponse:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc) -> None:
        return None


class FakeMake:
    """Answers by (method, path without the API prefix and query); records every request."""

    def __init__(self, routes: dict[tuple[str, str], tuple[int, object]], default: tuple[int, object] = (200, {})) -> None:
        self.routes = routes
        self.default = default
        self.calls: list[tuple[str, str]] = []

    def urlopen(self, req):
        path = req.full_url.split("/api/v2/sdk/apps", 1)[1].split("?", 1)[0]
        method = req.get_method()
        self.calls.append((method, path))
        status, body = self.routes.get((method, path), self.default)
        text = body if isinstance(body, str) else json.dumps(body)
        if status >= 400:
            raise urllib.error.HTTPError(req.full_url, status, "error", {}, io.BytesIO(text.encode("utf-8")))
        return FakeResponse(status, text)

    def writes(self) -> list[tuple[str, str]]:
        return [call for call in self.calls if call[0] != "GET"]


def clean_env(**values: str):
    env = {k: v for k, v in os.environ.items() if k not in (publish.DRY_RUN_ENV, publish.ALLOW_CREATE_ENV)}
    env.update(values)
    return mock.patch.dict(os.environ, env, clear=True)


def run(fake: FakeMake, fn, *args, **kwargs):
    out = io.StringIO()
    with mock.patch.object(publish.urllib.request, "urlopen", fake.urlopen), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        result = fn(*args, **kwargs)
    return result, out.getvalue()


METADATA = {"name": "scraper-api", "label": "Geonode", "description": "d", "theme": "#0d0c21"}
APP_MISSING = {("GET", "/scraper-api/1"): (404, {"message": "not found"}), ("GET", ""): (200, {"apps": []})}


class EnsureAppTest(unittest.TestCase):
    def client(self, dry_run: bool = False) -> publish.MakeClient:
        return publish.MakeClient("https://eu1.make.com", TOKEN, "test", dry_run=dry_run, verbose=False)

    def test_missing_app_stops_without_creating(self) -> None:
        fake = FakeMake(dict(APP_MISSING))
        with self.assertRaisesRegex(publish.PublishError, "without creating"):
            run(fake, publish.ensure_app, self.client(), METADATA, "scraper-api", "1", None)
        self.assertEqual(fake.writes(), [])

    def test_failed_app_list_stops_without_creating(self) -> None:
        fake = FakeMake({("GET", "/scraper-api/1"): (404, {}), ("GET", ""): (500, "oops")})
        with self.assertRaisesRegex(publish.PublishError, "Could not list apps"):
            run(fake, publish.ensure_app, self.client(), METADATA, "scraper-api", "1", None, allow_create=True)
        self.assertEqual(fake.writes(), [])

    def test_listed_but_unreadable_app_stops_without_creating(self) -> None:
        fake = FakeMake({
            ("GET", "/scraper-api/1"): (404, {}),
            ("GET", ""): (200, {"apps": [{"name": "scraper-api-abc123", "version": 1}]}),
            ("GET", "/scraper-api-abc123/1"): (403, {}),
        })
        with self.assertRaisesRegex(publish.PublishError, "without creating"):
            run(fake, publish.ensure_app, self.client(), METADATA, "scraper-api", "1", None, allow_create=True)
        self.assertEqual(fake.writes(), [])

    def test_create_only_with_opt_in(self) -> None:
        fake = FakeMake(dict(APP_MISSING))
        fake.routes[("POST", "")] = (200, {"app": {"name": "scraper-api-new1", "version": 1}})
        result, _ = run(fake, publish.ensure_app, self.client(), METADATA, "scraper-api", "1", None, allow_create=True)
        self.assertEqual(result, ("scraper-api-new1", "1"))
        self.assertEqual(fake.writes(), [("POST", "")])

    def test_existing_app_with_same_metadata_is_not_patched(self) -> None:
        fake = FakeMake({("GET", "/scraper-api/1"): (200, {"app": dict(METADATA)})})
        run(fake, publish.ensure_app, self.client(), METADATA, "scraper-api", "1", None)
        self.assertEqual(fake.writes(), [])


class MainTest(unittest.TestCase):
    ARGS = ["--token", TOKEN, "--app-name", "scraper-api", "--verbose"]

    def test_missing_app_fails_by_default(self) -> None:
        fake = FakeMake(dict(APP_MISSING))
        with clean_env():
            code, output = run(fake, publish.main, self.ARGS)
        self.assertEqual(code, 1)
        self.assertIn(publish.ALLOW_CREATE_ENV, output)
        self.assertEqual(fake.writes(), [])

    def test_dry_run_env_sends_only_reads(self) -> None:
        # Every resource but one module exists and differs, so a real run would PATCH, PUT and POST.
        fake = FakeMake({("GET", "/scraper-api/1/modules/makeApiCall"): (404, {"message": "Module not found"})})
        with clean_env(**{publish.DRY_RUN_ENV: "1"}):
            code, output = run(fake, publish.main, self.ARGS)
        self.assertEqual(code, 0)
        self.assertTrue(fake.calls)
        self.assertEqual(fake.writes(), [])
        self.assertIn("[dry run: not sent]", output)
        self.assertNotIn(TOKEN, output)
        # Nothing is reported as done when it was not sent.
        self.assertIn("metadata would be updated", output)
        self.assertIn("would be created", output)
        self.assertIn("would put api", output)
        for done in ("metadata updated", "  created", "  put ", "uploaded"):
            self.assertNotIn(done, output)
        self.assertIn("[review]", output)
        self.assertIn("would upload 512x512", output)

    def test_dry_run_never_creates_even_with_opt_in(self) -> None:
        fake = FakeMake(dict(APP_MISSING))
        with clean_env(**{publish.DRY_RUN_ENV: "true", publish.ALLOW_CREATE_ENV: "1"}):
            code, output = run(fake, publish.main, self.ARGS)
        self.assertEqual(code, 0)
        self.assertIn("would create app", output)
        self.assertEqual(fake.writes(), [])


def png_header(width: int, height: int) -> bytes:
    return publish.PNG_SIGNATURE + (13).to_bytes(4, "big") + b"IHDR" + width.to_bytes(4, "big") + height.to_bytes(4, "big")


class LogoAndReviewTest(unittest.TestCase):
    def client(self, dry_run: bool = False) -> publish.MakeClient:
        return publish.MakeClient("https://eu1.make.com", TOKEN, "test", dry_run=dry_run, verbose=True)

    def test_repo_logo_is_uploaded_as_png(self) -> None:
        fake = FakeMake({})
        _, output = run(fake, publish.put_logo, self.client(), "scraper-api", "1")
        self.assertEqual(fake.writes(), [("PUT", "/scraper-api/1/icon")])
        self.assertIn("uploaded 512x512", output)
        self.assertIn("bytes>", output)  # the PNG is not printed as text

    def test_bad_logo_is_refused_before_sending(self) -> None:
        tmp = pathlib.Path(__file__).with_name("_test_logo.png")
        try:
            for data, message in ((png_header(100, 100), "square PNG"), (png_header(512, 600), "square PNG"), (b"GIF89a", "not a PNG")):
                tmp.write_bytes(data)
                fake = FakeMake({})
                with self.assertRaisesRegex(publish.PublishError, message):
                    run(fake, publish.put_logo, self.client(), "scraper-api", "1", tmp)
                self.assertEqual(fake.writes(), [])
        finally:
            tmp.unlink(missing_ok=True)

    def test_missing_review_does_not_stop_the_run(self) -> None:
        fake = FakeMake({("GET", "/scraper-api/1/review"): (404, {"message": "not found"})})
        _, output = run(fake, publish.show_review, self.client(), "scraper-api", "1")
        self.assertIn("no review data (HTTP 404)", output)
        self.assertEqual(fake.writes(), [])


if __name__ == "__main__":
    unittest.main()
