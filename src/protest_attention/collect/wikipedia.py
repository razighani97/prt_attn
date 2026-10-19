"""Wikipedia article resolution and daily pageviews.

Pageviews are counted per exact title, and redirects are counted separately,
so a renamed article loses traffic unless its redirects are summed back in.
This module resolves the canonical title, lists its redirects, reads its move
log and creation date, and collects /user/ agent pageviews for every title.
"""

import json
import re
from datetime import date, datetime, timezone
from urllib.parse import quote

from protest_attention.http import get_json
from protest_attention.paths import RAW

PAGEVIEWS = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "{project}/all-access/{agent}/{title}/daily/{start}/{end}"
)
# The pageviews API starts here; anything earlier is not "zero", it is unknown.
PAGEVIEWS_START = date(2015, 7, 1)


def _api(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def _query(lang: str, **params) -> dict:
    status, data = get_json(
        _api(lang),
        {"action": "query", "format": "json", "formatversion": 2, **params},
        source=f"mediawiki:{lang}",
    )
    if status != 200 or data is None:
        raise RuntimeError(f"MediaWiki {lang} query failed: {status} {params}")
    return data


def resolve(lang: str, title: str) -> dict:
    """Canonical title, page id and creation date, or {'missing': True}."""
    data = _query(
        lang,
        titles=title,
        redirects=1,
        prop="revisions",
        rvdir="newer",
        rvlimit=1,
        rvprop="timestamp",
    )
    page = data["query"]["pages"][0]
    if page.get("missing"):
        return {"lang": lang, "requested": title, "missing": True}
    return {
        "lang": lang,
        "requested": title,
        "canonical": page["title"],
        "pageid": page["pageid"],
        "created": page["revisions"][0]["timestamp"],
        "missing": False,
    }


def langlinks(lang: str, canonical: str, targets: tuple[str, ...]) -> dict[str, str]:
    """Titles of the equivalent article in other language editions."""
    data = _query(lang, titles=canonical, prop="langlinks", lllimit="max")
    links = data["query"]["pages"][0].get("langlinks", [])
    return {l["lang"]: l["title"] for l in links if l["lang"] in targets}


def search(lang: str, text: str, limit: int = 10) -> list[dict]:
    """Full-text search, for finding candidate articles. Not used for collection."""
    data = _query(lang, list="search", srsearch=text, srlimit=limit)
    return [{"title": r["title"], "words": r["wordcount"]} for r in data["query"]["search"]]


def redirects(lang: str, canonical: str) -> list[str]:
    """Every title that redirects to the canonical page."""
    titles, cont = [], {}
    while True:
        data = _query(
            lang, titles=canonical, prop="redirects", rdlimit="max", **cont
        )
        page = data["query"]["pages"][0]
        titles += [r["title"] for r in page.get("redirects", [])]
        if "continue" not in data:
            return titles
        cont = data["continue"]


def moves(lang: str, titles: list[str]) -> list[dict]:
    """Move-log entries for any of the given titles (the log sits on the old name)."""
    entries = []
    for t in titles:
        data = _query(lang, list="logevents", letype="move", letitle=t, lelimit=50)
        for e in data["query"]["logevents"]:
            entries.append(
                {
                    "from": e["title"],
                    "to": e.get("params", {}).get("target_title"),
                    "timestamp": e["timestamp"],
                }
            )
    return entries


def pageviews(
    lang: str, title: str, start: date, end: date, agent: str = "user"
) -> list[dict]:
    """Daily views for one exact title. Days with no views are absent."""
    url = PAGEVIEWS.format(
        project=f"{lang}.wikipedia",
        agent=agent,
        title=quote(title.replace(" ", "_"), safe=""),
        start=start.strftime("%Y%m%d"),
        end=end.strftime("%Y%m%d"),
    )
    status, data = get_json(url, source=f"pageviews:{lang}")
    if status == 404:
        return []
    if status != 200 or data is None:
        raise RuntimeError(f"pageviews failed for {lang}:{title}: {status}")
    return [
        {"date": f"{i['timestamp'][:4]}-{i['timestamp'][4:6]}-{i['timestamp'][6:8]}",
         "views": i["views"]}
        for i in data["items"]
    ]


def _slug(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")[:80]


def collect_article(
    project: str, lang: str, title: str, start: date, end: date, agent: str = "user"
) -> dict:
    """Resolve, expand redirects, and collect pageviews for every title.

    Writes one immutable raw JSON file and returns its contents. Reruns are
    cheap because every HTTP response is cached.
    """
    start = max(start, PAGEVIEWS_START)
    meta = resolve(lang, title)
    record = {
        "project": project,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent": agent,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "article": meta,
        "series": {},
    }
    if not meta["missing"]:
        all_titles = [meta["canonical"], *redirects(lang, meta["canonical"])]
        record["moves"] = moves(lang, all_titles)
        for t in all_titles:
            record["series"][t] = pageviews(lang, t, start, end, agent)

    out = RAW / "pageviews"
    out.mkdir(parents=True, exist_ok=True)
    stamp = record["collected_at"].replace(":", "").replace("-", "")
    # Page id keeps non-Latin titles (Hindi, Bengali) distinct after slugging.
    page = meta.get("pageid", "missing")
    path = out / f"{project}_{lang}_{agent}_{page}_{_slug(title)}_{stamp}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1))
    record["path"] = str(path)
    return record


def summed(record: dict) -> dict[str, int]:
    """Canonical plus redirects, summed by day."""
    totals: dict[str, int] = {}
    for points in record["series"].values():
        for p in points:
            totals[p["date"]] = totals.get(p["date"], 0) + p["views"]
    return dict(sorted(totals.items()))
