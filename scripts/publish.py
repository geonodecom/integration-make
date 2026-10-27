#!/usr/bin/env python3
"""Publish the local app tree to Make.com via the Apps SDK REST API.

Idempotent — re-run any time to sync local edits up to Make. Uses only the
Python standard library; no extra installs.

Make appends a random suffix to the app name on creation (e.g. the configured
`scraper-api` becomes `scraper-api-5i531e`), so a GET on the configured name
404/403s on every later run. To avoid creating a new app each time, pass the
real (suffixed) name via --app-name. If you don't, the script discovers it by
listing the token's apps and matching on the configured name prefix; only when
no existing app is found does it create one.

Script parameters (command-line arguments):
    --token TOKEN        Required. Personal API token (Make -> Profile ->
                         API/MCP access -> Add token). Scopes required:
                         apps:read, apps:write.
    --app-name NAME      Optional. Overrides metadata.json::name. Pass the real
                         (Make-suffixed) name (e.g. scraper-api-5i531e) to update
                         an existing app in place.
    --app-version VER    Optional. Overrides metadata.json::version (default 1).
    --zone-url URL       Optional. Defaults to https://eu1.make.com.
    --team-id ID         Optional. Numeric team ID the app belongs to. Required
                         on zones that namespace SDK apps by team. Find it in
                         the URL of any Make page after `/team/{id}/...`.
    --user-agent UA      Optional. Override the User-Agent header. Make is
                         fronted by Cloudflare and blocks the default
                         Python-urllib UA with HTTP 403 (error 1010), so a
                         browser-like UA is sent by default.
    --dry-run            Optional. Prints the planned requests without
                         sending anything.
    --verbose            Optional. Prints request and response bodies.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ZONE = "https://eu1.make.com"
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; scraper-api-sdks/publish.py)"
PREVIEW_LIMIT = 1500

CONNECTION_SECTIONS = ("api", "common", "parameters", "scope", "scopes", "installSpec", "install", "uninstall")
MODULE_SECTIONS = ("api", "parameters", "expect", "interface", "samples", "scope", "epoch", "attach", "detach", "update")


class PublishError(RuntimeError):
    pass


# ---------- pure helpers ----------

def read_imljson(path: pathlib.Path) -> str:
    """Read a local .imljson/.json file, stripping any UTF-8 BOM (utf-8-sig) so the
    BOM is never uploaded to Make nor breaks json.loads / console printing."""
    return path.read_text(encoding="utf-8-sig")


def load_json(path: pathlib.Path) -> dict:
    return json.loads(read_imljson(path))


def is_trivially_empty(content: str) -> bool:
    return content.strip() in ("", "{}", "[]")


def to_api_name(dir_name: str) -> str:
    """kebab/snake -> camelCase, satisfying Make's IM005 (alphanumeric, alpha start, len >= 3)."""
    parts = [p for p in dir_name.replace("_", "-").split("-") if p]
    if not parts:
        raise PublishError(f"Cannot derive API name from empty directory name '{dir_name}'")
    name = parts[0].lower() + "".join(p[:1].upper() + p[1:].lower() for p in parts[1:])
    name = "".join(c for c in name if c.isalnum())
    if not name or not name[0].isalpha():
        name = "m" + name
    if len(name) < 3:
        name = name + "Mod"
    return name


def extract_name(response_text: str, *wrapper_keys: str, fallback: str) -> str:
    """Pull `name` from a JSON response, checking common wrapper keys then top-level."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return fallback
    if not isinstance(data, dict):
        return fallback
    for key in wrapper_keys:
        obj = data.get(key)
        if isinstance(obj, dict) and isinstance(obj.get("name"), str):
            return obj["name"]
    return data["name"] if isinstance(data.get("name"), str) else fallback


def parse_app_identity(response_text: str, fallback_name: str, fallback_version: str) -> tuple[str, str]:
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return fallback_name, fallback_version
    obj = data.get("app") if isinstance(data, dict) and isinstance(data.get("app"), dict) else data
    if not isinstance(obj, dict):
        return fallback_name, fallback_version
    name = obj.get("name") or fallback_name
    version = obj.get("latestVersion") or obj.get("version") or fallback_version
    return name, str(version)


def extract_list(response_text: str, *wrapper_keys: str) -> list:
    """Pull a list of records from a JSON response, checking wrapper keys then top-level."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in wrapper_keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def preview(text: str) -> str:
    return text if len(text) <= PREVIEW_LIMIT else text[:PREVIEW_LIMIT] + f"... [+{len(text) - PREVIEW_LIMIT} bytes]"


