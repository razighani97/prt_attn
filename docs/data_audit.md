# Data audit (Week 0)

One row per source. Gate: at least two independent outcome measures must pass
before any analysis code is written, and Google Trends alone does not count.

| Source | Tested | Result | Granularity | Coverage | Limits hit | Limitation that bites |
|---|---|---|---|---|---|---|
| Wikipedia pageviews | 2026-10-19 | **Pass** | Daily, `/user/` agent | 2015-07-01 onward; latest data lags ~3 days | Burst throttling: 429 with `retry-after: 4` even at 1 req/s; 42 throttled of ~620 calls, all recovered | Redirects carry up to 93% of traffic; Hindi and Bengali volumes are thin for 2026 events |
| Google Trends | | not yet tested | | | | |
| GDELT DOC 2.0 API | 2026-10-19 | **Pass on data, fail on access** | Daily, even for 19-month windows | 2017 onward (tested back to 2019) | Persistent 429s regardless of spacing, window size or cooldown; several calls took 4-20 min of backoff, one never cleared | Unusable as the main collection route from this connection |
| GDELT via BigQuery | 2026-10-19 | **Pass** | Daily (any) | 2015-02 onward | None; ~1 GB scanned per month of URL matching, ~15 GB with themes and locations, inside the 1 TB/month free tier | No full-text search: matching is on URLs, themes and entities, so it is a related but different measure from DOC keyword volume |
| YouTube Data API v3 | | not yet tested | | | | |
| Fact Check Tools API | | not yet tested | | | | |
| ACLED | 2026-10-19 | **Fail: no access** | n/a | n/a | Free Open-access tier has no API; event data needs a paid licence (ACLED reply, 2026-10-19) | Replaced by GDELT events below |
| GDELT events via BigQuery | 2026-10-19 | **Pass, as a control and cross-check** | Daily, by state (ADM1) | 2019-01-01 onward collected (2015 available) | None; 28 GB for 2019-2026 | Machine-coded and noisy: arrests are mostly ordinary crime, riots under-captured, Delhi over-represented, coverage drifts by year |
| SFLC.in shutdown tracker | | not yet tested | | | | |
| Bluesky | | not yet tested | | | | |
| Reddit | | not yet tested | | | | |
| Wayback Machine CDX | | not yet tested | | | | |

## Gate status

**Passed.** Two independent outcome measures work: Wikipedia pageviews and
GDELT article volume (via BigQuery, with the DOC API where it responds). They
agree on timing:

| Movement | Wikipedia peak | GDELT peak |
|---|---|---|
| CAA | Act 2019-12-16, protests 2019-12-21 | India 2019-12-19, abroad 2019-12-18 (DOC API) |
| Farmers | farm acts 2020-12-08; protest 2021-02-04, 2021-01-26 | India 2020-12-08 (DOC API); 2021-02-03/04 and 2021-01-26 (BigQuery, URL match) |

## GDELT

- **DOC API** (`timelinevolraw`) returns both the matching-article count and
  the day's total monitored articles, so absolute counts and shares come from
  one call. Collected so far: CAA India and abroad, farmers India. See
  `output/tables/audit_gdelt.csv` when the run completes.
- **Access is the problem.** The API answered 429 for most calls even at one
  request per 6 s and after 5-minute cooldowns. Splitting long windows into
  120-day chunks did not help, so it is throttling the connection, not the
  query. The collector now chunks, paces, backs off up to 5 minutes, logs
  every attempt and resumes from finished timelines.
- **BigQuery** (`gdelt-bq.gdeltv2.gkg_partitioned`, project
  `prt-attn-research`) works without billing. A URL-slug match for the
  farmers' protest reproduces both Wikipedia peaks. Caveat for the India and
  abroad split: country by `.in` domain misses major Indian outlets on `.com`
  (NDTV, The Hindu, Indian Express); use GDELT's domain-to-country lookup.

## GDELT events (replacing ACLED)

ACLED's free tier has no API access, so protest activity and coercion come
from the GDELT 2.0 events table (`make collect-events`). Stored as daily
counts by state and category only: no actors, URLs or individual records.

