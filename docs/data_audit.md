# Data audit (Week 0)

One row per source. Gate: at least two independent outcome measures must pass
before any analysis code is written, and Google Trends alone does not count.

| Source | Tested | Result | Granularity | Coverage | Limits hit | Limitation that bites |
|---|---|---|---|---|---|---|
| Wikipedia pageviews | 2026-10-19 | **Pass** | Daily, `/user/` agent | 2015-07-01 onward | Burst throttling: 429 with `retry-after: 4` even at 1 req/s; 42 throttled of ~620 calls, all recovered | Redirects carry up to 93% of traffic; Hindi and Bengali volumes are thin for 2026 events |
| Google Trends | | not yet tested | | | | |
| GDELT | | not yet tested | | | | |
| YouTube Data API v3 | | not yet tested | | | | |
| Fact Check Tools API | | not yet tested | | | | |
| ACLED | | not yet tested | | | | |
| SFLC.in shutdown tracker | | not yet tested | | | | |
| Bluesky | | not yet tested | | | | |
| Reddit | | not yet tested | | | | |
| Wayback Machine CDX | | not yet tested | | | | |

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

### Decisions still open for Project A

- Selection rule and peak threshold N (plan: "dedicated English article and a
  peak of at least N daily views").
- Whether NEET 2026 counts: the article is the scandal, not the protests.
- Whether SIR (a policy article, not a protest article) belongs in the set or
  only serves as context for the current wave.
- The redirect inclusion rule in finding 2.
- Farmers' protest: global peak only, or each peak as its own decay episode.
