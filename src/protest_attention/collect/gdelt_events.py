"""GDELT event counts for India via BigQuery: protest activity, and coercion
as a machine-coded cross-check on the hand-coded crackdown list.

Replaces ACLED, which does not offer API access at the free tier. GDELT
events are machine-coded from news reports (CAMEO codes), so they are noisier
than ACLED: duplicates, misplaced locations, and coverage that follows the
news cycle. They serve Project B as a control for protest activity and as a
check on the event list, never as the event list itself.

Only daily counts by state are stored: no actors, no URLs, no individual
records.

Categories (CAMEO):
  protest      root 14   demonstrate, rally, hunger strike, strike, blockade
  riot         145       protest violently, riot
  arrest       173       arrest, detain
  repression   175       use tactics of violent repression
  restriction  172x      curfew, ban, state of emergency, martial law

Run: make collect-events
"""

import json
import re
from datetime import date, datetime, timezone

from protest_attention.collect.gdelt_bq import MAX_GB, _bq, scan_gb
from protest_attention.paths import RAW

TABLE = "gdelt-bq.gdeltv2.events_partitioned"
CATEGORY_SQL = """
    case
      when EventCode = '145' then 'riot'
      when EventRootCode = '14' then 'protest'
      when EventCode = '173' then 'arrest'
      when EventCode = '175' then 'repression'
      when EventBaseCode = '172' then 'restriction'
    end"""


def daily_by_state(start: date, end: date) -> tuple[list[dict], float]:
    sql = f"""
        select cast(SQLDATE as string) as day, ActionGeo_ADM1Code as adm1,
               {CATEGORY_SQL} as category,
               count(distinct GLOBALEVENTID) as events,
               countif(IsRootEvent = 1) as root_events,
               sum(NumArticles) as articles
        from `{TABLE}`
        where _PARTITIONTIME between timestamp('{start}') and timestamp('{end}')
          and SQLDATE between {start:%Y%m%d} and {end:%Y%m%d}
          and ActionGeo_CountryCode = 'IN'
          and (EventRootCode = '14' or EventCode in ('173', '175') or EventBaseCode = '172')
        group by day, adm1, category"""
    gb = scan_gb(sql)
    if gb > MAX_GB:
        raise RuntimeError(f"query would scan {gb:.0f} GB, above the {MAX_GB} GB guard")
    rows = json.loads(_bq(sql) or "[]")
    return [
        {"date": f"{r['day'][:4]}-{r['day'][4:6]}-{r['day'][6:8]}", "adm1": r["adm1"],
         "category": r["category"], "events": int(r["events"]),
         "root_events": int(r["root_events"]), "articles": int(r["articles"])}
        for r in rows
    ], gb


def collect(project: str, start: date, end: date) -> dict:
    """One raw file per calendar-year chunk; resumable like the other collectors."""
    out = RAW / "gdelt_events"
    out.mkdir(parents=True, exist_ok=True)
    for f in sorted(out.glob(f"{project}_*.json")):
        prior = json.loads(f.read_text())
        if (prior["start"], prior["end"]) == (start.isoformat(), end.isoformat()):
            return {**prior, "path": str(f)}
    rows, gb = daily_by_state(start, end)
    record = {
        "project": project, "table": TABLE, "start": start.isoformat(),
        "end": end.isoformat(), "gb_scanned": round(gb, 2),
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
    }
    stamp = re.sub(r"[-:]", "", record["collected_at"])
    path = out / f"{project}_{start}_{end}_{stamp}.json"
    path.write_text(json.dumps(record))
    return {**record, "path": str(path)}


def run(first_year: int = 2019, today: date | None = None) -> list[dict]:
    today = today or date.today()
    last = date.fromordinal(today.toordinal() - 1)
    done = []
    for year in range(first_year, last.year + 1):
        start, end = date(year, 1, 1), min(date(year, 12, 31), last)
        rec = collect("events", start, end)
        print(f"{year}: {len(rec['rows'])} rows, {rec['gb_scanned']} GB", flush=True)
        done.append(rec)
    return done


if __name__ == "__main__":
    run()
