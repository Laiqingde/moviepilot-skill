#!/usr/bin/env python3
"""MoviePilot MCP client for the OpenClaw moviepilot skill.

Talks to MoviePilot's built-in MCP endpoint (/api/v1/mcp/*), which exposes
40+ self-describing tools that mirror the official `moviepilot-cli` skill
shipped in jxxghp/MoviePilot. Compatible tool names: search_media,
add_subscribe, query_download_tasks, etc.

Subcommands:
  configure --url URL (--api-token TOKEN | --username U --password P)
  status                     show binding + reachability
  list                       list all MCP tools
  show <tool>                show tool description + input schema
  call <tool> [k=v ...]      invoke an MCP tool with arguments

Note: list/show/call require api_token (X-API-KEY). username/password
mode is supported only for status/configure — MCP needs an API key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CFG_PATH = SKILL_DIR / "config.json"
JWT_PATH = SKILL_DIR / "jwt.json"

# warn agent if a single tool result exceeds this many characters
LARGE_RESULT_WARN = 8000


# ---- config -----------------------------------------------------------------

def _read_cfg() -> dict:
    if not CFG_PATH.exists():
        sys.exit(
            "error: MoviePilot is not configured yet.\n"
            "Run: python3 " + str(Path(__file__)) + " configure "
            "--url <URL> (--api-token <TOKEN> | --username <U> --password <P>)"
        )
    return json.loads(CFG_PATH.read_text())


def _save_cfg(cfg: dict) -> None:
    CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    try:
        os.chmod(CFG_PATH, 0o600)
    except OSError:
        pass


def _login(url: str, username: str, password: str) -> str:
    body = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(
        f"{url}/api/v1/login/access-token",
        method="POST",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"login failed: HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    tok = data.get("access_token")
    if not tok:
        sys.exit(f"login failed: unexpected response {data}")
    JWT_PATH.write_text(json.dumps({"access_token": tok}))
    try:
        os.chmod(JWT_PATH, 0o600)
    except OSError:
        pass
    return tok


def _get_jwt(cfg: dict, force: bool = False) -> str:
    if not force and JWT_PATH.exists():
        try:
            return json.loads(JWT_PATH.read_text())["access_token"]
        except Exception:
            pass
    return _login(cfg["url"].rstrip("/"), cfg["username"], cfg["password"])


# ---- HTTP -------------------------------------------------------------------

def _http(method: str, full_url: str, headers: dict, body: bytes | None = None) -> bytes:
    req = urllib.request.Request(full_url, method=method, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _legacy_request(method: str, path: str, params: dict | None = None, body: dict | None = None):
    """For non-MCP endpoints (login, dashboard) used by status."""
    cfg = _read_cfg()
    url = cfg["url"].rstrip("/")
    q = dict(params or {})
    headers = {"Accept": "application/json"}
    if cfg.get("api_token"):
        q["token"] = cfg["api_token"]
        retry = False
    else:
        headers["Authorization"] = f"Bearer {_get_jwt(cfg)}"
        retry = True
    full = f"{url}/api/v1{path}?{urllib.parse.urlencode(q, doseq=True)}" if q else f"{url}/api/v1{path}"
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        raw = _http(method, full, headers, data)
    except urllib.error.HTTPError as e:
        if e.code == 401 and retry:
            headers["Authorization"] = f"Bearer {_get_jwt(cfg, force=True)}"
            try:
                raw = _http(method, full, headers, data)
            except urllib.error.HTTPError as e2:
                sys.exit(f"HTTP {e2.code}: {e2.read().decode(errors='replace')[:500]}")
        else:
            sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.decode(errors="replace")


def _mcp_request(method: str, sub_path: str, body: dict | None = None):
    """For MCP endpoints. Requires api_token (X-API-KEY)."""
    cfg = _read_cfg()
    if not cfg.get("api_token"):
        sys.exit(
            "error: MCP tools require an API key.\n"
            "Re-run: configure --url <URL> --api-token <TOKEN>\n"
            "(username/password mode does not work with /api/v1/mcp/*)"
        )
    url = cfg["url"].rstrip("/")
    full = f"{url}/api/v1/mcp{sub_path}"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": cfg["api_token"],
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    try:
        raw = _http(method, full, headers, data)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.decode(errors="replace")


# ---- output -----------------------------------------------------------------

def out(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


# ---- commands ---------------------------------------------------------------

def cmd_configure(a):
    if not a.url:
        sys.exit("error: --url is required")
    url = a.url.rstrip("/")
    if a.api_token:
        _save_cfg({"url": url, "api_token": a.api_token})
        try:
            tools = _mcp_request("GET", "/tools")
        except SystemExit:
            CFG_PATH.unlink(missing_ok=True)
            raise
        out({
            "ok": True,
            "mode": "api_token",
            "url": url,
            "mcp_tools_count": len(tools) if isinstance(tools, list) else None,
            "mcp_supported": True,
        })
        return
    if a.username and a.password:
        _login(url, a.username, a.password)
        _save_cfg({"url": url, "username": a.username, "password": a.password})
        try:
            res = _legacy_request("GET", "/dashboard/statistic")
        except SystemExit:
            CFG_PATH.unlink(missing_ok=True)
            JWT_PATH.unlink(missing_ok=True)
            raise
        out({
            "ok": True,
            "mode": "username_password",
            "url": url,
            "stats": res,
            "mcp_supported": False,
            "warning": "MCP tools (list/show/call) need an API key. Re-configure with --api-token to enable them.",
        })
        return
    sys.exit("error: provide either --api-token, or both --username and --password")


def cmd_status(a):
    if not CFG_PATH.exists():
        out({"configured": False})
        return
    cfg = json.loads(CFG_PATH.read_text())
    mode = "api_token" if cfg.get("api_token") else "username_password"
    info = {"configured": True, "mode": mode, "url": cfg["url"]}
    try:
        if mode == "api_token":
            tools = _mcp_request("GET", "/tools")
            info["reachable"] = True
            info["mcp_tools_count"] = len(tools) if isinstance(tools, list) else None
        else:
            stats = _legacy_request("GET", "/dashboard/statistic")
            info["reachable"] = True
            info["stats"] = stats
            info["mcp_supported"] = False
    except SystemExit as e:
        info["reachable"] = False
        info["error"] = str(e)
    out(info)


def cmd_list(a):
    tools = _mcp_request("GET", "/tools")
    if not isinstance(tools, list):
        out(tools)
        return
    # group by category by name prefix when possible; otherwise just list
    slim = [
        {
            "name": t.get("name"),
            "description": (t.get("description") or "").split(".")[0][:140],
        }
        for t in tools
    ]
    if a.keyword:
        kw = a.keyword.lower()
        slim = [
            t for t in slim
            if kw in (t["name"] or "").lower() or kw in (t["description"] or "").lower()
        ]
    out({"total": len(slim), "tools": slim})


def cmd_show(a):
    tool = _mcp_request("GET", f"/tools/{a.name}")
    if isinstance(tool, dict):
        # strip noise
        schema = tool.get("inputSchema") or {}
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        params = []
        for pname, pdef in props.items():
            params.append({
                "name": pname,
                "required": pname in required,
                "type": pdef.get("type"),
                "description": (pdef.get("description") or "")[:200],
                "enum": pdef.get("enum"),
                "default": pdef.get("default"),
            })
        out({
            "name": tool.get("name"),
            "description": tool.get("description"),
            "parameters": params,
        })
    else:
        out(tool)


def _coerce(value: str):
    """Coerce 'k=v' string into JSON-typed value: int, float, bool, json, or str."""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.lower() in ("null", "none"):
        return None
    # JSON literal (object/array/quoted)
    if value and value[0] in "{[\"":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    # number
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    return value


def cmd_call(a):
    args = {}
    for kv in a.kv:
        if "=" not in kv:
            sys.exit(f"error: arg '{kv}' is not key=value")
        k, v = kv.split("=", 1)
        args[k] = _coerce(v)
    # always provide an explanation if not given (some MCP tools require it)
    args.setdefault("explanation", f"openclaw moviepilot skill: {a.name}")

    body = {"tool_name": a.name, "arguments": args}
    res = _mcp_request("POST", "/tools/call", body=body)

    # MCP returns {success, result} where result may be a JSON-encoded string
    if isinstance(res, dict) and "result" in res:
        result = res["result"]
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                pass
        rendered = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        if len(rendered) > LARGE_RESULT_WARN:
            sys.stderr.write(
                f"# token-warning: tool '{a.name}' returned {len(rendered)} chars "
                f"(~{len(rendered)//2} tokens). Consider narrower filters.\n"
            )
        print(rendered)
        if not res.get("success", True):
            sys.exit(2)
    else:
        out(res)


# ---- argparse ---------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(prog="mp")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("configure", help="bind a MoviePilot instance")
    s.add_argument("--url", required=True)
    s.add_argument("--api-token", dest="api_token")
    s.add_argument("--username")
    s.add_argument("--password")
    s.set_defaults(func=cmd_configure)

    s = sub.add_parser("status", help="show binding + reachability")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("list", help="list all MCP tools")
    s.add_argument("--keyword", help="substring filter on name/description")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="show a tool's parameter schema")
    s.add_argument("name")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("call", help="invoke an MCP tool")
    s.add_argument("name")
    s.add_argument("kv", nargs="*", help="key=value arguments")
    s.set_defaults(func=cmd_call)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
