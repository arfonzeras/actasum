"""Several statements per station: captures of one act, and successive acts."""

import io
import json
from dataclasses import replace

import pytest

from actasum.cli import main
from actasum.log import Log
from actasum.statement import (
    AreaTotals,
    FormatError,
    OfficialTotals,
    Statement,
    write_jsonl,
)
from actasum.verify import compare, resolve

ELECTION = "xx/test/2026-01"


def make(station, votes, *, blank=1, null=0, **kwargs):
    return Statement(
        profile="xx/test/v0", election=ELECTION, station=station, constituency="xx/1",
        blank=blank, null=null, candidatures=dict(votes), **kwargs,
    )


def official(votes, *, blank, null=0, stations=2):
    return OfficialTotals(
        profile="xx/test/v0", election=ELECTION,
        areas={"xx/1": AreaTotals(blank=blank, null=null, candidatures=dict(votes),
                                  stations=stations, candidature_total=sum(votes.values()))},
    )


A = make("xx/1/a", {"p": 10, "q": 5})
B = make("xx/1/b", {"p": 7, "q": 8})
# The general canvass corrects station b: two votes move from q to p.
B_CANVASS = make("xx/1/b", {"p": 9, "q": 6}, stage="canvass",
                 supersedes=B.statement_id(), evidence={"kind": "official-publication"})
COUNTED = official({"p": 17, "q": 13}, blank=2)
STANDING = official({"p": 19, "q": 11}, blank=2)


def test_default_stage_leaves_the_statement_and_its_identifier_untouched():
    doc = A.to_dict()
    assert "stage" not in doc and "supersedes" not in doc
    assert Statement.from_dict(doc).statement_id() == A.statement_id()
    assert replace(A, stage="count").statement_id() == A.statement_id()


def test_stage_and_supersedes_round_trip():
    again = Statement.from_dict(json.loads(B_CANVASS.canonical()))
    assert (again.stage, again.supersedes) == ("canvass", B.statement_id())
    assert again.statement_id() == B_CANVASS.statement_id() != B.statement_id()


@pytest.mark.parametrize("patch", [{"stage": "recount"}, {"supersedes": "b"}, {"supersedes": 3},
                                   {"evidence": {"kind": 1}}])
def test_bad_stage_supersedes_or_evidence_is_refused(patch):
    with pytest.raises(FormatError):
        Statement.from_dict({**A.to_dict(), **patch})


def test_one_statement_per_station_is_the_plain_case():
    result = compare([A, B], COUNTED)
    assert result.resolution.plain
    assert (result.ok, result.official_matches) == (True, "both")
    assert "as_counted" not in result.to_dict()


def test_two_captures_of_the_same_sheet_count_once():
    copy = replace(B, evidence={"kind": "observer-capture", "sha256": "sha256:" + "0" * 64})
    result = compare([A, B, copy, B], COUNTED)
    assert result.resolution.statements == 3
    assert len(result.resolution.counted) == 2
    assert (result.ok, result.official_matches) == (True, "both")


def test_captures_that_disagree_leave_the_station_out_of_both_sums():
    other = replace(B, candidatures={"p": 8, "q": 7}, evidence={"kind": "party-copy"})
    result = compare([A, B, other], COUNTED)
    (conflict,) = result.resolution.conflicts
    assert (conflict.station, conflict.stage, conflict.statements, conflict.versions) == (
        "xx/1/b", "count", 2, 2)
    assert [s.station for s in result.resolution.counted] == ["xx/1/a"]
    assert [s.station for s in result.resolution.standing] == ["xx/1/a"]
    assert not result.ok and result.official_matches == "neither"


def test_a_later_act_changes_what_stands_but_not_what_was_counted():
    resolution = resolve([A, B, B_CANVASS])
    assert sorted(s.candidatures["p"] for s in resolution.counted) == [7, 10]
    assert sorted(s.candidatures["p"] for s in resolution.standing) == [9, 10]
    (change,) = resolution.changes
    assert (change.station, change.stage, change.source) == (
        "xx/1/b", "canvass", "official-publication")
    assert change.items == {"candidature:p": (7, 9), "candidature:q": (8, 6)}


def test_official_totals_are_matched_against_both_sums():
    statements = [A, B, B_CANVASS]
    assert compare(statements, STANDING).official_matches == "as standing"
    assert compare(statements, COUNTED).official_matches == "as counted"
    assert compare(statements, official({"p": 1}, blank=0)).official_matches == "neither"
    assert compare(statements, STANDING).ok


def test_chain_of_acts_leaves_the_last_one_standing():
    ruling = make("xx/1/b", {"p": 8, "q": 7}, stage="ruling",
                  supersedes=B_CANVASS.statement_id())
    (standing_b,) = [s for s in resolve([A, B, B_CANVASS, ruling]).standing
                     if s.station == "xx/1/b"]
    assert standing_b.stage == "ruling"


def test_acts_with_no_link_between_them_are_undetermined():
    loose = replace(B_CANVASS, supersedes=None)
    result = compare([A, B, loose], STANDING)
    assert result.resolution.undetermined == ["xx/1/b"]
    assert [s.station for s in result.resolution.standing] == ["xx/1/a"]
    assert result.counted.ok is False and not result.ok


def test_a_later_act_stands_even_if_the_count_is_in_conflict():
    other = replace(B, candidatures={"p": 8, "q": 7})
    result = compare([A, B, other, B_CANVASS], STANDING)
    assert len(result.resolution.conflicts) == 1
    assert result.official_matches == "as standing"
    assert not result.ok  # the conflict about the count is still there to explain


def test_later_act_without_the_count_and_unknown_supersedes_are_listed():
    resolution = resolve([A, B_CANVASS])
    assert resolution.without_count == ["xx/1/b"]
    assert resolution.dangling == ["xx/1/b"]
    assert len(resolution.standing) == 2 and len(resolution.counted) == 1


def test_cli_shows_both_sums_and_says_which_one_matches(tmp_path, capsys):
    statements = tmp_path / "statements.jsonl"
    with open(statements, "w", encoding="utf-8") as handle:
        write_jsonl([A, B, B_CANVASS], handle)
    totals = tmp_path / "official.json"
    totals.write_text(json.dumps(STANDING.to_dict()))
    assert main(["verify", "--statements", str(statements), "--official", str(totals)]) == 0
    out = capsys.readouterr().out
    assert "--- AS COUNTED AT THE STATIONS ---" in out
    assert "--- AS LEFT STANDING ---" in out
    assert "candidature:p: counted 7, standing 9 (+2)" in out
    assert "match what was left standing, not what the stations counted" in out
    assert main(["verify", "--statements", str(statements), "--official", str(totals),
                 "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["official_matches"] == "as standing"
    assert doc["as_counted"]["ok"] is False
    assert doc["stations_changed"][0]["items"]["candidature:p"] == {"earlier": 7, "standing": 9}


def test_the_log_keeps_every_statement_of_a_station(tmp_path):
    log = Log.create(str(tmp_path / "log"), "actasum/test")
    assert log.append([A, B, B_CANVASS]) == (3, 0)
    assert len(log.find("xx/1/b")) == 2
    reopened = Log.open(str(tmp_path / "log"))
    buffer = io.StringIO("".join(leaf.decode() + "\n" for leaf in reopened.leaves))
    from actasum.statement import read_jsonl

    assert compare(list(read_jsonl(buffer)), STANDING).official_matches == "as standing"
