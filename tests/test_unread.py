"""Figures of a tally sheet that could not be read.

A figure that is illegible, or a field left empty, is not a zero. A statement
lists such figures under ``counts.unread`` and gives them no value; the
verifier then treats every sum they belong to as a lower bound.
"""

import pytest

from actasum.statement import AreaTotals, FormatError, OfficialTotals, Statement
from actasum.verify import aggregate, check_station, compare, format_comparison, resolve, verify


def statement(station="xx/01/A", *, blank=2, null=3, votes=None, stage="count", **more):
    return Statement(
        profile="xx/test/v0", election="xx/e/2026-01", station=station, constituency="xx",
        blank=blank, null=null, candidatures={"A": 50, "B": 30} if votes is None else votes,
        stage=stage, **more,
    )  # fmt: skip


def official(a=50, b=30, *, blank=2, null=3, other=None, total=None, unread=None):
    area = AreaTotals(
        blank=blank, null=null, candidatures={"A": a, "B": b}, other=other,
        candidature_total=total, unread=unread or {},
    )  # fmt: skip
    return OfficialTotals(profile="xx/test/v0", election="xx/e/2026-01", areas={"xx": area})


# --- the format ---


def test_statements_written_before_keep_their_identifier():
    """These three were hashed with the core as it was before this change."""
    docs = [
        {"spec": "actasum/statement/v0.1", "profile": "es/loreg/v0.1",
         "election": "es/congreso/2019-11", "station": "es/04/003/02/001/B",
         "constituency": "es/04",
         "counts": {"blank": 3, "null": 5, "candidatures": {"000001": 120, "000002": 88},
                    "registered": 512, "candidature_total": 208},
         "evidence": {"kind": "official-dataset",
                      "sha256": "e7b621f295d7bf79b794941d4f11e7bcf7bd971ecbd6eb21dd4269d59926e441"}},
        {"spec": "actasum/statement/v0.1", "profile": "es/loreg/v0.1",
         "election": "es/congreso/2019-11", "station": "es/04/999/09/0000/U",
         "constituency": "es/04", "unit": "aggregate",
         "counts": {"blank": 0, "null": 1, "candidatures": {"000001": 7}}},
        {"spec": "actasum/statement/v0.1", "profile": "co/codigo-electoral/v0.1",
         "election": "co/presidente/2026-05", "station": "co/16/001/01/01/001",
         "constituency": "co", "stage": "canvass", "supersedes": "sha256:" + "ab" * 32,
         "counts": {"blank": 2, "null": 0, "candidatures": {"0009-011": 49, "0026-001": 29},
                    "other": {"unmarked": 3}},
         "evidence": {"kind": "official-dataset", "sha256": "sha256:" + "cd" * 32}},
    ]  # fmt: skip
    assert [Statement.from_dict(doc).statement_id() for doc in docs] == [
        "sha256:59932774c7ffa175bbdfb6b9a6c8ff7b0d00a75318a185a33864e52f550b96c0",
        "sha256:c1423478f68cfacb8e2b6658398bab32f5df5493ed8a102b4591eab250bd27c8",
        "sha256:0282dece04c0f233e501c5868acc3fd0c5f302c372114cbdc26d7d4bdf193be0",
    ]
    assert all("unread" not in Statement.from_dict(doc).to_dict()["counts"] for doc in docs)


def test_an_unread_figure_has_no_value_and_keeps_its_reason():
    s = statement(
        null=None, votes={"A": 50},
        unread={"null": "empty", "candidature:B": "illegible", "other:unmarked": "empty"},
    )  # fmt: skip
    counts = s.to_dict()["counts"]
    assert "null" not in counts and "B" not in counts["candidatures"] and "other" not in counts
    assert counts["unread"] == {
        "candidature:B": "illegible", "null": "empty", "other:unmarked": "empty",
    }  # fmt: skip
    again = Statement.from_dict(s.to_dict())
    assert again == s and again.statement_id() == s.statement_id()
    assert s.value("candidature:B") is None and s.value("candidature:A") == 50
    assert s.value("candidature:C") == 0  # not listed and not unread: a zero, as before
    assert s.ballots == 52  # what was read; the sheet has at least that


