"""Official totals that count a candidature's votes as another item.

An authority may count the votes cast for a candidature as null, blank or
another category, as when a candidate withdrew after the ballots were set.
The statements keep what the sheet says. The official totals declare the
reclassification in ``count_as``; the verifier counts the statements the same
way before comparing, and always says that it did, with the figures.
"""

import json

import pytest

from actasum.statement import AreaTotals, FormatError, OfficialTotals, Statement
from actasum.verify import aggregate, compare, format_comparison, format_report, verify

ELECTION = "xx/e/2026-01"


def statement(station, votes, *, blank=2, null=3, unread=None):
    return Statement(
        profile="xx/test/v0", election=ELECTION, station=station, constituency="xx",
        blank=blank, null=null, candidatures=votes, unread=unread or {},
    )  # fmt: skip


STATEMENTS = [
    statement("xx/01/A", {"A": 50, "B": 30, "W": 1}),
    statement("xx/01/B", {"A": 40, "B": 20, "W": 2}),
]


def official(doc_area, **top):
    doc = {
        "spec": "actasum/official-totals/v0.1",
        "profile": "xx/test/v0",
        "election": ELECTION,
        "areas": {"xx": doc_area},
        **top,
    }
    return OfficialTotals.from_dict(json.loads(json.dumps(doc)))


def test_without_the_declaration_the_votes_are_a_difference():
    totals = official({"candidatures": {"A": 90, "B": 50}, "blank": 4, "null": 9})
    report = verify(STATEMENTS, totals)
    assert not report.ok
    assert {(d.item, d.delta) for d in report.differences} == {
        ("null", -3),
        ("candidature:W", 3),
    }
    assert report.counted_as == []
    assert "counted_as_the_official_totals_declare" not in report.to_dict()


def test_counted_as_null_matches_and_says_so():
    totals = official(
        {"candidatures": {"A": 90, "B": 50}, "blank": 4, "null": 9, "candidature_total": 140},
        count_as={"W": "null"},
    )
    report = verify(STATEMENTS, totals)
    assert report.ok
    [moved] = report.counted_as
    assert (moved.area, moved.candidature, moved.counted_as) == ("xx", "W", "null")
    assert (moved.votes, moved.statements, moved.unread) == (3, 2, 0)
    assert report.to_dict()["counted_as_the_official_totals_declare"] == [
        {"area": "xx", "candidature": "W", "counted_as": "null", "votes": 3,
         "statements": 2, "statements_with_the_figure_unread": 0}
    ]  # fmt: skip
    text = format_report(report)
    assert "3 votes of candidature W, from 2 statements, compared as null" in text
    assert "because the official totals declare that they count them so" in text
    assert text.splitlines()[-1].startswith("Result: recomputed totals match")
    assert "Some votes were compared as another item" in text.splitlines()[-1]


def test_counted_as_blank_and_as_another_category():
    as_blank = official(
        {"candidatures": {"A": 90, "B": 50}, "blank": 7, "null": 6}, count_as={"W": "blank"}
    )
    assert verify(STATEMENTS, as_blank).ok
    as_other = official(
        {"candidatures": {"A": 90, "B": 50}, "blank": 4, "null": 6, "other": {"withdrawn": 3}},
        count_as={"W": "other:withdrawn"},
    )
    report = verify(STATEMENTS, as_other)
    assert report.ok
    assert report.counted_as[0].counted_as == "other:withdrawn"


def test_the_statements_keep_what_the_sheet_says():
    before = [s.statement_id() for s in STATEMENTS]
    totals = official(
        {"candidatures": {"A": 90, "B": 50}, "blank": 4, "null": 9}, count_as={"W": "null"}
    )
    verify(STATEMENTS, totals)
    assert [s.statement_id() for s in STATEMENTS] == before
    assert STATEMENTS[0].candidatures["W"] == 1


def test_a_difference_left_after_counting_as_is_still_reported_with_the_move():
    totals = official(
        {"candidatures": {"A": 90, "B": 50}, "blank": 4, "null": 10}, count_as={"W": "null"}
    )
    report = verify(STATEMENTS, totals)
    assert not report.ok
    assert [(d.item, d.delta) for d in report.differences] == [("null", -1)]
    assert len(report.counted_as) == 1
    assert "compared as null" in format_report(report)


def test_an_unread_figure_moves_with_its_candidature():
    statements = [
        statement("xx/01/A", {"A": 50, "B": 30}, unread={"candidature:W": "illegible"}),
        statement("xx/01/B", {"A": 40, "B": 20, "W": 2}),
    ]
    totals = official(
        {"candidatures": {"A": 90, "B": 50}, "blank": 4, "null": 9, "candidature_total": 140},
        count_as={"W": "null"},
    )
    report = verify(statements, totals)
    # Null votes are now a lower bound (8 at least, against 9): nothing is
    # said about them. The candidature total is not a bound.
    assert [(b.item, b.recomputed, b.official) for b in report.bounds] == [("null", 8, 9)]
    assert report.differences == []
    assert report.counted_as[0].unread == 1
    assert "at least that many, since 1 statement could not read it" in format_report(report)
    area = aggregate(statements, count_as={"W": "null"})["xx"]
    assert "candidature_total" not in area.unread


def test_both_sums_report_it():
    totals = official(
        {"candidatures": {"A": 90, "B": 50}, "blank": 4, "null": 9}, count_as={"W": "null"}
    )
    comparison = compare(STATEMENTS, totals)
    assert comparison.ok
    assert "compared as null" in format_comparison(comparison)
    assert comparison.to_dict()["counted_as_the_official_totals_declare"]


def test_written_only_when_declared():
    plain = official({"candidatures": {"A": 90}, "blank": 4, "null": 6})
    assert "count_as" not in plain.to_dict()
    declared = official({"candidatures": {"A": 90}, "blank": 4, "null": 6}, count_as={"W": "null"})
    assert declared.to_dict()["count_as"] == {"W": "null"}
    assert OfficialTotals.from_dict(declared.to_dict()) == declared


@pytest.mark.parametrize(
    "top, area, message",
    [
        ({"count_as": {"W": "candidature:A"}}, {}, "must be null, blank or other"),
        ({"count_as": {"W": "other:"}}, {}, "must be null, blank or other"),
        ({"count_as": {"W": "null"}, "merge": {"W": "A"}}, {}, "both merged and counted"),
        ({"count_as": {"W": "null"}}, {"W": 3}, "cannot also have a figure of its own"),
        ({"count_as": ["W"]}, {}, "count_as must map"),
    ],
)
def test_declarations_that_cannot_be_read(top, area, message):
    with pytest.raises(FormatError, match=message):
        official({"candidatures": {"A": 90, **area}, "blank": 4, "null": 6}, **top)


def test_area_totals_without_the_declaration_are_unchanged():
    area = aggregate(STATEMENTS)["xx"]
    assert area.candidatures == {"A": 90, "B": 50, "W": 3}
    assert area.counted_as == {}
    assert isinstance(area, AreaTotals)