| Category | CAMEO | Typical day, India | Usable for |
|---|---|---|---|
| protest | root 14 | 70-160 events | Control for protest activity; placebo protest days |
| repression | 175 | under 20 | Cross-check on hand-coded crackdowns |
| restriction | 172x (curfew, ban, emergency) | 45-80 | Cross-check, noisy |
| arrest | 173 | ~200 | **Not usable:** dominated by ordinary crime |
| riot | 145 | ~10 | **Not usable:** the Delhi riots (2020-02-25) register 26 |

Validation against known dates (protest events, multiple of the median 30-60
days earlier): CAA nationwide protests 2019-12-19, 15x, and 2019-12-16 to
12-20 are the top five days of 2019; Bharat Bandh 2020-12-08, 10x; tractor
rally 2021-01-26, the top day of 2021; NEET protests 2026-07-22, the top day
of 2026 (1,042 events); anti-CEC 2026-10-10, 766 events against roughly
70-110 a day in mid-September.

Limitations: 7.5% of events have no state; Delhi (IN07) holds 73k protest
events, more than twice the next state, reflecting where news is datelined;
mean daily counts range from 72 to 160 by year, so only within-episode
comparisons are valid. These are counts of reported events, not of protests.

**Seen before preregistration.** The audit showed GDELT repression events
peaking at 345 on 2026-10-10 (under 20 on a typical day), the day before the
attention peak. That is event-side data, not an outcome, but it is recorded
in PREREGISTRATION.md as known before registration.

## Wikipedia pageviews

Plan test: `2020–2021 Indian farmers' protest`, en, 2020-08-01 to 2021-12-31,
more than 300 non-zero daily values. Result: 354 days on the canonical title
alone, 430 once its 23 redirects are summed. **Pass.**

Full candidate results: [`output/tables/audit_wikipedia.csv`](../output/tables/audit_wikipedia.csv).
Reproduce with `make audit-wikipedia`.

| Movement | Article (en) | Days with views | Total views | Redirect share | Peak | `/user/` ÷ all agents | hi total | bn total |
|---|---|---|---|---|---|---|---|---|
| CAA protests | Citizenship Amendment Act protests | 386 | 2.14M | 1% | 2019-12-21 (93k) | 0.97 | 78.6k | 4.2k |
| Farmers' protest | 2020–2021 Indian farmers' protest | 489 | 2.53M | 29% | 2021-02-04 (73k) | 0.95 | 58.9k | 3.2k |
| NEET 2026 | 2026 NEET scandal | 157 | 316k | 93% | 2026-07-27 (27k) | 0.75 | 364 | 144 |
| Anti-CEC 2026 (current) | 2026 anti-CEC protests | 14 | 33k | 51% | 2026-10-11 (7.6k) | 0.82 | 50 | 51 |
| SIR (related topic) | Special Intensive Revision | 355 | 1.41M | 0% | 2026-05-04 (19k) | 0.93 | 134 | 3.7k |
| Nirbhaya | 2012 Delhi gang rape and murder | n/a | n/a | n/a | Pre-dates the API (2015-07) | n/a | n/a | n/a |

### Findings

1. **Summing redirects is essential.** Redirects hold 29% of farmers'
   protest traffic, 51% for anti-CEC and 93% for NEET 2026, where most of the
   attention landed on the earlier title before a rename. Collecting only the
   canonical title would have lost most of the NEET series.
2. **Some redirects were separate articles before they were merged.** Views
   before the canonical article was created came from `NEET 2026 Paper leak`
   (12.4k) and `2026 Mumbai Shivaji Park protests` (765, a local sub-event
   merged into anti-CEC). Decision needed: which redirects count. Proposed
   rule: include a redirect unless it is a person's name or a distinct event.
   One example of each: `Baba Ram Singh` (a person) appears among the farmers'
   protest redirects.
3. **Automated traffic is higher on recent events.** `/user/` is 95–97% of
   all-agents for CAA and farmers, but 75% for NEET 2026 and 82% for anti-CEC.
   The `/user/` filter is therefore doing real work. Spot-check event days
   before Project B.
4. **The Hindi and Bengali replication is weak for 2026.** CAA and farmers have
   usable Hindi series (59–79k views). NEET 2026 and anti-CEC have a few hundred
   views or fewer in hi and bn, and those articles were created months after the
   events. A Hindi-only robustness check will be underpowered for current events.
   Report it, but don't lean on it.
