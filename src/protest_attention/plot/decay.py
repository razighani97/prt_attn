"""Project A figures.

fig_a_decay.png      main figure: excess attention as % of peak, days 0-90,
                     protest and issue articles side by side (English Wikipedia)
fig_a_decay_log.png  same curves on log-log axes, days 1-365. A power law would
                     be a straight line; the curves are not, which is why the
                     model comparison is not robust (see analyse/decay.py)
fig_a_news.png       the GDELT article-volume curves, the second measure

Curves are centred 7-day means of the daily series; the fits use daily data.
The ongoing movement is dashed and labelled as in progress.

Run: make plot-a
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from protest_attention.movements import MOVEMENTS
from protest_attention.paths import OUTPUT, PROCESSED

# Reference palette, categorical slots 1-4 in fixed order, light mode.
COLORS = {"caa": "#2a78d6", "farmers": "#eb6834", "neet": "#1baf7a", "cec": "#eda100"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NAMES = {m.key: m.name for m in MOVEMENTS}
ONGOING = {m.key for m in MOVEMENTS if m.episode_end is None}

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10, "axes.edgecolor": MUTED,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def _smooth(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("t").copy()
    g["smooth"] = g["pct_of_peak"].rolling(7, center=True, min_periods=1).mean()
    # The peak day itself stays at 100 so every curve starts from the same point.
    g.loc[g.t == 0, "smooth"] = 100.0
    return g


LABEL_X_PAD = 6     # days to the right of the last tick where the label column starts
LABEL_GAP = 13      # minimum vertical spacing between labels, in % of peak


def _place_labels(ax, ends: list[tuple[float, float, str]], max_t: int) -> None:
    """Stack labels in a column right of the curves, spread so none collide,
    each joined to its curve's end by a thin leader line."""
    ends = sorted(ends, key=lambda e: e[1])
    ys, floor = [], -2.0
    for _, y, _ in ends:
        floor = max(y, floor)
        ys.append(floor)
        floor += LABEL_GAP
    x_text = max_t + LABEL_X_PAD
    for (x, y, label), y_text in zip(ends, ys):
        ax.plot([x, x_text - 1], [y, y_text], color=MUTED, lw=0.6)
        ax.text(x_text, y_text, label, color=INK, fontsize=8, va="center")


def _panel(ax, cur: pd.DataFrame, halves: pd.DataFrame, role: str, lang: str,
           max_t: int, log: bool) -> None:
    ends = []
    for key in COLORS:
        g = cur[(cur.movement == key) & (cur.role == role) & (cur.lang == lang)]
        if g.empty:
            continue
        g = _smooth(g[g.t <= max_t])
        if log:
            g = g[(g.t >= 1) & (g.smooth > 0)]
        ongoing = key in ONGOING
        ax.plot(g.t if not log else g.t, g.smooth, color=COLORS[key], lw=2,
                ls="--" if ongoing else "-", solid_capstyle="round")
        h = halves[(halves.movement == key) & (halves.role == role) & (halves.lang == lang)]
        label = NAMES[key] + (" (in progress)" if ongoing else "")
        if not h.empty and not log:
            hl = h.iloc[0]
            parts = []
            if pd.notna(hl.get("empirical_half_life")):
                parts.append(f"halved in {int(hl.empirical_half_life)} d")
            if pd.notna(hl.get("pct_left_day30")):
                parts.append(f"{hl.pct_left_day30:.0f}% left at day 30")
            elif ongoing:
                parts.append(f"{int(hl.days_after_peak)} days of data")
            label = NAMES[key].split(" (")[0] + ("\n" + ", ".join(parts) if parts else "")
        if not log:
            end = g.iloc[-1]
            if ongoing:
                # The ongoing curve stops early; label it in the empty upper area.
                ax.annotate(label + " (in progress)", (end.t, end.smooth), xytext=(22, 72),
                            textcoords="data", color=INK, fontsize=8, va="center",
                            arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.6})
            else:
                ends.append((end.t, end.smooth, label))
    if ends:
        _place_labels(ax, ends, max_t)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def _legend(fig, ncol: int = 4) -> None:
    handles = [plt.Line2D([], [], color=COLORS[k], lw=2, ls="--" if k in ONGOING else "-")
               for k in COLORS]
    fig.legend(handles, [NAMES[k] for k in COLORS], loc="lower center", ncol=ncol,
               frameon=False, fontsize=9, labelcolor=INK)


