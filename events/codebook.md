# Crackdown event codebook (Project B)

Written before any event is coded. Changes after coding starts are logged at
the end with a date and a reason, and trigger a recode of affected rows.

**Status: DRAFT.** The items marked **[decide]** need the coder's sign-off
before pass 1 begins.

## What counts as a crackdown

A **discrete repressive act by state authorities** (police, central armed
forces, district administration, state or union government) that is directed
at the anti-CEC protests: at protesters, at people organising or leading
them, at places where they gather, or at the information environment around
them.

It must be an **act**, not a statement. Threats, warnings, ministers'
remarks and court hearings are out. A court order is out unless the
executive carries it out against protesters, in which case the carrying-out
is the act.

It must be **linked to the protests** by at least one source. Arrests for
unrelated crimes, routine traffic policing and election-day security that is
not aimed at protesters are out.

## Coding window

Acts that occurred from **2026-09-23** (the Indian Express report) to the
end of the protests. While the protests continue, the window is extended
weekly and new candidates are added to both coding sheets.

## Fixed source list [decide]

Only these outlets are read, and every article the sweep returns from them is
screened. Nothing from social media, memory or other outlets is added.

| Outlet | Why |
|---|---|
| The Hindu | Indian, centre-left; carries PTI wire copy |
| Times of India | Indian, largest circulation, establishment-leaning; carries PTI and ANI wire copy |
| Hindustan Times | Indian, centrist; carries PTI and ANI wire copy |
| Scroll | Indian, independent digital, left-leaning |
| BBC | International |

The plan asked for two wire services. Reuters, AP and PTI are not indexed by
GDELT for this period, so they cannot be swept systematically; PTI and ANI
copy enters through the three Indian dailies, where wire bylines are visible.
Indian Express is not indexed either, which matters because it broke the
story; this is a stated limitation.

## How candidates are found

`make sweep` lists every article from the five outlets in the window whose
URL or headline contains **both** a coercion term (detain, arrest, house
arrest, lathi, tear gas, water cannon, Section 144 / 163 BNSS, prohibitory,
curfew, internet, shutdown, crackdown, barricade, metro closed, banned,
denied permission, police, FIR, booked) **and** a topic term (protest,
agitation, march, rally, bandh, dharna, gherao, CEC, Chief Election
Commissioner, Gyanesh, Special Intensive Revision, SIR, Election Commission,
electoral roll, voter).

**Recall check.** A random 50 of the articles that match a topic term but
**no** coercion term are added, flagged `recall_check = 1`, and coded the same
way. The share of them that contain a qualifying act estimates what the
keyword filter misses.

## Unit of coding

One row per **candidate article**. For each, decide:

1. `relevant`: does the article report at least one qualifying act? (y/n)
2. If yes, code the **primary act**: the one in the headline, or else the
   first one reported. Other qualifying acts in the same article go in extra
   rows with the same `candidate_id` and `act_no` 2, 3, ...

Agreement between passes (Cohen's kappa) is computed on `relevant`, and on
`type` and `anticipated` for primary acts both passes coded as relevant.
Each must reach **0.7**; below that, tighten this codebook and recode.

## Fields

| Field | Rule |
|---|---|
| `event_date` | Date the act occurred, IST, from the article. Not the publication date. If only "on Monday" is given, resolve against the dateline |
| `type` | One value from the table below |
| `city`, `state` | Where the act occurred. For a statewide or national act (a shutdown order), city = `statewide` or `national` |
| `scale` | Number of people detained or arrested, where reported. A range: the lower bound. Different figures in different sources: the figure in the earliest article. Otherwise blank |
| `anticipated` | y/n, rule below |
| `protest_scheduled` | y/n: had a protest been publicly announced, before that day, for that date in that city? |
| `same_event_as` | `candidate_id` of another row describing the same act, so duplicates merge |
| `notes` | Anything that made the decision hard. Hard cases are what tighten the codebook |

## Types

| Type | Definition |
|---|---|
| `mass_detention` | Ten or more protesters detained or arrested in one place on one day |
| `leader_detention` | A named organiser, party leader or elected representative detained or arrested |
| `house_arrest` | A named person confined to their home to stop them reaching a protest |
| `internet_shutdown` | Mobile or broadband internet suspended in an area |
| `transit_closure` | Metro stations, roads, borders or rail routes closed to stop people reaching a protest |
| `press_restriction` | Journalists detained, blocked or attacked by police; outlets or accounts ordered taken down |
| `force_used` | Lathi charge, tear gas, water cannon, rubber bullets or live fire against protesters |
| `assembly_ban` **[decide]** | Prohibitory order (Section 163 BNSS, formerly 144) or denial of permission targeting a protest. Not in the plan's list; proposed because it is the commonest pre-emptive act |

If one act fits two types (a leader detained during a mass detention), code
two rows. Fewer than ten people detained and none named: not a crackdown
under this codebook (note it).

FIRs and charges filed against protesters are **out** **[decide]**: too
frequent, rarely dated precisely, and not visible as an act on the day.

## Anticipated: the identification variable

`anticipated = n` when the public could not have known the act was coming
from information available the evening before:

- detentions or house arrests carried out **before** a scheduled protest
  begins (overnight or early morning), or of leaders travelling to it
  (at airports, stations, borders);
- a shutdown, closure or ban imposed **without prior public notice**;
- any act on a day with **no** protest scheduled in that city.

`anticipated = y` when the act was a response, at the scene, to a publicly
scheduled protest: detaining marchers at the march, force used at the rally,
an order announced at least a day in advance.

When the sources do not say when or why, code `y`. This is the conservative
direction: it keeps the unanticipated subsample, which carries the causal
claim, clean.

## Building the event list

`make events` merges relevant rows into events. Rows with the same
`event_date`, `type` and `city`, or linked by `same_event_as`, are one event.
An event needs **at least two of the five outlets**; single-source events are
kept in a separate file and dropped from the main analysis, with the count
reported.

## Procedure

1. Pass 1: code `events/coding_pass1.csv` top to bottom.
2. Wait at least seven days. Do not open pass 1.
3. Pass 2: code `events/coding_pass2.csv`, same articles, shuffled order,
   blank fields.
4. `make kappa`. Below 0.7 on any variable: tighten the codebook, log the
   change, recode both passes for the affected variable.
5. Disagreements: resolve by rereading the article against the codebook,
   record the resolution in `notes`. The resolved pass 1 is the dataset.

## Change log

| Date | Change | Reason |
|---|---|---|
| 2026-10-19 | First draft | |