# ---------- HTTP client ----------

class MakeClient:
    def __init__(self, zone: str, token: str, user_agent: str, dry_run: bool, verbose: bool) -> None:
        self.base = zone.rstrip("/") + "/api/v2/sdk/apps"
        self.token = token
        self.user_agent = user_agent
        self.dry_run = dry_run
        self.verbose = verbose

    def request(self, method: str, path: str, *, body: object = None, content_type: str = "application/json") -> tuple[int, str]:
        url = self.base + path
        payload = self._encode_body(body)

        if self.verbose or self.dry_run:
            print(f"  -> {method} {url}")
            if payload and self.verbose:
                print(f"     body: {preview(payload.decode('utf-8', errors='replace'))}")

        if self.dry_run and method != "GET":
            return 200, ""

        req = urllib.request.Request(url, data=payload, method=method)
        req.add_header("Authorization", f"Token {self.token}")
        req.add_header("User-Agent", self.user_agent)
        req.add_header("Accept", "application/json")
        if payload is not None:
            req.add_header("Content-Type", content_type)

        try:
            with urllib.request.urlopen(req) as resp:
                status, text = resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            status, text = exc.code, exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise PublishError(f"Network error calling {method} {url}: {exc}") from exc

        if self.verbose:
            print(f"     <- {status}: {preview(text)}")
        return status, text

    @staticmethod
    def _encode_body(body: object) -> bytes | None:
        if body is None:
            return None
        if isinstance(body, (dict, list)):
            return json.dumps(body).encode("utf-8")
        if isinstance(body, str):
            return body.encode("utf-8")
        raise PublishError(f"Unsupported body type: {type(body).__name__}")

    def expect_ok(self, method: str, path: str, status: int, text: str, *, allow: tuple[int, ...] = ()) -> None:
        if 200 <= status < 300 or status in allow:
            return
        raise PublishError(f"{method} {path} -> HTTP {status}\n{text}")


# ---------- section upload (handles empty bodies, content-type quirks, path fallback) ----------

def upload_section(client: MakeClient, primary: str, content: str, *, fallback: str | None = None) -> None:
    paths = [p for p in (primary, fallback) if p]
    for i, path in enumerate(paths):
        status, text = client.request("PUT", path, body=content, content_type="application/jsonc")
        if status == 400 and "content-type" in text.lower():
            print("  jsonc rejected — retrying as application/json")
            status, text = client.request("PUT", path, body=content, content_type="application/json")
        if 200 <= status < 300:
            return
        next_path = paths[i + 1] if i + 1 < len(paths) else None
        if status == 404 and next_path:
            print(f"  {path} 404 — trying {next_path}")
            continue
        raise PublishError(f"PUT {path} -> HTTP {status}\n{text}")


def upload_dir_sections(client: MakeClient, directory: pathlib.Path, sections: tuple[str, ...], *, primary, fallback=None) -> None:
    for section in sections:
        file_path = directory / f"{section}.imljson"
        if not file_path.exists():
            continue
        content = read_imljson(file_path)
        if is_trivially_empty(content):
            print(f"  skip {section} (empty)")
            continue
        upload_section(client, primary(section), content, fallback=fallback(section) if fallback else None)
        print(f"  put {section}")


# ---------- ensure resources exist ----------

