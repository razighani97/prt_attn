"""Candidate articles for crackdown coding (Project B, events/codebook.md).

Lists every article from the fixed source list in the coding window whose URL
or headline has both a coercion term and a topic term, plus a fixed random
sample of 50 topic-only articles to estimate what the keyword filter misses.
Then adds any new candidates to both coding sheets, never touching rows that
are already there.

Run: make sweep
"""

import csv
import hashlib
import html
import json
import random
import re
from datetime import date, datetime, timedelta, timezone

from protest_attention.collect.gdelt_bq import MAX_GB, _bq, scan_gb
from protest_attention.paths import RAW, ROOT

WINDOW_START = date(2026, 9, 23)
OUTLETS = {
    "thehindu.com": "The Hindu",
    "timesofindia.indiatimes.com": "Times of India",
    "hindustantimes.com": "Hindustan Times",
    "scroll.in": "Scroll",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
}
COERCION = (r"detain|detention|arrest|house.arrest|lathi|tear.gas|water.cannon|section.?144"
            r"|163.?bnss|prohibitory|curfew|internet|shutdown|crackdown|barricad"
            r"|metro.*(clos|shut)|banned|denied permission|police|fir\b|booked")
TOPIC = (r"protest|agitat|march|rally|bandh|dharna|gherao|cec\b|chief.election|gyanesh"
         r"|special.intensive|\bsir\b|election.commission|electoral.roll|voter")
RECALL_SAMPLE = 50
SEED = 20261019

SHEET_COLUMNS = [
    "candidate_id", "outlet", "first_seen", "title", "url", "recall_check",
    "relevant", "act_no", "event_date", "type", "city", "state", "scale",
    "anticipated", "protest_scheduled", "same_event_as", "notes",
]
SHEETS = {1: ROOT / "events" / "coding_pass1.csv", 2: ROOT / "events" / "coding_pass2.csv"}


def _query(start: date, end: date) -> str:
    domains = "|".join(re.escape(d) for d in OUTLETS)
    text = "lower(concat(url, ' ', ifnull(title, '')))"
    return f"""
        with docs as (
          select DocumentIdentifier as url,
                 any_value(regexp_extract(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>')) as title,
                 min(date(_PARTITIONTIME)) as first_seen
          from `gdelt-bq.gdeltv2.gkg_partitioned`
          where _PARTITIONTIME between timestamp('{start}') and timestamp('{end}')
            and regexp_contains(lower(DocumentIdentifier), r'^https?://(www\\.)?({domains})/')
          group by url
        )
        select url, title, format_date('%Y-%m-%d', first_seen) as first_seen,
               regexp_contains({text}, r'{COERCION}') as coercion,
               regexp_contains({text}, r'{TOPIC}') as topic
        from docs
        where regexp_contains({text}, r'{TOPIC}')"""


def _outlet(url: str) -> str:
    host = re.sub(r"^https?://(www\.)?", "", url.lower()).split("/")[0]
    return OUTLETS.get(host, host)


def _id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:8]


def collect(end: date) -> dict:
    sql = _query(WINDOW_START, end)
    gb = scan_gb(sql)
    if gb > MAX_GB:
        raise RuntimeError(f"query would scan {gb:.0f} GB, above the {MAX_GB} GB guard")
    rows = json.loads(_bq(sql) or "[]")
    both = [r for r in rows if r["coercion"] == "true"]
    topic_only = sorted((r for r in rows if r["coercion"] != "true"), key=lambda r: _id(r["url"]))
    recall = random.Random(SEED).sample(topic_only, min(RECALL_SAMPLE, len(topic_only)))
    record = {
        "window": [WINDOW_START.isoformat(), end.isoformat()], "gb_scanned": round(gb, 2),
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_topic": len(rows), "n_both": len(both), "n_topic_only": len(topic_only),
        "candidates": [
            {"candidate_id": _id(r["url"]), "outlet": _outlet(r["url"]),
             "first_seen": r["first_seen"], "title": html.unescape(r["title"] or ""),
             "url": r["url"], "recall_check": int(r in recall)}
            for r in both + recall
        ],
    }
    out = RAW / "sweep"
    out.mkdir(parents=True, exist_ok=True)
    stamp = re.sub(r"[-:]", "", record["collected_at"])
    (out / f"sweep_{end}_{stamp}.json").write_text(json.dumps(record, ensure_ascii=False))
    return record


def update_sheets(candidates: list[dict]) -> dict[int, int]:
    """Append new candidates to both sheets. Pass 1 in date order, pass 2 shuffled."""
    added = {}
    for n, path in SHEETS.items():
        existing, rows = set(), []
        if path.exists():
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            existing = {r["candidate_id"] for r in rows}
        new = [{**{c: "" for c in SHEET_COLUMNS}, **c, "act_no": "1"}
               for c in candidates if c["candidate_id"] not in existing]
        if n == 1:
            new.sort(key=lambda r: (r["first_seen"], r["outlet"], r["title"]))
        else:
            random.Random(SEED + len(existing)).shuffle(new)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
            w.writeheader()
            w.writerows(rows + new)
        added[n] = len(new)
    return added


def run(end: date | None = None) -> None:
    end = end or date.today() - timedelta(days=1)
    rec = collect(end)
    added = update_sheets(rec["candidates"])
    print(f"window {rec['window'][0]}..{rec['window'][1]}: {rec['n_topic']} topic articles, "
          f"{rec['n_both']} with a coercion term, recall sample {RECALL_SAMPLE}, "
          f"{rec['gb_scanned']} GB")
    print(f"added to pass 1: {added[1]}, pass 2: {added[2]}")


if __name__ == "__main__":
    run()
