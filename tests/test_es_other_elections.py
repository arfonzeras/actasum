"""Local and European Parliament elections: a different constituency each.

Synthetic data only. The layout is the Ministry's documented one; whether the
real files of these election types follow it is for a real run to tell.
"""

import zipfile

import pytest

import synth
from actasum.cli import main
from actasum.profiles.es import infoelectoral
from actasum.statement import FormatError, OfficialTotals
from actasum.verify import verify


def write_zip(path, members):
    with zipfile.ZipFile(path, "w") as archive:
        for name, lines in members.items():
            archive.writestr(name, ("\r\n".join(lines) + "\r\n").encode("iso-8859-1"))
    return str(path)


def candidature_row(code, national_head="000000"):
    kind, year, month = synth.ELECTION
    return synth._line(232, [
        (1, 2, kind), (3, 6, year), (7, 8, month), (9, 14, code), (15, 64, "SIGLAS " + code),
        (215, 220, code), (221, 226, code), (227, 232, national_head),
    ])


def national_row(stations, blank, null, total):
    return synth._line(172, synth._head("99", "99") + [
        (14, 14, "9"), (15, 64, "TOTAL NACIONAL"), (73, 77, stations),
        (126, 133, blank), (134, 141, null), (142, 149, total), (172, 172, "S"),
    ])


def national_candidature_row(code, votes):
    return synth._line(33, synth._head("99", "99") + [(14, 14, "9"), (15, 20, code), (21, 28, votes)])


# ---------------------------------------------------------------- local


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setattr(synth, "ELECTION", ("04", "2023", "05"))
    mesa, _ = synth.build(tmp_path)
    return mesa


def test_local_election_constituency_is_the_municipality(local):
    dataset = infoelectoral.load_dataset(str(local))
    statements = infoelectoral.read_statements(dataset)
    assert {s.election for s in statements} == {"es/municipales/2023-05"}
    assert {s.constituency for s in statements} == {"es/08/019", "es/08/101", "es/28/079"}
    totals = infoelectoral.read_official_totals(dataset)
    assert (totals.level, totals.grouping) == ("constituency", "constituency")
    report = verify(statements, totals)
    assert report.ok
    assert (report.areas_checked, report.areas_matching) == (3, 3)


def test_local_election_difference_is_reported_per_municipality(tmp_path, monkeypatch):
    monkeypatch.setattr(synth, "ELECTION", ("04", "2023", "05"))

    def tweak(municipalities):
        municipalities[("08", "101")]["votes"]["000003"] += 2

    mesa, _ = synth.build(tmp_path, municipal_tweak=tweak)
    assert main(["es", "replay", "--mesa", str(mesa)]) == 1


def test_local_election_has_no_overseas_level(local, capsys):
    assert main(["es", "replay", "--mesa", str(local), "--level", "overseas"]) == 2
    assert "no overseas rows" in capsys.readouterr().err


def test_files_of_another_election_type_are_set_aside(tmp_path, monkeypatch):
    # The local-election ZIP also carries provincial-council files (type 10)
    # that reuse file numbers 05 to 08.
    monkeypatch.setattr(synth, "ELECTION", ("04", "2023", "05"))
    mesa, _ = synth.build(tmp_path, as_zip=False)
    for number in ("05", "07"):
        (mesa / f"{number}102305.DAT").write_text("10202305 something else\n")
    dataset = infoelectoral.load_dataset(str(mesa))
    assert dataset.kind == "04"
    assert dataset.other == ("05102305.DAT", "07102305.DAT")
    assert verify(
        infoelectoral.read_statements(dataset), infoelectoral.read_official_totals(dataset)
    ).ok


# ------------------------------------------------------------- european

# Candidatures 000002 and 000003 are the same list under two regional names:
# the national totals report both under 000002.
EU_STATIONS = {
    **synth.STATIONS,
    ("08", "999", "09", "0000", "U"): (700, 1, 2, {"000001": 40, "000003": 5}),
}