def ensure_app(client: MakeClient, metadata: dict, app_name: str, version: str, team_id: str | None) -> tuple[str, str]:
    print(f"[app] {app_name} v{version}")
    qs = f"?teamId={team_id}" if team_id else ""

    # 1. Try the given name directly. Pass the real (suffixed) name via --app-name
    #    to update in place without a listing round-trip.
    status, body = client.request("GET", f"/{app_name}/{version}{qs}")
    if 200 <= status < 300:
        _update_app(client, metadata, app_name, version, qs)
        return app_name, version
    if status not in (403, 404):
        client.expect_ok("GET", f"/{app_name}/{version}", status, body)

    # 2. Not directly accessible — discover the app Make actually created (it
    #    suffixes the name) by listing the token's apps and matching the prefix.
    found = _discover_existing(client, app_name, version, team_id)
    if found:
        rname, rversion = found
        vstatus, _ = client.request("GET", f"/{rname}/{rversion}{qs}")
        if 200 <= vstatus < 300:
            print(f"  found existing app '{rname}' v{rversion} — updating it")
            _update_app(client, metadata, rname, rversion, qs)
            return rname, rversion
        print(f"  matched '{rname}' in app list but GET returned HTTP {vstatus} — creating a new app")

    # 3. Nothing found — create.
    return _create_app(client, metadata, app_name, version, team_id, qs)


def _update_app(client: MakeClient, metadata: dict, app_name: str, version: str, qs: str) -> None:
    patch = {
        "label": metadata.get("label", app_name),
        "description": metadata.get("description", ""),
        "theme": metadata.get("theme", "#000000"),
    }
    status, text = client.request("PATCH", f"/{app_name}/{version}{qs}", body=patch)
    client.expect_ok("PATCH", f"/{app_name}/{version}", status, text)
    print(f"  metadata updated ({app_name} v{version})")


def _list_apps(client: MakeClient, team_id: str | None) -> list:
    qs = "?pg%5Blimit%5D=10000"
    if team_id:
        qs += f"&teamId={team_id}"
    status, body = client.request("GET", qs)
    if not (200 <= status < 300):
        print(f"  warning: could not list apps for discovery (HTTP {status})")
        return []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []
    apps = data.get("apps") if isinstance(data, dict) else data
    return apps if isinstance(apps, list) else []


def _discover_existing(client: MakeClient, base_name: str, version: str, team_id: str | None) -> tuple[str, str] | None:
    matches = [
        a for a in _list_apps(client, team_id)
        if isinstance(a, dict) and isinstance(a.get("name"), str)
        and (a["name"] == base_name or a["name"].startswith(base_name + "-"))
    ]
    if not matches:
        return None
    if len(matches) > 1:
        names = ", ".join(sorted(a["name"] for a in matches))
        print(f"  multiple apps match '{base_name}-*': {names}")
        print("  using the most recently created; delete stale duplicates in Make to avoid ambiguity")
    best = max(matches, key=lambda a: a.get("created") or "")
    resolved_version = best.get("latestVersion") or best.get("version") or version
    return best["name"], str(resolved_version)


def _create_app(client: MakeClient, metadata: dict, app_name: str, version: str, team_id: str | None, qs: str) -> tuple[str, str]:
    payload = {
        "name": app_name,
        "label": metadata.get("label", app_name),
        "description": metadata.get("description", ""),
        "theme": metadata.get("theme", "#000000"),
        "language": metadata.get("language", "en"),
        "countries": metadata.get("countries"),
        "private": metadata.get("private", True),
        "audience": metadata.get("audience", "global"),
    }
    if team_id:
        payload["teamId"] = int(team_id) if team_id.isdigit() else team_id

    status, text = client.request("POST", qs, body=payload)
    if status == 409:
        raise PublishError(
            f"App '{app_name}' exists but the token cannot read it (HTTP 409 on create after 403/404 on GET). "
            "Likely causes: (a) the token belongs to a different team — pass --team-id for the team that owns the app; "
            "(b) the token is missing apps:read / apps:write / app-development scopes."
        )
    client.expect_ok("POST", "/", status, text)

    resolved_name, resolved_version = parse_app_identity(text, app_name, version)
    if (resolved_name, resolved_version) != (app_name, version):
        print(f"  created (Make resolved this to {resolved_name} v{resolved_version})")
    else:
        print("  created")

    verify_status, verify_body = client.request("GET", f"/{resolved_name}/{resolved_version}{qs}")
    if not (200 <= verify_status < 300):
        raise PublishError(
            f"Created app but follow-up GET /{resolved_name}/{resolved_version} returned HTTP {verify_status}.\n"
            f"POST response: {text}\nGET response: {verify_body}\n"
            "Re-run with --verbose to see full payloads."
        )
    return resolved_name, resolved_version


