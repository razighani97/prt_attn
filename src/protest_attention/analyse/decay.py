"""Project A: attention decay from the episode peak.

For each series (movement x role x language x redirect variant):

1. Baseline: median of observed days in the 90 days before onset. An article
   that did not exist before the event has baseline 0, flagged.
2. t = 0: the maximum between onset and episode end plus PEAK_GRACE_DAYS. If that day is more than
   3x the median of its surrounding week, the peak of the centred 7-day mean
   is used instead (a one-link spike, not the movement).
3. Fit, on days 0..365 after the peak, with a Poisson likelihood and the
   baseline held fixed:
       exponential  mu(t) = b + A exp(-t / tau)      half-life = tau ln 2
       power law    mu(t) = b + A (t + 1)^-alpha    half-life = 2^(1/alpha) - 1
   and compare by AIC. Both have two free parameters.
4. Half-life of the better model, with a 95% interval from a moving-block
   bootstrap (7-day blocks, preserving weekly periodicity) of multiplicative
   residuals, refitting the same model each time.
5. Model-free summaries, which carry the headline: the empirical half-life
   (first day the centred 3-day mean of excess attention falls below half the
   peak excess; if it never does, the series is right-censored and only a
   lower bound is reported) and the share of peak excess remaining at days 7,
   30 and 90 (centred 7-day mean). The empirical half-life gets no bootstrap
   interval: resampling residual blocks scrambles the first few days, which
   are exactly what it measures, and produced intervals that excluded the
   point estimate.
6. Robustness: the better model refitted with the floor b as a free
   parameter. Articles created by the event have baseline 0 by construction,
   so their permanent background traffic would otherwise count as excess and
   could manufacture a long power-law tail.

Fits need a peak excess of at least MIN_FIT_PEAK (200): at half the peak that
is still 100 per day, where Poisson noise is 10%. Smaller series (most Hindi and
Bengali ones) get the empirical half-life only.

Run: make analyse-a
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln

from protest_attention.movements import BASELINE_DAYS, MOVEMENTS, PEAK_GRACE_DAYS
from protest_attention.paths import INTERIM, PROCESSED

FIT_DAYS = 365
MIN_FIT_DAYS = 60
MIN_FIT_PEAK = 200
SPIKE_RATIO = 3.0
BLOCK = 7
N_BOOT = 2000
SEED = 20261019

MODELS = {
    "exponential": (lambda t, p: np.exp(-t / np.exp(p[1])),
                    lambda p: np.exp(p[1]) * np.log(2)),
    "power_law": (lambda t, p: (t + 1.0) ** (-np.exp(p[1])),
                  lambda p: 2 ** (1 / np.exp(p[1])) - 1),
}


def _nll(p, t, y, b, shape):
    mu = b + np.exp(p[0]) * shape(t, p)
    mu = np.maximum(mu, 1e-9)
    return -(y * np.log(mu) - mu - gammaln(y + 1)).sum()


def fit(t: np.ndarray, y: np.ndarray, b: float, model: str, a0: float) -> dict:
    shape, half = MODELS[model]
    best = None
    # A few starting points: decay fits have flat directions and local optima.
    starts = [np.log(5), np.log(30)] if model == "exponential" else [np.log(0.5), np.log(1.5)]
    for s1 in starts:
        r = minimize(_nll, x0=[np.log(max(a0, 1.0)), s1], args=(t, y, b, shape),
                     method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-6, "maxiter": 4000})
        if best is None or r.fun < best.fun:
            best = r
    mu = b + np.exp(best.x[0]) * shape(t, best.x)
    return {"params": best.x, "nll": best.fun, "aic": 2 * 2 + 2 * best.fun,
            "half_life": half(best.x), "mu": mu}


def _nll_floor(p, t, y, shape):
    mu = np.exp(p[2]) + np.exp(p[0]) * shape(t, p)
    mu = np.maximum(mu, 1e-9)
    return -(y * np.log(mu) - mu - gammaln(y + 1)).sum()


def fit_floor(t: np.ndarray, y: np.ndarray, model: str, start: dict) -> dict:
    """The same model with the floor b estimated instead of fixed."""
    shape, half = MODELS[model]
    b0 = max(float(np.median(y[-60:])), 1.0)
    r = minimize(_nll_floor, x0=[start["params"][0], start["params"][1], np.log(b0)],
                 args=(t, y, shape), method="Nelder-Mead",
                 options={"xatol": 1e-6, "fatol": 1e-6, "maxiter": 6000})
    return {"floor": float(np.exp(r.x[2])), "half_life": half(r.x), "aic": 2 * 3 + 2 * r.fun}


def empirical_half_life(y: np.ndarray, b: float) -> int | None:
    excess3 = pd.Series(y - b).rolling(3, center=True, min_periods=1).mean().values
    below = np.nonzero(excess3[1:] < 0.5 * (y[0] - b))[0]
    return int(below[0] + 1) if len(below) else None


def _block_resample(r: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    n = len(r)
    starts = rng.integers(0, n - BLOCK + 1, size=int(np.ceil(n / BLOCK)))
    return np.concatenate([r[s:s + BLOCK] for s in starts])[:n]


def bootstrap(t, y, b, model, fitted, rng, n_boot=N_BOOT) -> np.ndarray:
    """Model half-lives from moving-block resamples of multiplicative residuals."""
    mu = fitted["mu"]
    ratio = np.where(mu > 0, y / mu, 1.0)
    out = np.empty(n_boot)
    for i in range(n_boot):
        y_star = mu * _block_resample(ratio, rng)
        out[i] = fit(t, y_star, b, model, a0=np.exp(fitted["params"][0]))["half_life"]
    return out


def find_peak(s: pd.Series, onset, episode_end) -> tuple[pd.Timestamp, bool]:
    ep = s[onset: episode_end] if episode_end is not None else s[onset:]
    day = ep.idxmax()
    week = s[day - pd.Timedelta(days=3): day + pd.Timedelta(days=3)].drop(day)
    if week.median() > 0 and s[day] > SPIKE_RATIO * week.median():
        smooth = s.rolling(7, center=True, min_periods=4).mean()
        ep_s = smooth[onset: episode_end] if episode_end is not None else smooth[onset:]
        return ep_s.idxmax(), True
    return day, False


def analyse_series(g: pd.DataFrame, m, rng, do_boot: bool, n_boot: int = N_BOOT,
                   en_peak: pd.Timestamp | None = None) -> dict:
    """en_peak: for Hindi and Bengali series, the English article's peak day.
    A translation created after it measures the article's creation, not the
    movement, so it is excluded."""
    s = g.set_index("date")["views"]
    obs = g.set_index("date")["observed"]
    onset = pd.Timestamp(m.onset)
    end = pd.Timestamp(m.episode_end) + pd.Timedelta(days=PEAK_GRACE_DAYS) if m.episode_end else None
    pre = s[(s.index >= onset - pd.Timedelta(days=BASELINE_DAYS)) & (s.index < onset) & obs]
    baseline = float(pre.median()) if len(pre) else 0.0

    peak_day, smoothed = find_peak(s.where(obs, 0.0), onset, end)
    # Only observed days after the peak: unpublished trailing days are dropped.
    after = s[peak_day:][obs[peak_day:]].iloc[: FIT_DAYS + 1]
    t = np.arange(len(after), dtype=float)
    y = after.values.astype(float)
    peak_excess = y[0] - baseline

    emp_half = empirical_half_life(y, baseline) if peak_excess > 0 else None
    smooth7 = pd.Series(y - baseline).rolling(7, center=True, min_periods=4).mean().values

    def remaining(day: int) -> float | None:
        if peak_excess <= 0 or len(y) <= day + 3:
            return None
        return round(100 * smooth7[day] / peak_excess, 1)

    row = {
        "movement": m.key, "role": g["role"].iat[0], "lang": g["lang"].iat[0],
        "variant": g["variant"].iat[0], "title": g["title"].iat[0],
        "baseline": round(baseline, 1), "baseline_exists": bool(len(pre)),
        "peak_day": peak_day.date().isoformat(), "peak_views": int(y[0]),
        "peak_from_7day_mean": smoothed, "peak_over_baseline":
            round(y[0] / baseline, 1) if baseline > 0 else None,
        "days_after_peak": len(after) - 1,
        "empirical_half_life": emp_half,
        "pct_left_day7": remaining(7),
        "pct_left_day30": remaining(30),
        "pct_left_day90": remaining(90),
        "censored": emp_half is None,
        "half_life_lower_bound": len(after) - 1 if emp_half is None else None,
    }
    first_obs = obs[obs].index.min() if obs.any() else None
    reason = None
    if not obs[peak_day] or peak_excess <= 0:
        reason = "excluded: no views during the episode"
    elif en_peak is not None and first_obs is not None and first_obs > en_peak:
        reason = "excluded: article created after the English peak"
    if reason:
        row.update(fit=reason, censored=None, half_life_lower_bound=None,
                   empirical_half_life=None, pct_left_day7=None,
                   pct_left_day30=None, pct_left_day90=None)
        return row
    if row["days_after_peak"] < MIN_FIT_DAYS:
        row["fit"] = "partial: too few days after peak"
        return row
    if peak_excess < MIN_FIT_PEAK:
        row["fit"] = "low volume: empirical half-life only"
        return row

    fits = {k: fit(t, y, baseline, k, a0=peak_excess) for k in MODELS}
    better = min(fits, key=lambda k: fits[k]["aic"])
    resid = (y - fits[better]["mu"]) / np.sqrt(np.maximum(fits[better]["mu"], 1e-9))
    row.update({
        "fit": "ok",
        "aic_exponential": round(fits["exponential"]["aic"], 1),
        "aic_power_law": round(fits["power_law"]["aic"], 1),
        "better_model": better,
        "delta_aic": round(abs(fits["exponential"]["aic"] - fits["power_law"]["aic"]), 1),
        "half_life_exponential": round(fits["exponential"]["half_life"], 2),
        "half_life_power_law": round(fits["power_law"]["half_life"], 2),
        "half_life": round(fits[better]["half_life"], 2),
        "power_law_alpha": round(float(np.exp(fits["power_law"]["params"][1])), 3),
        "resid_lag7_autocorr": round(float(pd.Series(resid).autocorr(7)), 3),
    })
    floor = fit_floor(t, y, better, fits[better])
    row.update({
        "free_floor": round(floor["floor"], 1),
        "half_life_free_floor": round(floor["half_life"], 2),
    })
    # Does the power law still win once the floor is free? Fit the other model too.
    other = "exponential" if better == "power_law" else "power_law"
    floor_other = fit_floor(t, y, other, fits[other])
    row["better_model_free_floor"] = better if floor["aic"] <= floor_other["aic"] else other
    if do_boot:
        boot = bootstrap(t, y, baseline, better, fits[better], rng, n_boot)
        row["half_life_ci_low"], row["half_life_ci_high"] = (
            round(float(x), 2) for x in np.nanpercentile(boot, [2.5, 97.5]))
    return row


def curves(df: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Peak-normalised excess attention, t = 0 at each series' peak (for plotting)."""
    out = []
    for _, r in results.iterrows():
        if str(r.fit).startswith("excluded"):
            continue
        g = df[(df.movement == r.movement) & (df.role == r.role) & (df.lang == r.lang)
               & (df.variant == r.variant)].set_index("date")
        after = g.loc[r.peak_day:]
        after = after.loc[after.observed, "views"].iloc[: FIT_DAYS + 1]
        norm = 100 * (after.values - r.baseline) / (r.peak_views - r.baseline)
        out.append(pd.DataFrame({"movement": r.movement, "role": r.role, "lang": r.lang,
                                 "variant": r.variant, "t": np.arange(len(after)),
                                 "date": after.index, "pct_of_peak": norm}))
    return pd.concat(out, ignore_index=True)


