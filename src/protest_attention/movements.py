"""Project A movements and episode definitions.

Fixed by the selection rule in docs/data_audit.md. Each movement is measured
through a protest article and an issue article on English Wikipedia (plus the
Hindi and Bengali equivalents where they exist, as separate series).

onset: the trigger date. The baseline is the median of the 90 days before it.
episode_end: last day the peak may fall on (None = ongoing). t = 0 is the
maximum between onset and episode_end, not the article's all-time maximum.
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Movement:
    key: str
    name: str
    protest: str
    issue: str
    onset: date
    episode_end: date | None
    onset_note: str
    end_note: str


MOVEMENTS = [
    Movement(
        "caa", "CAA protests 2019-20",
        protest="Citizenship Amendment Act protests",
        issue="Citizenship (Amendment) Act, 2019",
        onset=date(2019, 12, 9), episode_end=date(2020, 3, 24),
        onset_note="Bill introduced in the Lok Sabha",
        end_note="National lockdown; the pandemic ends the episode (a stated confound)",
    ),
    Movement(
        "farmers", "Farmers' protests 2020-21",
        protest="2020–2021 Indian farmers' protest",
        issue="2020 Indian agriculture acts",
        onset=date(2020, 9, 17), episode_end=date(2021, 12, 11),
        onset_note="Farm bills passed by the Lok Sabha",
        end_note="Protest called off after repeal",
    ),
    Movement(
        "neet", "NEET protests 2026",
        protest="2026 Delhi Jantar Mantar protests",
        issue="2026 NEET scandal",
        onset=date(2026, 5, 12), episode_end=date(2026, 7, 25),
        onset_note="NEET-UG 2026 cancelled",
        end_note="Last day of the Jantar Mantar protests",
    ),
    Movement(
        "cec", "Anti-CEC protests 2026 (ongoing)",
        protest="2026 anti-CEC protests",
        issue="Special Intensive Revision",
        onset=date(2026, 9, 23), episode_end=None,
        onset_note="Indian Express report on dissent inside the Election Commission",
        end_note="Ongoing: right-censored",
    ),
]

BASELINE_DAYS = 90
# The peak may fall up to a week after the episode ends, to include reaction
# to the ending itself. Added after seeing the data (post-hoc): the NEET issue
# article peaks two days after the protests ended. See docs/project_a.md.
PEAK_GRACE_DAYS = 7
FOLLOW_DAYS = 365


def window(m: Movement, today: date) -> tuple[date, date]:
    """Collection window: 90 days before onset to a year after the episode, or today."""
    last = today - timedelta(days=1)
    end = m.episode_end + timedelta(days=FOLLOW_DAYS) if m.episode_end else last
    return m.onset - timedelta(days=BASELINE_DAYS), min(end, last)