def put_base(client: MakeClient, app_name: str, version: str, base_path: pathlib.Path) -> None:
    if not base_path.exists():
        print("[base] base.imljson missing — skipping")
        return
    print("[base] base.imljson")
    upload_section(client, f"/{app_name}/{version}/base", read_imljson(base_path))


def _discover_connection(client: MakeClient, app_name: str, api_name: str, expected_type: str, expected_label: str) -> str | None:
    """Make names SDK connections after the app, not the local dir (e.g. apiKey ->
    scraperApiProduction2), and suffixes them on each create. So we can't rely on
    the name; find an existing connection by listing the app's connections and
    matching on type/label (which we control) — with exact name as a shortcut."""
    status, body = client.request("GET", f"/{app_name}/connections")
    if not (200 <= status < 300):
        return None
    conns = [c for c in extract_list(body, "appConnections", "connections", "data")
             if isinstance(c, dict) and isinstance(c.get("name"), str)]
    if not conns:
        return None

    def names_where(predicate) -> list:
        return sorted({c["name"] for c in conns if predicate(c)})

    # Most-specific match first: same type AND label, then same type alone, then
    # exact name, then the name carrying the api_name token (older naming).
    for label, candidates in (
        (f"type '{expected_type}' + label '{expected_label}'",
         names_where(lambda c: c.get("type") == expected_type and c.get("label") == expected_label)),
        (f"type '{expected_type}'",
         names_where(lambda c: c.get("type") == expected_type)),
        ("exact name",
         names_where(lambda c: c["name"] == api_name)),
        (f"name containing '{api_name}'",
         names_where(lambda c: api_name in c["name"])),
    ):
        if not candidates:
            continue
        if len(candidates) > 1:
            print(f"  multiple connections match by {label}: {', '.join(candidates)}")
            print("  using the first; delete stale duplicates in Make to avoid ambiguity")
        return candidates[0]
    return None


def ensure_connection(client: MakeClient, app_name: str, conn_dir: pathlib.Path) -> str:
    meta = load_json(conn_dir / "metadata.json")
    local_name = conn_dir.name
    api_name = to_api_name(local_name)
    conn_type = meta.get("type", "basic")
    conn_label = meta.get("label", local_name)
    print(f"[connection] {local_name}")

    status, body = client.request("GET", f"/{app_name}/connections/{api_name}")
    if status == 404:
        discovered = _discover_connection(client, app_name, api_name, conn_type, conn_label)
        if discovered:
            print(f"  found existing connection '{discovered}' — reusing it")
            resolved = discovered
        else:
            payload = {"name": api_name, "label": conn_label, "type": conn_type}
            status, text = client.request("POST", f"/{app_name}/connections", body=payload)
            if status == 409:
                print("  already exists")
                resolved = api_name
            else:
                client.expect_ok("POST", f"/{app_name}/connections", status, text)
                resolved = extract_name(text, "appConnection", "connection", "data", fallback=api_name)
                print(f"  created as {resolved}")
    else:
        client.expect_ok("GET", f"/{app_name}/connections/{api_name}", status, body)
        resolved = extract_name(body, "appConnection", "connection", "data", fallback=api_name)

    upload_dir_sections(
        client, conn_dir, CONNECTION_SECTIONS,
        primary=lambda s: f"/connections/{resolved}/{s}",
        fallback=lambda s: f"/{app_name}/connections/{resolved}/{s}",
    )
    return resolved


