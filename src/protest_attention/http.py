"""Cached, logged, retrying HTTP for every collector.

Every response is cached on disk keyed by the request, so collectors can be
rerun freely while debugging without spending API quota. Every call, cached or
not, is logged with its parameters and status, which is the record of what was
asked for and what came back.
"""

import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

from protest_attention.paths import CACHE, ROOT

load_dotenv(ROOT / ".env")

# Statuses worth caching: a 404 from the pageviews API means "no data", which
# is a stable answer, not a transient failure.
CACHEABLE = {200, 404}
RETRYABLE = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 8
# Wikimedia throttles bursts (429, retry-after: 4) even well under its
# documented limits, so live calls to any one host are spaced out.
MIN_INTERVAL = 1.0
_last_call: dict[str, float] = {}


def _user_agent() -> str:
    contact = os.getenv("CONTACT_EMAIL")
    base = "protest-attention-research/0.1 (academic research"
    return f"{base}; {contact})" if contact else f"{base})"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    CACHE.mkdir(exist_ok=True)
    db = sqlite3.connect(CACHE / "http.sqlite")
    db.execute(
        """create table if not exists responses (
            key text primary key, url text, params text, status integer,
            body text, fetched_at text)"""
    )
    db.execute(
        """create table if not exists api_calls (
            called_at text, source text, url text, params text,
            status integer, from_cache integer)"""
    )
    return db


def _key(url: str, params: dict | None) -> str:
    canonical = json.dumps([url, sorted((params or {}).items())])
    return hashlib.sha256(canonical.encode()).hexdigest()


def _pace(url: str) -> None:
    """Keep live requests to one host at least MIN_INTERVAL seconds apart."""
    host = httpx.URL(url).host
    wait = _last_call.get(host, 0) + MIN_INTERVAL - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def _fetch(
    url: str, params: dict | None, db: sqlite3.Connection, source: str
) -> httpx.Response:
    """GET with pacing and retries. Every attempt, throttled or not, is logged."""
    params_json = json.dumps(params or {}, sort_keys=True)
    for attempt in range(MAX_ATTEMPTS):
        _pace(url)
        try:
            resp = httpx.get(
                url,
                params=params,
                headers={"User-Agent": _user_agent()},
                timeout=30,
                follow_redirects=True,
            )
        except httpx.TransportError:
            db.execute(
                "insert into api_calls values (?, ?, ?, ?, ?, ?)",
                (_now(), source, url, params_json, -1, 0),
            )
            time.sleep(2 ** attempt)
            continue
        if resp.status_code not in RETRYABLE:
            return resp
        db.execute(
            "insert into api_calls values (?, ?, ?, ?, ?, ?)",
            (_now(), source, url, params_json, resp.status_code, 0),
        )
        retry_after = resp.headers.get("retry-after", "")
        time.sleep(float(retry_after) if retry_after.isdigit() else 2 ** attempt)
    raise RuntimeError(f"gave up after {MAX_ATTEMPTS} attempts: {url} {params}")


def get_json(
    url: str, params: dict | None = None, *, source: str, refresh: bool = False
) -> tuple[int, dict | None]:
    """Return (status, parsed JSON or None). Uses the cache unless refresh."""
    key = _key(url, params)
    params_json = json.dumps(params or {}, sort_keys=True)
    with _connect() as db:
        row = None
        if not refresh:
            row = db.execute(
                "select status, body from responses where key = ?", (key,)
            ).fetchone()
        if row:
            status, body = row
            from_cache = 1
        else:
            resp = _fetch(url, params, db, source)
            status, body = resp.status_code, resp.text
            from_cache = 0
            if status in CACHEABLE:
                db.execute(
                    "insert or replace into responses values (?, ?, ?, ?, ?, ?)",
                    (key, url, params_json, status, body, _now()),
                )
        db.execute(
            "insert into api_calls values (?, ?, ?, ?, ?, ?)",
            (_now(), source, url, params_json, status, from_cache),
        )
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, None