def run(n_boot: int = N_BOOT) -> pd.DataFrame:
    df = pd.read_parquet(INTERIM / "project_a_daily.parquet")
    by_key = {m.key: m for m in MOVEMENTS}
    rng = np.random.default_rng(SEED)
    rows = []
    en_peaks = {}
    # English first, so each translation can be checked against its English peak.
    ordered = sorted(df.groupby(["movement", "role", "lang", "variant"], sort=True),
                     key=lambda kv: kv[0][2] != "en")
    for (mov, role, lang, variant), g in ordered:
        # Intervals for the primary variant only; other variants are point checks.
        row = analyse_series(g.sort_values("date"), by_key[mov], rng,
                             do_boot=variant in ("all", "url_match"), n_boot=n_boot,
                             en_peak=en_peaks.get((mov, role, variant)) if lang in ("hi", "bn") else None)
        if lang == "en":
            en_peaks[(mov, role, variant)] = pd.Timestamp(row["peak_day"])
        rows.append(row)
    res = pd.DataFrame(rows).sort_values(["movement", "role", "lang", "variant"])
    PROCESSED.mkdir(parents=True, exist_ok=True)
    res.to_csv(PROCESSED / "project_a_halflives.csv", index=False)
    curves(df, res).to_csv(PROCESSED / "project_a_curves.csv", index=False)
    return res


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 40)
    res = run()
    cols = ["movement", "role", "lang", "variant", "peak_day", "peak_views", "baseline",
            "empirical_half_life", "better_model", "delta_aic", "half_life",
            "half_life_ci_low", "half_life_ci_high", "resid_lag7_autocorr", "fit"]
    print(res[[c for c in cols if c in res]].to_string(index=False))