def ensure_module(client: MakeClient, app_name: str, version: str, module_dir: pathlib.Path, connection_name: str | None) -> None:
    meta = load_json(module_dir / "metadata.json")
    local_name = module_dir.name
    api_name = to_api_name(local_name)
    suffix = f" -> {api_name}" if api_name != local_name else ""
    print(f"[module] {local_name}{suffix} (typeId {meta.get('typeId')})")

    status, body = client.request("GET", f"/{app_name}/{version}/modules/{api_name}")
    if status == 404:
        payload = {
            "name": api_name,
            "label": meta.get("label", local_name),
            "description": meta.get("description", ""),
            "typeId": meta["typeId"],
        }
        if "actionType" in meta:
            payload["actionType"] = meta["actionType"]
        if connection_name and meta.get("connection"):
            payload["connection"] = connection_name
        status, text = client.request("POST", f"/{app_name}/{version}/modules", body=payload)
        if status == 409:
            print("  already exists")
        else:
            client.expect_ok("POST", f"/{app_name}/{version}/modules", status, text)
            print("  created")
    else:
        client.expect_ok("GET", f"/{app_name}/{version}/modules/{api_name}", status, body)

    upload_dir_sections(
        client, module_dir, MODULE_SECTIONS,
        primary=lambda s: f"/{app_name}/{version}/modules/{api_name}/{s}",
        fallback=lambda s: f"/modules/{api_name}/{s}",
    )


# ---------- entrypoint ----------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="publish.py",
        description="Publish the local app tree to Make.com via the Apps SDK REST API.",
    )
    parser.add_argument(
        "--token", required=True,
        help="Required. Personal API token (Make -> Profile -> API/MCP access -> Add token). "
             "Scopes required: apps:read, apps:write.",
    )
    parser.add_argument(
        "--app-name",
        help="Overrides metadata.json::name. Pass the real (Make-suffixed) name "
             "e.g. scraper-api-5i531e to update an existing app in place; otherwise "
             "the app is discovered by listing and matching the configured name prefix.",
    )
    parser.add_argument("--app-version", help="Overrides metadata.json::version (default 1).")
    parser.add_argument("--zone-url", default=DEFAULT_ZONE, help=f"Defaults to {DEFAULT_ZONE}.")
    parser.add_argument(
        "--team-id",
        help="Numeric team ID the app belongs to. Required on zones that namespace SDK apps by "
             "team. Find it in the URL of any Make page after `/team/{id}/...`.",
    )
    parser.add_argument(
        "--user-agent", default=DEFAULT_USER_AGENT,
        help="Override the User-Agent header. Make is fronted by Cloudflare and blocks the default "
             "Python-urllib UA with HTTP 403 (error 1010), so a browser-like UA is sent by default.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the planned requests without sending anything.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print request and response bodies.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # Make output robust on Windows consoles (cp1252) — bodies and log lines may
    # contain a UTF-8 BOM, em dashes, etc. that would otherwise raise on print.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except ValueError:
                pass

    args = parse_args(argv)
    token = args.token

    metadata = load_json(REPO_ROOT / "metadata.json")
    app_name = args.app_name or metadata.get("name")
    if not app_name:
        print("App name missing — pass --app-name or add 'name' to metadata.json.", file=sys.stderr)
        return 2

    version = args.app_version or str(metadata.get("version", 1))
    zone = args.zone_url
    user_agent = args.user_agent
    team_id = args.team_id
    dry_run = args.dry_run
    verbose = args.verbose

    print(f"Target: {zone}  app={app_name}  version={version}  team={team_id or '-'}  dry_run={dry_run}")
    client = MakeClient(zone, token, user_agent=user_agent, dry_run=dry_run, verbose=verbose)

    try:
        resolved_name, resolved_version = ensure_app(client, metadata, app_name, version, team_id)
        put_base(client, resolved_name, resolved_version, REPO_ROOT / "base.imljson")

        connection_names: dict[str, str] = {}
        conn_root = REPO_ROOT / "connections"
        if conn_root.is_dir():
            for conn_dir in sorted(p for p in conn_root.iterdir() if p.is_dir()):
                connection_names[conn_dir.name] = ensure_connection(client, resolved_name, conn_dir)

        modules_root = REPO_ROOT / "modules"
        if modules_root.is_dir():
            for module_dir in sorted(p for p in modules_root.iterdir() if p.is_dir()):
                conn_ref = load_json(module_dir / "metadata.json").get("connection")
                resolved_conn = connection_names.get(conn_ref) if conn_ref else None
                ensure_module(client, resolved_name, resolved_version, module_dir, resolved_conn)
    except PublishError as exc:
        print(f"\nPublish failed: {exc}", file=sys.stderr)
        return 1

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