def test_unread_is_never_a_zero_nor_a_value():
    with pytest.raises(FormatError, match="cannot also carry a value"):
        statement(votes={"A": 50, "B": 0}, unread={"candidature:B": "illegible"})
    with pytest.raises(FormatError, match="cannot also carry a value"):
        statement(null=0, unread={"null": "empty"})
    with pytest.raises(FormatError, match="must be one of"):
        statement(votes={"A": 50}, unread={"candidature:B": "smudged"})
    with pytest.raises(FormatError, match="is not blank, null"):
        statement(unread={"registered": "illegible"})
    with pytest.raises(FormatError, match="counts.null must be"):
        statement(null=None)  # missing, and not said to be unread
    doc = statement().to_dict()
    del doc["counts"]["blank"]
    with pytest.raises(FormatError, match="counts.blank"):
        Statement.from_dict(doc)


def test_the_two_reasons_give_different_statements():
    one = statement(votes={"A": 50}, unread={"candidature:B": "illegible"})
    other = statement(votes={"A": 50}, unread={"candidature:B": "empty"})
    assert one.statement_id() != other.statement_id() and one.figures != other.figures


# --- the sum of an area ---


def test_a_sum_with_an_unread_figure_is_a_lower_bound_neither_match_nor_difference():
    statements = [
        statement("xx/01/A"),
        statement("xx/01/B", votes={"A": 40}, unread={"candidature:B": "illegible"}),
    ]
    totals = aggregate(statements)["xx"]
    assert totals.candidatures == {"A": 90, "B": 30}
    assert totals.unread == {"candidature:B": 1, "candidature_total": 1}

    # The official figure for B is 55: the stations give at least 30.
    report = verify(statements, official(a=90, b=55, blank=4, null=6, total=145))
    assert not report.differences
    assert [(b.item, b.recomputed, b.official, b.statements) for b in report.bounds] == [
        ("candidature_total", 120, 145, 1),
        ("candidature:B", 30, 55, 1),
    ]
    assert report.areas_checked == 1 and report.areas_matching == 0
    assert not report.ok and report.undecided
    assert report.areas_undecided == ["xx"] and report.areas_differing == []

    # Even when the figures happen to be equal, the sum is not called a match.
    equal = verify(statements, official(a=90, b=30, blank=4, null=6))
    assert not equal.ok and equal.undecided and not equal.differences


def test_case_1_a_lower_bound_above_the_official_figure_differs_by_at_least_that_much():
    statements = [
        statement(null=None, unread={"null": "illegible"}),
        statement("xx/01/B", null=9),
    ]
    report = verify(statements, official(a=100, b=60, blank=4, null=5))
    (difference,) = report.differences
    assert (difference.item, difference.recomputed, difference.official) == ("null", 9, 5)
    assert difference.bound == "recomputed" and difference.describe_delta == "at least 4 above"
    doc = report.to_dict()["differences"][0]
    assert doc["delta"] == 4 and doc["delta_is_a_minimum"] is True
    text = format_comparison(compare(statements, official(a=100, b=60, blank=4, null=5)))
    assert "null: recomputed at least 9, official 5 (at least 4 above)" in text
    # A difference between two totals is still an exact one.
    exact = verify([statement()], official(a=49))
    assert exact.differences[0].describe_delta == "+1" and not exact.differences[0].bound
    assert "delta_is_a_minimum" not in exact.to_dict()["differences"][0]


def test_case_2_a_lower_bound_equal_to_or_below_the_official_figure_says_nothing():
    statements = [statement(null=None, unread={"null": "empty"}), statement("xx/01/B", null=5)]
    for official_null in (5, 8):  # equal, then above
        report = verify(statements, official(a=100, b=60, blank=4, null=official_null))
        assert report.differences == []
        (bound,) = report.bounds
        assert (bound.item, bound.recomputed, bound.official) == ("null", 5, official_null)
        assert not report.ok and report.undecided and report.areas_matching == 0
    text = format_comparison(compare(statements, official(a=100, b=60, blank=4, null=8)))
    assert "null: recomputed at least 5, official 8" in text and "nothing is said" in text


