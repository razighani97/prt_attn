"""GDELT DOC 2.0 article-volume timelines.

mode=timelinevolraw returns, per day, the number of matching articles
("value") and the total number of articles GDELT monitored that day ("norm").
Keeping both means volume can be reported as an absolute count or as a share
of all coverage, and a spike on a quiet news day can be told apart from a real
one.
"""

import json
import re
from datetime import date, datetime, timedelta, timezone

from protest_attention.http import get_json
from protest_attention.paths import RAW

DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
# Longest window requested in one call.
CHUNK_DAYS = 120


def scoped(query: str, scope: str) -> str:
    """Restrict a query to Indian sources, non-Indian sources, or all."""
    return {
        "india": f"{query} sourcecountry:IN",
        "abroad": f"{query} -sourcecountry:IN",
        "all": query,
    }[scope]


def _params(query: str, start: date, end: date) -> dict:
    return {
        "query": query,
        "mode": "timelinevolraw",
        "startdatetime": start.strftime("%Y%m%d000000"),
        "enddatetime": end.strftime("%Y%m%d235959"),
        "format": "json",
    }


def _chunks(start: date, end: date, days: int) -> list[tuple[date, date]]:
    out, cur = [], start
    while cur <= end:
        stop = min(end, cur + timedelta(days=days - 1))
        out.append((cur, stop))
        cur = stop + timedelta(days=1)
    return out


def timeline(query: str, start: date, end: date, chunk_days: int = CHUNK_DAYS) -> dict:
    """Daily matching-article counts and daily totals for one query.

    Long windows are requested in chunks: GDELT answers expensive queries
    (long windows, especially with -sourcecountry) with 429s that never clear.
    """
    points, resolutions = [], set()
    for a, b in _chunks(start, end, chunk_days):
        status, data = get_json(DOC_API, _params(query, a, b), source="gdelt:doc")
        if status != 200 or not data or "timeline" not in data:
            raise RuntimeError(f"GDELT query failed ({status}): {query} {a}..{b}")
        resolutions.add(data.get("query_details", {}).get("date_resolution"))
        points += data["timeline"][0]["data"] if data["timeline"] else []
    return {
        "params": _params(query, start, end),
        "chunk_days": chunk_days,
        "resolution": ",".join(sorted(r for r in resolutions if r)),
        "points": [
            {"date": f"{p['date'][:4]}-{p['date'][4:6]}-{p['date'][6:8]}",
             "articles": p["value"], "all_articles": p["norm"]}
            for p in points
        ],
    }


def collect(
    project: str, label: str, query: str, scope: str, start: date, end: date
) -> dict:
    """Collect one scoped timeline and write it as an immutable raw file.

    Resumable: if a raw file with identical query parameters already exists,
    it is returned instead of writing a duplicate.
    """
    out = RAW / "gdelt"
    for existing in sorted(out.glob(f"{project}_{label}_{scope}_*.json")):
        prior = json.loads(existing.read_text())
        if prior["params"]["query"] == scoped(query, scope) and prior["params"][
            "startdatetime"
        ] == start.strftime("%Y%m%d000000") and prior["params"][
            "enddatetime"
        ] == end.strftime("%Y%m%d235959"):
            return {**prior, "path": str(existing)}
    record = {
        "project": project,
        "label": label,
        "scope": scope,
        "base_query": query,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **timeline(scoped(query, scope), start, end),
    }
    out.mkdir(parents=True, exist_ok=True)
    stamp = re.sub(r"[-:]", "", record["collected_at"])
    path = out / f"{project}_{label}_{scope}_{stamp}.json"
    path.write_text(json.dumps(record, indent=1))
    record["path"] = str(path)
    return record
