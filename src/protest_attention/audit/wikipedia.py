"""Week 0 audit: is Wikipedia pageviews usable for each candidate movement?

Audit only. The windows below are rough and exist to test the source; the
Project A movement list and windows are fixed by the selection rule, written
down before the real collection.

Run: uv run python -m protest_attention.audit.wikipedia
"""

from datetime import date, timedelta

import pandas as pd

from protest_attention.collect import wikipedia as w
from protest_attention.paths import OUTPUT

# (label, English title, window start, window end)
YESTERDAY = date.today() - timedelta(days=1)
CANDIDATES = [
    ("caa", "Citizenship Amendment Act protests", date(2019, 9, 1), date(2020, 12, 31)),
    ("farmers", "2020–2021 Indian farmers' protest", date(2020, 8, 1), date(2022, 2, 28)),
    ("neet2026", "2026 NEET scandal", date(2026, 3, 1), YESTERDAY),
    ("anticec2026", "2026 anti-CEC protests", date(2026, 7, 1), YESTERDAY),
    ("sir", "Special Intensive Revision", date(2025, 3, 1), YESTERDAY),
    ("nirbhaya", "2012 Delhi gang rape and murder", date(2015, 7, 1), date(2016, 6, 30)),
    # Issue and protest counterparts, so every movement has both kinds of article.
    ("caa_issue", "Citizenship (Amendment) Act, 2019", date(2019, 9, 1), date(2020, 12, 31)),
    ("farmers_issue", "2020 Indian agriculture acts", date(2020, 8, 1), date(2022, 2, 28)),
    ("neet_protest", "2026 Delhi Jantar Mantar protests", date(2026, 3, 1), YESTERDAY),
    ("cec_controversy", "2026 Indian electoral controversy", date(2026, 7, 1), YESTERDAY),
]
OTHER_LANGS = ("hi", "bn")


def _stats(record: dict) -> dict:
    series = w.summed(record)
    canon = record["article"].get("canonical")
    canon_total = sum(p["views"] for p in record["series"].get(canon, []))
    total = sum(series.values())
    peak_day, peak = max(series.items(), key=lambda kv: kv[1], default=(None, 0))
    return {
        "titles": len(record["series"]),
        "moves": len(record.get("moves", [])),
        "nonzero_days": sum(1 for v in series.values() if v > 0),
        "total_views": total,
        "redirect_share": round(1 - canon_total / total, 3) if total else None,
        "peak_day": peak_day,
        "peak_views": peak,
        "first_day_with_views": next(iter(series), None),
    }


def run() -> pd.DataFrame:
    rows = []
    for label, title, start, end in CANDIDATES:
        en = w.collect_article("audit", "en", title, start, end)
        row = {"movement": label, "lang": "en", "requested": title,
               "canonical": en["article"].get("canonical"),
               "created": en["article"].get("created"),
               "window": f"{start}..{end}", **_stats(en)}

        # Bot filter check: compare /user/ with /all-agents/ on the canonical title.
        if not en["article"]["missing"]:
            allag = w.pageviews("en", en["article"]["canonical"], start, end, "all-agents")
            user = {p["date"]: p["views"] for p in en["series"][en["article"]["canonical"]]}
            a_total = sum(p["views"] for p in allag)
            row["user_share_of_all_agents"] = (
                round(sum(user.values()) / a_total, 3) if a_total else None
            )
        rows.append(row)

        if en["article"]["missing"]:
            continue
        for lang, ltitle in w.langlinks("en", en["article"]["canonical"], OTHER_LANGS).items():
            rec = w.collect_article("audit", lang, ltitle, start, end)
            rows.append({"movement": label, "lang": lang, "requested": ltitle,
                         "canonical": rec["article"].get("canonical"),
                         "created": rec["article"].get("created"),
                         "window": f"{start}..{end}", **_stats(rec)})
        for lang in OTHER_LANGS:
            if not any(r["movement"] == label and r["lang"] == lang for r in rows):
                rows.append({"movement": label, "lang": lang, "requested": None,
                             "canonical": "(no equivalent article)"})

    df = pd.DataFrame(rows)
    out = OUTPUT / "tables" / "audit_wikipedia.csv"
    df.to_csv(out, index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(run().to_string(index=False))