def build_european(tmp_path, *, with_candidatures=True, national_tweak=None):
    mesa, _ = synth.build(tmp_path, stations=EU_STATIONS, as_zip=False)
    suffix = "072406.DAT"
    blank = sum(v[1] for v in EU_STATIONS.values())
    null = sum(v[2] for v in EU_STATIONS.values())
    votes = {"000001": 0, "000002": 0}
    for *_, per_station in EU_STATIONS.values():
        for code, count in per_station.items():
            votes["000002" if code == "000003" else code] += count
    if national_tweak:
        national_tweak(votes)
    stations = sum(1 for key in EU_STATIONS if key[1] != "999")
    with open(mesa / ("07" + suffix), "a", encoding="iso-8859-1") as handle:
        handle.write(national_row(stations, blank, null, sum(votes.values())) + "\n")
    with open(mesa / ("08" + suffix), "a", encoding="iso-8859-1") as handle:
        for code, count in votes.items():
            handle.write(national_candidature_row(code, count) + "\n")
    if with_candidatures:
        rows = [candidature_row("000001", "000001"), candidature_row("000002", "000002"),
                candidature_row("000003", "000002")]
        (mesa / ("03" + suffix)).write_text("\n".join(rows) + "\n", encoding="iso-8859-1")
    return str(mesa)


@pytest.fixture
def european(monkeypatch):
    monkeypatch.setattr(synth, "ELECTION", ("07", "2024", "06"))


def test_european_election_is_one_national_constituency(tmp_path, european):
    dataset = infoelectoral.load_dataset(build_european(tmp_path))
    statements = infoelectoral.read_statements(dataset)
    assert {s.election for s in statements} == {"es/europeas/2024-06"}
    assert {s.constituency for s in statements} == {"es"}
    totals = infoelectoral.read_official_totals(dataset)
    assert set(totals.areas) == {"es"}
    assert totals.merge == {"000003": "000002"}
    report = verify(statements, totals)
    assert report.ok, report.differences
    assert (report.stations, report.aggregates, report.aggregates_left_out) == (4, 1, 0)


def test_european_totals_without_the_candidature_file_do_not_merge(tmp_path, european):
    dataset = infoelectoral.load_dataset(build_european(tmp_path, with_candidatures=False))
    totals = infoelectoral.read_official_totals(dataset)
    assert totals.merge == {}
    report = verify(infoelectoral.read_statements(dataset), totals)
    assert {d.item for d in report.differences} == {"candidature:000002", "candidature:000003"}


def test_european_national_difference_is_reported(tmp_path, european):
    def tweak(votes):
        votes["000001"] += 3

    path = build_european(tmp_path, national_tweak=tweak)
    assert main(["es", "replay", "--mesa", path]) == 1


def test_merge_survives_the_two_step_pipeline(tmp_path, european):
    dataset = infoelectoral.load_dataset(build_european(tmp_path))
    totals = infoelectoral.read_official_totals(dataset)
    assert OfficialTotals.from_dict(totals.to_dict()).merge == totals.merge
    with pytest.raises(FormatError, match="merge"):
        OfficialTotals.from_dict({**totals.to_dict(), "merge": {"000003": 2}})


def test_province_level_counts_the_overseas_row_in_its_province(tmp_path, european, capsys):
    path = build_european(tmp_path)
    assert main(["es", "replay", "--mesa", path, "--level", "province"]) == 0
    out = capsys.readouterr().out
    assert "Level: province" in out
    assert "Provinces compared: 2 (2 match the official totals)" in out
    assert "left out" not in out


def test_municipality_level_still_leaves_the_overseas_row_out(tmp_path, european, capsys):
    path = build_european(tmp_path)
    assert main(["es", "replay", "--mesa", path, "--level", "municipality"]) == 0
    assert "Aggregate rows left out at this level: 1" in capsys.readouterr().out


def test_describe_lists_files_and_merged_candidatures(tmp_path, european, capsys):
    import json

    assert main(["es", "describe", "--mesa", build_european(tmp_path)]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert (doc["election_type"], doc["supported"]) == ("07", True)
    by_number = {entry["file"][:2]: entry for entry in doc["files"]}
    assert by_number["03"]["merged_under_another_code_national"] == 1
    assert by_number["07"]["national_rows"] == 1
    assert by_number["09"]["overseas_rows_municipality_999"] == 1