def test_case_3_two_lower_bounds_say_nothing_whichever_is_larger():
    statements = [statement(null=None, unread={"null": "empty"}), statement("xx/01/B", null=9)]
    for official_null in (5, 9, 20):  # below, equal and above the recomputed bound
        totals = official(a=100, b=60, blank=4, null=official_null, unread={"null": 2})
        report = verify(statements, totals)
        assert report.differences == []
        (bound,) = report.bounds
        assert (bound.recomputed, bound.official) == (9, official_null)
        assert (bound.statements, bound.official_unread) == (1, 2)
        assert report.undecided
    text = format_comparison(compare(statements, totals))
    assert "recomputed at least 9, official at least 20" in text


def test_an_official_figure_that_is_a_lower_bound_is_treated_the_same_way():
    statements = [statement(null=3)]
    below = verify(statements, official(null=7, unread={"null": 1}))
    (difference,) = below.differences
    assert difference.bound == "official" and difference.describe_delta == "at least 4 below"
    assert verify(statements, official(null=2, unread={"null": 1})).differences == []
    # and an official-totals document keeps the mark when written and read back
    again = OfficialTotals.from_dict(official(null=7, unread={"null": 1}).to_dict())
    assert again.areas["xx"].unread == {"null": 1}
    # an unread candidature behind the official figures makes their total a bound too
    total = verify(
        [statement()], official(a=50, b=40, total=90, unread={"candidature:B": 1})
    )
    assert [(d.item, d.bound) for d in total.differences] == [
        ("candidature_total", "official"), ("candidature:B", "official"),
    ]  # fmt: skip


def test_a_lower_bound_above_the_official_figure_is_a_difference():
    statements = [statement(votes={"A": 40}, unread={"candidature:B": "empty"})]
    report = verify(statements, official(a=35, b=30))
    # A was read: 40 against 35. B is open. The total, at least 40, is below 65.
    assert [(d.item, d.recomputed, d.official) for d in report.differences] == [
        ("candidature:A", 40, 35)
    ]
    assert [b.item for b in report.bounds] == ["candidature:B"]
    assert not report.undecided  # something does differ

    # The total of candidatures is a lower bound too: at least 70 against 65.
    over = verify(
        [statement(votes={"A": 70}, unread={"candidature:B": "empty"})],
        official(a=70, b=0, total=65),
    )
    assert [(d.item, d.recomputed, d.official) for d in over.differences] == [
        ("candidature_total", 70, 65)
    ]
    assert [b.item for b in over.bounds] == ["candidature:B"]
    above = verify(
        [statement(null=None, unread={"null": "illegible"}), statement("xx/01/B", null=9)],
        official(a=100, b=60, blank=4, null=5),
    )
    assert [(d.item, d.recomputed, d.official) for d in above.differences] == [("null", 9, 5)]


def test_blank_null_and_other_categories_can_be_lower_bounds_too():
    statements = [
        statement(blank=None, null=None, other={}, unread={
            "blank": "empty", "null": "illegible", "other:unmarked": "empty",
        }),
        statement("xx/01/B", other={"unmarked": 4}),
    ]  # fmt: skip
    report = verify(statements, official(a=100, b=60, blank=5, null=7, other={"unmarked": 6}))
    assert sorted(b.item for b in report.bounds) == ["blank", "null", "other:unmarked"]
    assert not report.differences and report.undecided


def test_merged_candidatures_carry_the_bound_to_the_code_they_are_added_to():
    statements = [statement(votes={"A": 50}, unread={"candidature:B": "illegible"})]
    totals = aggregate(statements, merge={"B": "A"})["xx"]
    assert totals.candidatures == {"A": 50}
    assert totals.unread == {"candidature:A": 1, "candidature_total": 1}
    # A statement with two unread candidatures is one statement behind the total.
    two = statement(votes={}, unread={"candidature:A": "empty", "candidature:B": "illegible"})
    assert aggregate([two])["xx"].unread["candidature_total"] == 1


