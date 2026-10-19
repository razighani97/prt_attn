"""Coding sheets -> validation, inter-pass agreement, and the event list.

  make check-coding   report invalid values in either sheet
  make kappa          Cohen's kappa between pass 1 and pass 2 (codebook: >= 0.7)
  make events         merge relevant pass-1 rows into events/crackdowns.csv

Rules are in events/codebook.md; this file only applies them.
"""

import csv
from collections import defaultdict
from datetime import datetime, timezone

from protest_attention.collect.sweep import SHEETS
from protest_attention.paths import ROOT

TYPES = {"mass_detention", "leader_detention", "house_arrest", "internet_shutdown",
         "transit_closure", "press_restriction", "force_used", "assembly_ban"}
YN = {"y", "n"}
KAPPA_TARGET = 0.7
EVENT_FIELDS = ["event_id", "date", "type", "location", "scale", "anticipated",
                "protest_scheduled", "source_urls", "n_outlets", "coder", "coded_at"]


def load(n: int) -> list[dict]:
    path = SHEETS[n]
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def problems(rows: list[dict]) -> list[str]:
    """Every invalid or missing value, as 'candidate_id: message'."""
    out = []
    for r in rows:
        cid, rel = r["candidate_id"], r["relevant"].lower()
        if rel == "":
            continue  # not coded yet
        if rel not in YN:
            out.append(f"{cid}: relevant must be y or n, got {r['relevant']!r}")
            continue
        if rel == "n":
            continue
        if r["type"] not in TYPES:
            out.append(f"{cid}: type {r['type']!r} not in codebook")
        for field in ("anticipated", "protest_scheduled"):
            if r[field].lower() not in YN:
                out.append(f"{cid}: {field} must be y or n")
        try:
            datetime.strptime(r["event_date"], "%Y-%m-%d")
        except ValueError:
            out.append(f"{cid}: event_date must be YYYY-MM-DD, got {r['event_date']!r}")
        if not r["state"]:
            out.append(f"{cid}: state is required")
        if r["scale"] and not r["scale"].isdigit():
            out.append(f"{cid}: scale must be a whole number or blank")
    return out


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    """Cohen's kappa for two equal-length label lists."""
    if not a or len(a) != len(b):
        return None
    n = len(a)
    labels = set(a) | set(b)
    p_obs = sum(x == y for x, y in zip(a, b)) / n
    p_exp = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return 1.0 if p_exp == 1 else (p_obs - p_exp) / (1 - p_exp)


def _primary(rows: list[dict]) -> dict[str, dict]:
    return {r["candidate_id"]: r for r in rows if r.get("act_no", "1") in ("", "1")}


def agreement(p1: list[dict], p2: list[dict]) -> dict:
    a, b = _primary(p1), _primary(p2)
    both = [c for c in a if c in b and a[c]["relevant"] and b[c]["relevant"]]
    result = {"articles_coded_in_both": len(both)}
    rel_a = [a[c]["relevant"].lower() for c in both]
    rel_b = [b[c]["relevant"].lower() for c in both]
    result["relevant"] = cohen_kappa(rel_a, rel_b)
    yes = [c for c in both if a[c]["relevant"].lower() == b[c]["relevant"].lower() == "y"]
    result["relevant_in_both"] = len(yes)
    for field in ("type", "anticipated"):
        result[field] = cohen_kappa([a[c][field].lower() for c in yes],
                                    [b[c][field].lower() for c in yes])
    return result


def build_events(rows: list[dict], coder: str) -> tuple[list[dict], list[dict]]:
    """Merge relevant rows into events; split off single-outlet events."""
    rel = [r for r in rows if r["relevant"].lower() == "y"]
    by_id = {(r["candidate_id"], r.get("act_no") or "1"): r for r in rel}
    parent: dict = {}

    def find(k):
        while parent.get(k, k) != k:
            k = parent[k]
        return k

    def union(x, y):
        parent[find(x)] = find(y)

    groups: dict[tuple, list] = defaultdict(list)
    for key, r in by_id.items():
        groups[(r["event_date"], r["type"], r["city"].lower(), r["state"].lower())].append(key)
    for keys in groups.values():
        for k in keys[1:]:
            union(k, keys[0])
    for key, r in by_id.items():
        if r["same_event_as"]:
            for other in by_id:
                if other[0] == r["same_event_as"]:
                    union(key, other)

    clusters: dict = defaultdict(list)
    for key in by_id:
        clusters[find(key)].append(by_id[key])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    events, single = [], []
    for members in sorted(clusters.values(), key=lambda m: (m[0]["event_date"], m[0]["type"])):
        first = min(members, key=lambda r: (r["first_seen"], r["candidate_id"]))
        outlets = sorted({m["outlet"] for m in members})
        scales = [int(m["scale"]) for m in sorted(members, key=lambda r: r["first_seen"]) if m["scale"]]
        ev = {
            "date": first["event_date"], "type": first["type"],
            "location": f"{first['city']}, {first['state']}",
            "scale": scales[0] if scales else "",
            # Conservative: anticipated unless every source agrees it was not.
            "anticipated": "n" if all(m["anticipated"].lower() == "n" for m in members) else "y",
            "protest_scheduled": "y" if any(m["protest_scheduled"].lower() == "y" for m in members) else "n",
            "source_urls": " ".join(sorted({m["url"] for m in members})),
            "n_outlets": len(outlets), "coder": coder, "coded_at": now,
        }
        (events if len(outlets) >= 2 else single).append(ev)
    for i, ev in enumerate(events, 1):
        ev["event_id"] = f"CR{i:03d}"
    for i, ev in enumerate(single, 1):
        ev["event_id"] = f"SS{i:03d}"
    return events, single


def _write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        w.writeheader()
        w.writerows(rows)


def main(command: str, coder: str = "AG") -> None:
    if command == "check":
        for n in SHEETS:
            rows = load(n)
            coded = sum(1 for r in rows if r["relevant"])
            issues = problems(rows)
            print(f"pass {n}: {coded} of {len(rows)} rows coded, {len(issues)} problems")
            for p in issues[:50]:
                print("  ", p)
    elif command == "kappa":
        res = agreement(load(1), load(2))
        print(f"articles coded in both passes: {res['articles_coded_in_both']}, "
              f"relevant in both: {res['relevant_in_both']}")
        for field in ("relevant", "type", "anticipated"):
            k = res[field]
            verdict = "n/a" if k is None else ("pass" if k >= KAPPA_TARGET else "BELOW 0.7")
            print(f"  {field:12} kappa = {'n/a' if k is None else f'{k:.3f}'}  {verdict}")
    elif command == "events":
        events, single = build_events(load(1), coder)
        _write(ROOT / "events" / "crackdowns.csv", events)
        _write(ROOT / "events" / "crackdowns_single_source.csv", single)
        print(f"{len(events)} events from two or more outlets, {len(single)} single-source")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "check")