def main_figure(cur, halves) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    for ax, role, title in zip(axes, ("protest", "issue"),
                               ("Protest article", "Issue article")):
        _panel(ax, cur, halves, role, "en", 90, log=False)
        ax.set_title(title, color=INK, loc="left", fontsize=11)
        ax.set_xlim(0, 145)
        ax.set_xticks([0, 15, 30, 60, 90])
        ax.set_ylim(-5, 105)
        ax.set_xlabel("Days since peak")
    axes[0].set_ylabel("Excess attention, % of peak")
    fig.suptitle("Attention to Indian protest movements falls by half within days of its peak",
                 x=0.06, ha="left", color=INK, fontsize=13)
    fig.text(0.06, 0.885, "English Wikipedia pageviews above the pre-onset baseline, "
             "7-day centred mean, t = 0 at each movement's peak. Half-life: first day below 50% of peak.",
             color=MUTED, fontsize=9)
    _legend(fig)
    fig.subplots_adjust(top=0.8, bottom=0.2, left=0.06, right=0.97, wspace=0.08)
    fig.savefig(OUTPUT / "figures" / "fig_a_decay.png", dpi=200)
    plt.close(fig)


def log_figure(cur, halves) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    for ax, role, title in zip(axes, ("protest", "issue"), ("Protest article", "Issue article")):
        _panel(ax, cur, halves, role, "en", 365, log=True)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(title, color=INK, loc="left", fontsize=11)
        ax.set_xlabel("Days since peak (log)")
    axes[0].set_ylabel("Excess attention, % of peak (log)")
    fig.suptitle("Neither a clean power law nor an exponential: secondary waves interrupt the decay",
                 x=0.06, ha="left", color=INK, fontsize=13)
    _legend(fig)
    fig.subplots_adjust(top=0.86, bottom=0.2, left=0.07, right=0.97, wspace=0.08)
    fig.savefig(OUTPUT / "figures" / "fig_a_decay_log.png", dpi=200)
    plt.close(fig)


def news_figure(cur, halves) -> None:
    fig, ax = plt.subplots(figsize=(7, 5.2))
    _panel(ax, cur, halves, "news", "gdelt", 90, log=False)
    ax.set_xlim(0, 145)
    ax.set_xticks([0, 15, 30, 60, 90])
    ax.set_ylim(-5, 105)
    ax.set_xlabel("Days since peak")
    ax.set_ylabel("Excess articles, % of peak")
    ax.set_title("Second measure: GDELT news articles naming the movement in the URL",
                 color=INK, loc="left", fontsize=11)
    _legend(fig, ncol=2)
    fig.subplots_adjust(top=0.9, bottom=0.24, left=0.1, right=0.97)
    fig.savefig(OUTPUT / "figures" / "fig_a_news.png", dpi=200)
    plt.close(fig)


def run() -> None:
    cur = pd.read_csv(PROCESSED / "project_a_curves.csv")
    halves = pd.read_csv(PROCESSED / "project_a_halflives.csv")
    cur = cur[cur.variant.isin(["all", "url_match"])]
    halves = halves[halves.variant.isin(["all", "url_match"])]
    (OUTPUT / "figures").mkdir(parents=True, exist_ok=True)
    main_figure(cur, halves)
    log_figure(cur, halves)
    news_figure(cur, halves)


if __name__ == "__main__":
    run()