def test_the_comparison_says_undecided_and_does_not_pass():
    statements = [statement(votes={"A": 50}, unread={"candidature:B": "illegible"})]
    comparison = compare(statements, official())
    assert comparison.official_matches == "undecided" and not comparison.ok
    text = format_comparison(comparison)
    assert "only a lower bound" in text and "recomputed at least 0, official 30" in text
    assert "neither match nor differ" in text
    doc = comparison.to_dict()
    assert doc["ok"] is False and doc["lower_bounds"][0]["statements_with_the_figure_unread"] == 1


def test_a_sheet_total_is_not_contradicted_by_rows_that_could_not_all_be_read():
    partial = statement(votes={"A": 50}, unread={"candidature:B": "illegible"}, candidature_total=80)
    assert check_station(partial) == []
    too_many = statement(
        votes={"A": 90}, unread={"candidature:B": "illegible"}, candidature_total=80
    )
    assert [issue.code for issue in check_station(too_many)] == ["candidature-sum"]


# --- several captures of one act ---


def test_one_capture_unread_and_another_read_is_not_a_conflict():
    unreadable = statement(votes={"A": 50}, unread={"candidature:B": "illegible"})
    read = statement(evidence={"kind": "observer-capture"})
    resolution = resolve([unreadable, read])
    assert resolution.conflicts == []
    (counted,) = resolution.counted
    assert counted.candidatures == {"A": 50, "B": 30} and not counted.unread
    assert compare([unreadable, read], official()).official_matches == "both"


def test_captures_that_each_read_what_the_other_could_not_are_put_together():
    first = statement(votes={"A": 50}, unread={"candidature:B": "illegible"})
    second = statement(null=None, unread={"null": "empty"})
    (counted,) = resolve([first, second]).counted
    assert (counted.null, counted.candidatures, counted.unread) == (3, {"A": 50, "B": 30}, {})


def test_a_figure_nobody_read_stays_unread():
    first = statement(votes={"A": 50}, unread={"candidature:B": "illegible"})
    second = statement(votes={"A": 50}, unread={"candidature:B": "empty"}, evidence={"kind": "x"})
    resolution = resolve([first, second])
    assert resolution.conflicts == []
    assert set(resolution.counted[0].unread) == {"candidature:B"}


def test_two_captures_that_read_different_figures_are_still_a_conflict():
    unreadable = statement(votes={"A": 50}, unread={"candidature:B": "illegible"})
    thirty = statement(evidence={"kind": "observer-capture"})
    forty = statement(votes={"A": 50, "B": 40}, evidence={"kind": "party-copy"})
    resolution = resolve([unreadable, thirty, forty])
    assert [(c.station, c.statements) for c in resolution.conflicts] == [("xx/01/A", 3)]
    assert resolution.counted == []
    # and a figure read differently is a conflict whatever else is unread
    other = statement(votes={"A": 51}, unread={"candidature:B": "empty"})
    assert len(resolve([thirty, other]).conflicts) == 1


# --- two acts ---


def test_an_unread_figure_is_not_a_change_between_two_acts():
    count = statement(votes={"A": 50}, unread={"candidature:B": "illegible"})
    canvass = statement(stage="canvass", supersedes=count.statement_id())
    resolution = resolve([count, canvass])
    assert resolution.changes == []
    assert resolution.partly_compared == ["xx/01/A"]


def test_a_change_in_a_figure_both_acts_read_is_listed_with_what_was_not_compared():
    count = statement(votes={"A": 50}, unread={"candidature:B": "illegible"})
    canvass = statement(votes={"A": 48, "B": 30}, stage="canvass", supersedes=count.statement_id())
    resolution = resolve([count, canvass])
    (change,) = resolution.changes
    assert change.items == {"candidature:A": (50, 48)}
    assert change.not_compared == ("candidature:B",)
    assert resolution.partly_compared == ["xx/01/A"]
    comparison = compare([count, canvass], official(a=48, b=30))
    assert comparison.official_matches == "as standing"
    assert comparison.counted.undecided is False  # A, read as 50, differs from 48
    text = format_comparison(comparison)
    assert "could be compared only in part" in text
