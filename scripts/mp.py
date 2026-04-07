#!/usr/bin/env python3
"""MoviePilot CLI for the OpenClaw moviepilot skill.

On first use, run `configure` to bind a MoviePilot instance:
  mp.py configure --url URL (--api-token TOKEN | --username U --password P)

Auth is then read from config.json next to the skill. Two modes are supported:
  1. api_token  -> appended as ?token= on every request
  2. username/password -> POST /login/access-token, JWT cached in jwt.json

Other subcommands:
  status, search, subscribe-add, subscribe-list, subscribe-del,
  downloads, history, plugins, raw
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CFG_PATH = SKILL_DIR / "config.json"
JWT_PATH = SKILL_DIR / "jwt.json"


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


def request(method: str, path: str, params: dict | None = None, body: dict | None = None) -> object:
    cfg = _read_cfg()
    url = cfg["url"].rstrip("/")
    q = dict(params or {})
    headers = {"Accept": "application/json"}
    if cfg.get("api_token"):
        q["token"] = cfg["api_token"]
        retry_on_401 = False
    else:
        headers["Authorization"] = f"Bearer {_get_jwt(cfg)}"
        retry_on_401 = True

    def _do(hdrs):
        full = f"{url}/api/v1{path}?{urllib.parse.urlencode(q, doseq=True)}" if q else f"{url}/api/v1{path}"
        data = json.dumps(body).encode() if body is not None else None
        h = dict(hdrs)
        if data is not None:
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(full, method=method, data=data, headers=h)
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read()

    try:
        raw = _do(headers)
    except urllib.error.HTTPError as e:
        if e.code == 401 and retry_on_401:
            headers["Authorization"] = f"Bearer {_get_jwt(cfg, force=True)}"
            try:
                raw = _do(headers)
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


def out(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


# ---- commands ---------------------------------------------------------------

def cmd_configure(a):
    if not a.url:
        sys.exit("error: --url is required")
    url = a.url.rstrip("/")
    if a.api_token:
        cfg = {"url": url, "api_token": a.api_token}
        _save_cfg(cfg)
        # verify
        try:
            res = request("GET", "/dashboard/statistic")
        except SystemExit as e:
            CFG_PATH.unlink(missing_ok=True)
            raise
        out({"ok": True, "mode": "api_token", "url": url, "stats": res})
        return
    if a.username and a.password:
        # try login first, only save on success
        tok = _login(url, a.username, a.password)
        cfg = {"url": url, "username": a.username, "password": a.password}
        _save_cfg(cfg)
        try:
            res = request("GET", "/dashboard/statistic")
        except SystemExit:
            CFG_PATH.unlink(missing_ok=True)
            JWT_PATH.unlink(missing_ok=True)
            raise
        out({"ok": True, "mode": "username_password", "url": url, "stats": res})
        return
    sys.exit("error: provide either --api-token, or both --username and --password")


def cmd_status(a):
    if not CFG_PATH.exists():
        out({"configured": False})
        return
    cfg = json.loads(CFG_PATH.read_text())
    mode = "api_token" if cfg.get("api_token") else "username_password"
    try:
        res = request("GET", "/dashboard/statistic")
        out({"configured": True, "mode": mode, "url": cfg["url"], "reachable": True, "stats": res})
    except SystemExit as e:
        out({"configured": True, "mode": mode, "url": cfg["url"], "reachable": False, "error": str(e)})


def cmd_search(a):
    res = request("GET", "/media/search", {"title": a.query})
    if isinstance(res, list):
        if a.type:
            want = "电影" if a.type == "movie" else "电视剧"
            res = [r for r in res if r.get("type") == want]
        res = res[: a.limit]
        # trim to essentials
        slim = [
            {
                "tmdb_id": r.get("tmdb_id"),
                "type": r.get("type"),
                "title": r.get("title"),
                "year": r.get("year"),
                "original_title": r.get("original_title"),
                "vote": r.get("vote_average"),
                "overview": (r.get("overview") or "")[:160],
            }
            for r in res
        ]
        out(slim)
    else:
        out(res)


def cmd_subscribe_add(a):
    body = {
        "name": a.name or "",
        "tmdbid": int(a.tmdbid),
        "type": "电影" if a.type == "movie" else "电视剧",
    }
    if a.season is not None:
        body["season"] = a.season
    # MoviePilot needs name; if not provided, look it up.
    if not body["name"]:
        info = request("GET", f"/tmdb/{a.tmdbid}", {"type": body["type"]})
        if isinstance(info, dict):
            body["name"] = info.get("title") or info.get("name") or ""
            body.setdefault("year", info.get("year") or "")
            body.setdefault("poster", info.get("poster_path") or "")
    out(request("POST", "/subscribe/", body=body))


def cmd_subscribe_list(a):
    res = request("GET", "/subscribe/")
    if isinstance(res, list):
        slim = [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "year": r.get("year"),
                "type": r.get("type"),
                "season": r.get("season"),
                "tmdbid": r.get("tmdbid"),
                "vote": r.get("vote"),
                "state": r.get("state"),
            }
            for r in res
        ]
        out(slim)
    else:
        out(res)


def cmd_subscribe_del(a):
    out(request("DELETE", f"/subscribe/{a.id}"))


def cmd_downloads(a):
    res = request("GET", "/download/")
    if isinstance(res, list):
        slim = [
            {
                "title": r.get("title"),
                "name": r.get("name"),
                "season_episode": r.get("season_episode"),
                "progress": round(float(r.get("progress") or 0), 3),
                "state": r.get("state"),
                "dlspeed": r.get("dlspeed"),
                "upspeed": r.get("upspeed"),
                "size_mb": round((r.get("size") or 0) / 1024 / 1024, 1),
                "downloader": r.get("downloader"),
                "hash": r.get("hash"),
            }
            for r in res
        ]
        out(slim)
    else:
        out(res)


def cmd_history(a):
    res = request("GET", "/history/transfer", {"page": a.page, "count": a.count})
    if isinstance(res, dict) and "data" in res:
        items = (res.get("data") or {}).get("list") or []
        slim = [
            {
                "id": i.get("id"),
                "title": i.get("title"),
                "category": i.get("category"),
                "seasons": i.get("seasons"),
                "episodes": i.get("episodes"),
                "status": i.get("status"),
                "date": i.get("date"),
                "dest": i.get("dest"),
            }
            for i in items
        ]
        out({"total": (res.get("data") or {}).get("total"), "items": slim})
    else:
        out(res)


def cmd_plugins(a):
    out(request("GET", "/plugin/installed"))


def cmd_raw(a):
    body = json.loads(a.json) if a.json else None
    out(request(a.method.upper(), a.path, body=body))


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

    s = sub.add_parser("status", help="show current binding + reachability")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("search", help="search movies/tv")
    s.add_argument("query")
    s.add_argument("--type", choices=["movie", "tv"])
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("subscribe-add", help="add a subscription")
    s.add_argument("tmdbid")
    s.add_argument("--type", choices=["movie", "tv"], required=True)
    s.add_argument("--season", type=int)
    s.add_argument("--name")
    s.set_defaults(func=cmd_subscribe_add)

    s = sub.add_parser("subscribe-list", help="list subscriptions")
    s.set_defaults(func=cmd_subscribe_list)

    s = sub.add_parser("subscribe-del", help="delete a subscription")
    s.add_argument("id")
    s.set_defaults(func=cmd_subscribe_del)

    s = sub.add_parser("downloads", help="show active downloads")
    s.set_defaults(func=cmd_downloads)

    s = sub.add_parser("history", help="show transfer/library history")
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--count", type=int, default=20)
    s.set_defaults(func=cmd_history)

    s = sub.add_parser("plugins", help="list installed plugins")
    s.set_defaults(func=cmd_plugins)

    s = sub.add_parser("raw", help="raw API call")
    s.add_argument("method")
    s.add_argument("path")
    s.add_argument("--json")
    s.set_defaults(func=cmd_raw)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
