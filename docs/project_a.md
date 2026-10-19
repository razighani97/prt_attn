# Project A: attention decay across Indian protest movements

Data through 2026-10-18 (pageviews published through 2026-10-17).
Reproduce with `make project-a`. Full results:
[`data/processed/project_a_halflives.csv`](../data/processed/project_a_halflives.csv).

## Finding

Public attention to Indian protest movements **halves within 2 to 5 days of
its peak**, on every movement and on both independent measures (Wikipedia
pageviews and GDELT news articles). Half-life does not tell the movements
apart. **What remains a month later does**: 27% of peak attention for the CAA
protests, 10% for the farmers' protests and 2% for the NEET protests. GDELT
news coverage shows the same order. The current anti-CEC wave halved in 2 days,
in line with its predecessors. Six days after its peak, it is too early to say
how much will remain.

![Decay curves](../output/figures/fig_a_decay.png)

## Results (English Wikipedia and GDELT, primary specification)

Excess attention above the pre-onset baseline, as a percentage of the peak
excess. Half-life: first day the 3-day centred mean falls below 50% of peak.
Day 7/30/90: centred 7-day mean.

| Movement | Series | Peak | Half-life (days) | Left at day 7 | Day 30 | Day 90 |
|---|---|---|---|---|---|---|
| CAA 2019-20 | Protest article | 2019-12-21 (93k) | 3 | 31% | **27%** | 2.3% |
| | Issue article | 2019-12-16 (575k) | 5 | 23% | 3.7% | 1.0% |
| | GDELT news | 2019-12-19 (2,061) | 5 | 43% | **26%** | 3.2% |
| Farmers 2020-21 | Protest article | 2021-02-04 (73k) | 3 | 23% | **10%** | 2.9% |
| | Issue article | 2020-12-08 (41k) | 3 | 42% | 21% | 7.6% |
| | GDELT news | 2021-02-05 (533) | 3 | 31% | **18%** | 1.3% |
| NEET 2026 | Protest article | 2026-07-25 (39k) | 2 | 13% | **2.4%** | n/a (84 days) |
| | Issue article | 2026-07-27 (27k) | 2 | 7% | 1.5% | n/a |
| | GDELT news | 2026-07-23 (800) | 3 | 23% | **6.0%** | n/a |
| Anti-CEC 2026 (ongoing) | Protest article | 2026-10-11 (7.6k) | 2 | 6 days of data | | |
| | Issue article (SIR) | 2026-10-11 (18k) | 3 | 6 days of data | | |
| | GDELT news | 2026-09-25 (372) | 3 | 50% (second wave) | 23 days of data | |

**Two measures agree on order.** On day-30 attention, protest articles rank
CAA > farmers > NEET, and so does GDELT (26% > 18% > 6%). Issue articles rank
differently (farmers > CAA > NEET), because the farm-acts article absorbed the
January–February 2021 wave and the repeal in November 2021.

**The current wave, first week (exploratory, chosen after seeing the data).**
Excess remaining at day 4 on the protest article: anti-CEC 28%, CAA 28%,
farmers 35%, NEET 25%. Nothing so far separates it from its predecessors.
GDELT coverage of the wave has two peaks, the Indian Express report
(2026-09-25) and the protest peak (2026-10-11), so news attention has already
been sustained longer than its first half-life suggests.

## Robustness

| Check | Result |
|---|---|
| Redirect handling (all / canonical only / no pre-merge pages) | Dropping the pre-merge pages changes nothing (except the anti-CEC protest article, which has not yet reached 50% within its 6 days without its merged page). Canonical-only changes half-lives by at most 1 day, except the NEET issue article (25 days, 37% at day 30): 93% of its traffic sits on its pre-rename title, so the canonical title alone misses the peak. That is the case for summing redirects. Farm-acts day 30: 21% with redirects, 8.3% canonical only |
| Hindi replication | Valid for two series. CAA Act: half-life 5 days, 5.5% at day 30 (English 5 days, 3.7%). Farmers' protest: 3 days, 21% at day 30 (English 3 days, 10%). Five translations were created after the English peak and are excluded; the rest are too small to fit |
| Bengali | Too small. Every Bengali series that existed at the English peak peaks below 200 views/day |
| Exponential vs power law | **Not robust.** With the floor fixed at the pre-onset baseline, AIC prefers a power law for 9 of 11 fitted series; with the floor estimated, for 6 of 11 (farm acts, farmers GDELT and the NEET protest article flip to exponential). The log-log curves are not straight: secondary waves interrupt the decay. No claim about functional form is made |
| Model half-lives | Bootstrap intervals are wide and the models misfit the first days (CAA protest exponential: 34 days, against an observed 3), so they are reported in the CSV but not used |

## Decisions, including those made after seeing the data

Set before collection: the selection rule and N = 5,000 (`docs/data_audit.md`),
t = 0 at the episode peak, baseline = pre-onset median, redirects included,
farmers' protest at its global peak.

Made after seeing the data, and labelled as such:

1. **Peak search extended 7 days past the episode end.** The NEET issue
   article peaks on 2026-07-27, two days after the protests ended, and the
   original rule placed t = 0 on 07-25. Effect: NEET issue half-life 4 → 2
   days, day 30 1.6% → 1.5%. No other English series changed.
2. **Model-free measures as the headline.** Planned headline: model half-lives
   with bootstrap intervals. Changed because the functional form was not
   robust (above).
3. **Minimum fit volume of 200 at peak**, and **translations created after
   the English peak excluded**, both added when the Hindi and Bengali series
   turned out to be tiny or to start at their own creation.
4. **Unpublished days are missing, not zero.** The pageviews API publishes
   with a one-to-three-day lag; a cleaning bug had filled those days with
   zeros. Fixed before any result was recorded.

## What this does not show

- **Attention is not support.** Pageviews and article counts measure looking
  up and writing about, including hostile attention.
- **Not the Indian public.** English Wikipedia skews urban, educated and
  partly diaspora; the Hindi replication covers only two series.
- **No magnitude comparisons across years.** India's online population grew
  enormously between 2019 and 2026; only normalised shapes are compared.
- **CAA is confounded by the pandemic.** The episode ends with the national
  lockdown on 2020-03-24.
- **NEET's rise is unobserved.** The protest article was created six weeks
  into the protests; its peak and decay are observed.
- **GDELT matching is by URL.** It counts articles whose web address names the
  movement, a narrower measure than full-text volume.
- **Faster or slower decay is not success or failure.** A longer tail is a
  longer window in which organisation is possible, nothing more.
