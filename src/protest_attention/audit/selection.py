"""Selection diagnostics for Project A candidates (English Wikipedia).

For each candidate series this computes the quantities the selection rule is
written in terms of, so the rule can be checked mechanically rather than by
eye. Reads the latest Wikipedia audit raw files; makes no API calls.

Run: make audit-selection
"""

import pandas as pd

from protest_attention.audit.gdelt import _wikipedia_series
from protest_attention.audit.wikipedia import CANDIDATES, YESTERDAY
from protest_attention.paths import OUTPUT

# Criteria. See docs/data_audit.md for the reasoning behind each threshold.
MIN_PEAK = 5_000          # views on the peak day, redirects summed
MAX_SPIKE_RATIO = 3.0     # peak / median of the surrounding week (plan's check)
MIN_DAYS_AFTER_PEAK = 90  # below this the series is right-censored


def diagnose(label: str, title: str) -> dict:
    s = _wikipedia_series(title)
    if s.empty:
        return {"movement": label, "title": title, "note": "no data"}
    s = s.asfreq("D", fill_value=0)
    peak_day, peak = s.idxmax(), s.max()
    week = s[peak_day - pd.Timedelta(days=3): peak_day + pd.Timedelta(days=3)].drop(peak_day)
    pre = s[peak_day - pd.Timedelta(days=120): peak_day - pd.Timedelta(days=30)]
    after = s[peak_day:]
    smooth = after.rolling(7, min_periods=1).mean()

    def share_at(days: int) -> float | None:
        return round(smooth.iloc[days] / peak, 3) if len(smooth) > days else None

    days_after = len(after) - 1
    spike = round(peak / week.median(), 2) if week.median() > 0 else None
    return {
        "movement": label,
        "title": title,
        "peak_day": peak_day.date().isoformat(),
        "peak": int(peak),
        "spike_ratio": spike,
        "baseline_median": int(pre.median()) if len(pre) else None,
        "peak_over_baseline": round(peak / pre.median(), 1) if len(pre) and pre.median() > 0 else None,
        "days_after_peak": days_after,
        "share_at_30d": share_at(30),
        "share_at_90d": share_at(90),
        "views_at_1pct": round(peak / 100),
        "pass_peak": peak >= MIN_PEAK,
        "pass_spike": spike is None or spike <= MAX_SPIKE_RATIO,
        "censored": days_after < MIN_DAYS_AFTER_PEAK,
    }


def run() -> pd.DataFrame:
    rows = [diagnose(label, title) for label, title, _, end in CANDIDATES if label != "nirbhaya"]
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT / "tables" / "audit_selection.csv", index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(f"data through {YESTERDAY}")
    print(run().drop(columns="title").to_string(index=False))
