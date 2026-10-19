"""Raw Project A pageviews -> one long daily table.

Three redirect variants per article, so redirect handling is a robustness
check rather than a hidden choice:

  all          canonical title plus every redirect (primary)
  canonical    canonical title only
  no_premerge  drops redirects that had views before the canonical article
               existed: those were separate pages later merged in

Days before an article existed are unobserved, not zero, so each row carries
an `observed` flag. The API omits days with no views, so observed gaps are
filled with zeros.

Run: make clean-a
"""

import json

import pandas as pd

from protest_attention.collect.project_a import MANIFEST
from protest_attention.paths import INTERIM


def _daily(series: dict[str, list[dict]], titles: list[str]) -> pd.Series:
    totals: dict[str, int] = {}
    for t in titles:
        for p in series.get(t, []):
            totals[p["date"]] = totals.get(p["date"], 0) + p["views"]
    s = pd.Series(totals, dtype=float)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def variants(rec: dict) -> dict[str, tuple[pd.Series, pd.Timestamp]]:
    """Each variant's daily series and the first day it is observed."""
    canon = rec["article"]["canonical"]
    created = pd.Timestamp(rec["article"]["created"][:10])
    titles = list(rec["series"])
    premerge = [
        t for t in titles
        if t != canon and any(pd.Timestamp(p["date"]) < created and p["views"] > 0
                              for p in rec["series"][t])
    ]
    out = {}
    for name, keep in (
        ("all", titles),
        ("canonical", [canon]),
        ("no_premerge", [t for t in titles if t not in premerge]),
    ):
        s = _daily(rec["series"], keep)
        first_view = s[s > 0].index.min() if (s > 0).any() else created
        out[name] = (s, min(created, first_view))
    return out


def last_published(rec: dict) -> pd.Timestamp:
    """Last day the API returned data for any title. The API publishes with a
    lag of one to three days, and a day it has not published yet is missing,
    not zero."""
    days = [p["date"] for pts in rec["series"].values() for p in pts]
    return pd.Timestamp(max(days)) if days else pd.Timestamp(rec["start"])



def _gdelt_frame(entry: dict, rec: dict) -> pd.DataFrame:
    """GDELT counts in the same shape. Every day in the window is observed."""
    full = pd.date_range(rec["start"], rec["end"], freq="D")
    s = pd.Series({pd.Timestamp(p["date"]): p["articles"] for p in rec["points"]}, dtype=float)
    return pd.DataFrame({
        "movement": entry["movement"], "role": "news", "lang": "gdelt",
        "variant": "url_match", "title": rec["pattern"], "date": full,
        "views": s.reindex(full, fill_value=0.0).values, "observed": True,
    })


def build() -> pd.DataFrame:
    manifest = json.loads(MANIFEST.read_text())
    frames = []
    for entry in manifest:
        rec = json.loads(open(entry["path"]).read())
        if entry["lang"] == "gdelt":
            frames.append(_gdelt_frame(entry, rec))
            continue
        if rec["article"]["missing"]:
            continue
        full = pd.date_range(rec["start"], rec["end"], freq="D")
        last = last_published(rec)
        for variant, (s, first) in variants(rec).items():
            s = s.reindex(full, fill_value=0.0)
            frames.append(pd.DataFrame({
                "movement": entry["movement"], "role": entry["role"],
                "lang": entry["lang"], "variant": variant,
                "title": rec["article"]["canonical"], "date": full,
                "views": s.values, "observed": (full >= first) & (full <= last),
            }))
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(INTERIM / "project_a_daily.parquet", index=False)
    return df


if __name__ == "__main__":
    df = build()
    summary = (df[df.observed].groupby(["movement", "role", "lang", "variant"])
               .views.agg(["count", "sum", "max"]).astype(int))
    print(summary.to_string())
