"""Week 0 audit: is GDELT article volume a usable second outcome measure?

For each candidate movement, collect daily article counts from Indian sources
and from non-Indian sources, and check them against the English Wikipedia
series from the Wikipedia audit: same peak, correlated over time?

Audit only. The queries below are a first keyword set; the plan requires the
final analysis to be rerun on at least two alternative lists.

Run: make audit-gdelt
"""

import glob
import json

import pandas as pd

from protest_attention.audit.wikipedia import CANDIDATES
from protest_attention.collect import gdelt
from protest_attention.collect import wikipedia as w
from protest_attention.paths import OUTPUT, RAW

QUERIES = {
    "caa": '("citizenship amendment" OR "anti-CAA" OR "CAA protest")',
    "farmers": '("farmers protest" OR "farm laws" OR "kisan andolan")',
    "neet2026": '("NEET paper leak" OR "NEET scandal" OR "NEET exam")',
    "anticec2026": '("Chief Election Commissioner" OR "anti-CEC")',
    "sir": '("Special Intensive Revision" OR "electoral roll revision")',
}
SCOPES = ("india", "abroad")


def _wikipedia_series(title: str) -> pd.Series:
    """Summed en pageviews from the most recent Wikipedia audit raw file."""
    files = sorted(glob.glob(str(RAW / "pageviews" / f"audit_en_user_*{w._slug(title)}_*.json")))
    if not files:
        return pd.Series(dtype=float)
    s = pd.Series(w.summed(json.loads(open(files[-1]).read())), dtype=float)
    s.index = pd.to_datetime(s.index)
    return s


def run() -> pd.DataFrame:
    rows = []
    for label, title, start, end in CANDIDATES:
        if label not in QUERIES:
            continue
        wiki = _wikipedia_series(title)
        for scope in SCOPES:
            row = {"movement": label, "scope": scope, "query": QUERIES[label],
                   "window": f"{start}..{end}"}
            try:
                rec = gdelt.collect("audit", label, QUERIES[label], scope, start, end)
            except RuntimeError as exc:
                # Throttling that outlasts every retry is a finding, not a crash.
                rows.append({**row, "status": f"failed: {str(exc)[:40]}"})
                continue
            df = pd.DataFrame(rec["points"])
            row.update({"status": "ok", "resolution": rec["resolution"], "days_returned": len(df)})
            if df.empty:
                rows.append(row)
                continue
            df["date"] = pd.to_datetime(df["date"])
            arts = df.set_index("date")["articles"]
            peak_day = arts.idxmax()
            # Reindex to the full window: GDELT omits days, it does not report zeros.
            both = pd.concat([arts, wiki], axis=1, keys=["gdelt", "wiki"], sort=True).loc[str(start):str(end)].fillna(0)
            row.update({
                "nonzero_days": int((arts > 0).sum()),
                "total_articles": int(arts.sum()),
                "peak_day": peak_day.date().isoformat(),
                "peak_articles": int(arts.max()),
                "peak_share_of_all": round(arts.max() / df.set_index("date").loc[peak_day, "all_articles"], 5),
                "wiki_peak_day": wiki.idxmax().date().isoformat() if len(wiki) else None,
                "spearman_vs_wiki": round(both["gdelt"].corr(both["wiki"], method="spearman"), 3) if len(wiki) else None,
            })
            rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT / "tables" / "audit_gdelt.csv", index=False)
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 40)
    print(run().drop(columns="query").to_string(index=False))