5. **The current wave has 14 days of data.** Its peak so far is 2026-10-11, so
   it is right-censored as the plan expected. Report a half-life lower bound only.
6. **Nirbhaya is out.** Pageviews start 2015-07-01; the in-window peak
   (2015-12-21) is the juvenile convict's release, not the 2012 protests.
7. **Operational: the Mac slept during collection** and stretched a 15-minute
   run to 7.5 hours. Collection targets now run under `caffeinate -i`.

## Project A selection rule

Diagnostics: `output/tables/audit_selection.csv` (`make audit-selection`).

**Unit.** A movement is measured through two English Wikipedia articles: the
**protest** article and the **issue** article for what was contested. Each is a
separate series; they are never summed.

| Movement | Protest article | Issue article |
|---|---|---|
| CAA 2019-20 | Citizenship Amendment Act protests | Citizenship (Amendment) Act, 2019 (policy) |
| Farmers 2020-21 | 2020–2021 Indian farmers' protest | 2020 Indian agriculture acts (policy) |
| NEET 2026 | 2026 Delhi Jantar Mantar protests | 2026 NEET scandal (event) |
| Current wave | 2026 anti-CEC protests | Special Intensive Revision (policy) |

**Rules.**

1. **Existence.** The movement has a dedicated English article for the
   protests and one for the issue, and the protest article was created on or
   before its peak day, so the peak is observed.
2. **Coverage.** The peak falls after 2015-07-01, when the pageviews API starts.
   Excludes Nirbhaya.
3. **Magnitude: N = 5,000.** The protest article's peak is at least 5,000
   `/user/` views, redirects summed. The reason is resolution, not taste:
   decay is fitted down to about 1% of peak, and at N = 5,000 that level is
   still at least 50 views/day, where Poisson noise is about 14%. Below that
   the tail is noise. Every historical candidate clears it by 4-19x; the
   current wave clears it at 7,593. `2026 Indian electoral controversy` (3,353)
   would fail, which is one reason SIR is the current wave's issue article.
4. **Episode peak.** t = 0 is the maximum within the movement's episode,
   not the article's all-time maximum. This matters for policy articles with
   several waves: SIR's all-time peak (2026-05-04) is a Supreme Court ruling;
   its current-wave peak is 2026-10-11, the same day as the protest article.
5. **Spike check.** If the peak is more than 3x the median of the surrounding
   week, use the peak of the 7-day mean (plan's rule). All episode peaks pass
   (1.6-3.0); SIR's all-time peak would have failed at 3.66.
6. **Censoring.** A series whose 7-day mean has not yet fallen below 50% of
   peak is reported only as a lower bound. A series with fewer than 60 days
   after peak is excluded from the fitted tail comparison and shown as a
   partial curve.

### How NEET 2026 fits

It fits, through both articles. `2026 Delhi Jantar Mantar protests` is the
NEET protest article (6 June to 25 July 2026, demanding the Education
Minister's resignation over the NEET leak and other exam irregularities). It
peaks on 2026-07-25 at 38.9k, and the scandal article peaks two days later at
26.8k. It is the plan's "clear resolution" case: decay is fast, with the
scandal article at 1.6% of peak after 30 days. Caveats to state:

- The protest article was created on 2026-07-16, six weeks into the protests,
  so the rise is unobserved. The peak and decay, which are what Project A
  measures, are observed.
- The protests covered several exams' irregularities, not only NEET.
- Follow-up is 80-84 days, enough for the half-life, and above the 60-day
  floor for the tail.

### How SIR fits

It fits as the current wave's issue article, in the same role as the CAA Act
and the farm acts: a policy that preceded the protests and that they contest.
Its current-wave peak coincides with the protest article's (2026-10-11), at
11x its August 2026 median (1,658/day). It is not a movement on its own, and
it must use the episode peak (rule 4), not its all-time peak.

### Provisional finding to report honestly

The current wave is not decaying slowly so far. The anti-CEC protest article
fell to 40% of peak two days after its 2026-10-11 peak and to 28% by 10-15;
SIR to 37%. The plan's framing, "has not yet fallen below 50%", does not hold
on current data. The wave is ongoing and may produce new peaks, so treat this as
provisional and recheck at each collection.

### Decisions still open

- Redirects: include all, or exclude people's names and distinct events
  (finding 2).
- Farmers' protest: global peak only, or each major peak as its own episode.
