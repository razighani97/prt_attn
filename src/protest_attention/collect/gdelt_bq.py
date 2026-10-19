"""GDELT article volume via BigQuery (the second outcome measure).

The GDELT DOC API throttles this connection persistently (docs/data_audit.md),
so volume comes from the public GKG table instead. GKG has no full-text
field, so articles are matched on their URL, which for news sites almost
always carries a slug of the headline. That makes this a measure of articles
whose headline names the movement: narrower than keyword volume, and
independent of Wikipedia.

Every query is dry-run first and refused above MAX_GB scanned, so a mistake
cannot exhaust the free tier (1 TB/month).
"""

import json
import os
import re
import subprocess
from datetime import date, datetime, timezone

from dotenv import load_dotenv

from protest_attention.paths import RAW, ROOT

load_dotenv(ROOT / ".env")
TABLE = "gdelt-bq.gdeltv2.gkg_partitioned"
MAX_GB = 60

# Matched against the lowercased article URL. Slug words are separated by
# - _ / or . so boundaries are written explicitly.
B = r"(^|[/_.-])"
E = r"([/_.-]|$)"
PATTERNS = {
    "caa": rf"citizenship-?amendment|{B}(anti-?)?caa{E}|caa-?nrc",
    "farmers": r"farm(er)?s?-?(protest|law|bill|agitation|stir|union)|kisan-?andolan|farm-?laws",
    "neet": rf"{B}neet{E}|neet-?ug",
    "cec": rf"special-?intensive-?revision|{B}sir-?(exercise|process|drive|row){E}|anti-?cec"
           r"|chief-?election-?commissioner|gyanesh-?kumar",
}


def _bq(sql: str, dry_run: bool = False) -> str:
    project = os.environ["GCP_PROJECT"]
    cmd = ["bq", f"--project_id={project}", "query", "--use_legacy_sql=false",
           "--format=json", "--max_rows=100000"]
    if dry_run:
        cmd.append("--dry_run")
    return subprocess.run(cmd + [sql], check=True, capture_output=True, text=True).stdout


def scan_gb(sql: str) -> float:
    """Bytes the query would scan, from a dry run, in GB."""
    job = json.loads(_bq(sql, dry_run=True))
    return int(job["statistics"]["totalBytesProcessed"]) / 1e9


def daily_counts(pattern: str, start: date, end: date) -> tuple[list[dict], float]:
    sql = f"""
        select format_date('%Y-%m-%d', date(_PARTITIONTIME)) as day,
               count(distinct DocumentIdentifier) as articles
        from `{TABLE}`
        where _PARTITIONTIME between timestamp('{start}') and timestamp('{end}')
          and regexp_contains(lower(DocumentIdentifier), r'{pattern}')
        group by day order by day"""
    gb = scan_gb(sql)
    if gb > MAX_GB:
        raise RuntimeError(f"query would scan {gb:.0f} GB, above the {MAX_GB} GB guard")
    rows = json.loads(_bq(sql) or "[]")
    return [{"date": r["day"], "articles": int(r["articles"])} for r in rows], gb


def collect(project: str, key: str, start: date, end: date) -> dict:
    """Resumable: returns an existing raw file for the same request."""
    out = RAW / "gdelt_bq"
    out.mkdir(parents=True, exist_ok=True)
    for f in sorted(out.glob(f"{project}_{key}_*.json")):
        prior = json.loads(f.read_text())
        if (prior["pattern"], prior["start"], prior["end"]) == (
            PATTERNS[key], start.isoformat(), end.isoformat()
        ):
            return {**prior, "path": str(f)}
    points, gb = daily_counts(PATTERNS[key], start, end)
    record = {
        "project": project, "key": key, "pattern": PATTERNS[key], "table": TABLE,
        "start": start.isoformat(), "end": end.isoformat(), "gb_scanned": round(gb, 2),
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "points": points,
    }
    stamp = re.sub(r"[-:]", "", record["collected_at"])
    path = out / f"{project}_{key}_{stamp}.json"
    path.write_text(json.dumps(record, indent=1))
    return {**record, "path": str(path)}
