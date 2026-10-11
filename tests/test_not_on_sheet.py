"""Figures a tally sheet does not have at all.

Not the same as a figure that could not be read: nothing is missing from the
sum, so it is not a lower bound. Same shape and place as ``counts.unread``.
"""

import pytest

from actasum.statement import AreaTotals, FormatError, OfficialTotals, Statement
from actasum.verify import aggregate, compare, format_comparison, resolve, verify

NO_BLANK = {"blank": "no-field"}


def statement(station="xx/01/A", *, blank=None, null=3, votes=None, **more):
    more.setdefault("not_on_sheet", NO_BLANK if blank is None else {})
    return Statement(
        profile="xx/test/v0", election="xx/e/2026-01", station=station, constituency="xx",
        blank=blank, null=null, candidatures={"A": 50, "B": 30} if votes is None else votes,
        **more,
    )  # fmt: skip


def official(*, blank=None, null=3, a=50, b=30):
    area = AreaTotals(blank=blank, null=null, candidatures={"A": a, "B": b})
    return OfficialTotals(profile="xx/test/v0", election="xx/e/2026-01", areas={"xx": area})


def test_same_place_and_shape_as_unread_and_no_value():
    s = statement(votes={"A": 50}, unread={"candidature:B": "illegible"})
    counts = s.to_dict()["counts"]
    assert "blank" not in counts
    assert counts["not_on_sheet"] == {"blank": "no-field"}
    assert counts["unread"] == {"candidature:B": "illegible"}
    assert Statement.from_dict(s.to_dict()) == s
    assert s.value("blank") is None and s.ballots == 53


def test_a_figure_is_in_one_state_only():
    with pytest.raises(FormatError, match="cannot also carry a value"):
        statement(blank=0, not_on_sheet=NO_BLANK)
    with pytest.raises(FormatError, match="both unread and not on the sheet"):
        statement(unread={"blank": "empty"})
    with pytest.raises(FormatError, match="must be one of"):
        statement(not_on_sheet={"blank": "forgotten"})
    with pytest.raises(FormatError, match="counts.blank must be"):
        statement(not_on_sheet={})  # no value, and not said why
    doc = statement().to_dict()
    del doc["counts"]["not_on_sheet"]
    with pytest.raises(FormatError, match="counts.blank"):
        Statement.from_dict(doc)


def test_statements_written_before_keep_their_identifier():
    doc = {"spec": "actasum/statement/v0.1", "profile": "es/loreg/v0.1",
           "election": "es/congreso/2019-11", "station": "es/04/003/02/001/B",
           "constituency": "es/04",
           "counts": {"blank": 3, "null": 5, "candidatures": {"000001": 120, "000002": 88},
                      "registered": 512, "candidature_total": 208},
           "evidence": {"kind": "official-dataset",
                        "sha256": "e7b621f295d7bf79b794941d4f11e7bcf7bd971ecbd6eb21dd4269d59926e441"}}  # fmt: skip
    read = Statement.from_dict(doc)
    assert read.statement_id() == (
        "sha256:59932774c7ffa175bbdfb6b9a6c8ff7b0d00a75318a185a33864e52f550b96c0"
    )
    assert "not_on_sheet" not in read.to_dict()["counts"]


def test_nothing_is_missing_from_the_sum_so_it_is_not_a_lower_bound():
    statements = [statement("xx/01/A"), statement("xx/01/B")]
    totals = aggregate(statements)["xx"]
    assert totals.not_on_sheet == {"blank": 2} and not totals.unread and not totals.contradicted
    report = verify(statements, official(null=6, a=100, b=60))
    assert report.ok and not report.bounds and not report.not_comparable
    assert report.areas_matching == 1


def test_official_totals_that_give_the_category_are_not_comparable_not_a_difference():
    statements = [statement("xx/01/A"), statement("xx/01/B")]
    for official_blank in (0, 7):
        report = verify(statements, official(blank=official_blank, null=6, a=100, b=60))
        assert report.differences == [] and report.bounds == []
        (item,) = report.not_comparable
        assert (item.item, item.official, item.statements) == ("blank", official_blank, 2)
        # the other items are compared, and match
        assert report.ok and report.areas_matching == 1
    comparison = compare(statements, official(blank=7, null=6, a=100, b=60))
    text = format_comparison(comparison)
    assert "Not comparable: xx blank. The official totals give 7" in text
    assert "match the official totals in every item compared. Not compared: blank." in text
    assert comparison.to_dict()["not_comparable"][0]["official"] == 7


def test_the_other_way_round_is_not_comparable_either():
    report = verify([statement(blank=4)], official(blank=None))
    (item,) = report.not_comparable
    assert (item.item, item.official, item.recomputed) == ("blank", None, 4)
    assert report.ok and not report.differences


def test_one_statement_says_no_such_figure_and_another_gives_one_it_is_flagged_not_chosen():
    statements = [statement("xx/01/A"), statement("xx/01/B", blank=4), statement("xx/01/C")]
    totals = aggregate(statements)["xx"]
    assert totals.not_on_sheet == {"blank": 2} and totals.contradicted == {"blank": 1}
    report = verify(statements, official(blank=4, null=9, a=150, b=90))
    (found,) = report.inconsistent
    assert (found.item, found.not_on_sheet, found.with_a_figure) == ("blank", 2, 1)
    # neither a match nor a difference, whatever the official figure is
    assert report.differences == [] and report.not_comparable == []
    assert not report.ok and report.undecided and report.areas_matching == 0
    assert verify(statements, official(blank=99, null=9, a=150, b=90)).differences == []
    comparison = compare(statements, official(blank=4, null=9, a=150, b=90))
    assert comparison.official_matches == "undecided" and not comparison.ok
    text = format_comparison(comparison)
    assert "Statements do not agree on what the sheet has: xx blank" in text
    assert "2 say the sheet has no such figure, 1 give one" in text


def test_an_unread_figure_also_contradicts_a_sheet_said_not_to_have_it():
    statements = [
        statement("xx/01/A"),
        statement("xx/01/B", not_on_sheet={}, unread={"blank": "illegible"}),
    ]
    report = verify(statements, official(blank=4, null=6, a=100, b=60))
    assert [i.item for i in report.inconsistent] == ["blank"] and not report.bounds


def test_two_captures_of_one_act_that_disagree_on_what_the_sheet_has_are_a_conflict():
    without = statement()
    with_figure = statement(blank=2, evidence={"kind": "observer-capture"})
    resolution = resolve([without, with_figure])
    assert [(c.station, c.versions) for c in resolution.conflicts] == [("xx/01/A", 2)]
    # two captures that both say the sheet has no such figure are one act
    again = statement(evidence={"kind": "party-copy"})
    assert resolve([without, again]).conflicts == []


def test_between_two_acts_an_item_one_of_them_lacks_is_not_a_change():
    count = statement()
    canvass = statement(blank=2, stage="canvass", supersedes=count.statement_id())
    resolution = resolve([count, canvass])
    assert resolution.changes == [] and resolution.partly_compared == ["xx/01/A"]


def test_an_item_neither_act_has_is_not_something_left_uncompared():
    count = statement()
    canvass = statement(votes={"A": 48, "B": 30}, stage="canvass", supersedes=count.statement_id())
    resolution = resolve([count, canvass])
    (change,) = resolution.changes
    assert change.items == {"candidature:A": (50, 48)} and change.not_compared == ()
    assert resolution.partly_compared == []
