from protest_attention.clean.events import agreement, build_events, cohen_kappa, problems


def _row(cid, outlet="The Hindu", **kw):
    base = {"candidate_id": cid, "outlet": outlet, "first_seen": "2026-10-10",
            "title": "", "url": f"https://x/{cid}", "recall_check": "0", "relevant": "y",
            "act_no": "1", "event_date": "2026-10-10", "type": "mass_detention",
            "city": "Delhi", "state": "Delhi", "scale": "", "anticipated": "y",
            "protest_scheduled": "y", "same_event_as": "", "notes": ""}
    return {**base, **kw}


def test_kappa_known_values():
    assert cohen_kappa(list("yyyn"), list("yyyn")) == 1.0
    # 60% raw agreement, 50% expected by chance -> kappa 0.2.
    a = list("yyyyynnnnn")
    b = list("yyynnnnnyy")
    assert abs(cohen_kappa(a, b) - 0.2) < 1e-9


def test_problems_flags_bad_values():
    bad = [_row("a", type="beating"), _row("b", event_date="10/10/2026"),
           _row("c", anticipated="maybe"), _row("d", relevant="n", type="")]
    msgs = problems(bad)
    assert any("a:" in m and "type" in m for m in msgs)
    assert any("b:" in m and "event_date" in m for m in msgs)
    assert any("c:" in m and "anticipated" in m for m in msgs)
    assert not any(m.startswith("d:") for m in msgs)


def test_same_act_in_two_outlets_is_one_event():
    rows = [_row("a", outlet="The Hindu", scale="120"),
            _row("b", outlet="Times of India", scale="150", first_seen="2026-10-11")]
    events, single = build_events(rows, "AG")
    assert len(events) == 1 and not single
    assert events[0]["n_outlets"] == 2
    assert events[0]["scale"] == 120  # earliest article's figure


def test_single_outlet_event_is_set_aside():
    events, single = build_events([_row("a")], "AG")
    assert not events and len(single) == 1


def test_anticipated_only_if_all_sources_say_no():
    rows = [_row("a", anticipated="n"), _row("b", outlet="Scroll", anticipated="y")]
    events, _ = build_events(rows, "AG")
    assert events[0]["anticipated"] == "y"


def test_same_event_as_links_rows_with_different_cities():
    rows = [_row("a", city="New Delhi"),
            _row("b", outlet="BBC", city="Delhi", same_event_as="a")]
    events, _ = build_events(rows, "AG")
    assert len(events) == 1


def test_agreement_counts_only_rows_coded_in_both():
    p1 = [_row("a"), _row("b", relevant="n"), _row("c")]
    p2 = [_row("a"), _row("b", relevant="n"), _row("c", relevant="")]
    res = agreement(p1, p2)
    assert res["articles_coded_in_both"] == 2
    assert res["relevant"] == 1.0
