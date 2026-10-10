import json

import pytest

import synth
from tallylog.cli import main
from tallylog.profiles.es import infoelectoral
from tallylog.statement import FormatError
from tallylog.verify import VerificationError, verify


def load(tmp_path, **kwargs):
    mesa, tota = synth.build(tmp_path, **kwargs)
    statements = infoelectoral.read_statements(infoelectoral.load_dataset(str(mesa)))
    totals = infoelectoral.read_official_totals(infoelectoral.load_dataset(str(tota)))
    return statements, totals


def test_reader_extracts_station_fields(tmp_path):
    statements, _ = load(tmp_path)
    by_id = {s.station: s for s in statements}
    assert set(by_id) == {
        "es/08/019/01/001/A",
        "es/08/019/01/001/B",
        "es/08/101/02/010/U",
        "es/28/079/05/123/A",
    }
    s = by_id["es/28/079/05/123/A"]
    assert s.election == "es/congreso/2019-11"
    assert s.constituency == "es/28"
    assert (s.registered, s.blank, s.null, s.candidature_total) == (800, 9, 7, 560)
    assert s.candidatures == {"000001": 300, "000002": 250, "000003": 10}
    assert s.evidence["kind"] == "official-dataset"
    assert s.evidence["sha256"].startswith("sha256:")


def test_reader_ignores_national_subtotals(tmp_path):
    _, totals = load(tmp_path)
    assert set(totals.constituencies) == {"es/08", "es/28"}
    assert totals.constituencies["es/08"].stations == 3
    assert totals.constituencies["es/08"].candidatures == {
        "000001": 270,
        "000002": 350,
        "000003": 30,
    }


def test_directory_input_gives_the_same_statements(tmp_path):
    (tmp_path / "z").mkdir()
    (tmp_path / "d").mkdir()
    from_zip, _ = load(tmp_path / "z")
    from_dir, _ = load(tmp_path / "d", as_zip=False)
    strip = lambda s: {k: v for k, v in s.to_dict().items() if k != "evidence"}
    assert [strip(s) for s in from_zip] == [strip(s) for s in from_dir]


def test_matching_data_verifies(tmp_path):
    report = verify(*load(tmp_path))
    assert report.ok
    assert report.stations == 4
    assert (report.constituencies_checked, report.constituencies_matching) == (2, 2)
    assert report.station_issues == []


def test_altered_official_total_is_reported(tmp_path):
    def tweak(provinces):
        provinces["08"]["votes"]["000001"] += 25

    report = verify(*load(tmp_path, official_tweak=tweak))
    assert not report.ok
    assert report.constituencies_matching == 1
    assert {(d.constituency, d.item, d.delta) for d in report.differences} == {
        ("es/08", "candidature:000001", -25),
        ("es/08", "candidature_total", -25),
    }


def test_candidature_only_on_one_side_is_reported(tmp_path):
    def tweak(provinces):
        provinces["28"]["votes"]["000009"] = 5

    report = verify(*load(tmp_path, official_tweak=tweak))
    assert ("es/28", "candidature:000009", -5) in {
        (d.constituency, d.item, d.delta) for d in report.differences
    }


def test_missing_station_changes_count_and_totals(tmp_path):
    statements, totals = load(tmp_path)
    report = verify([s for s in statements if s.station != "es/08/101/02/010/U"], totals)
    items = {d.item: d.delta for d in report.differences if d.constituency == "es/08"}
    assert items["stations"] == -1
    assert items["null"] == -5
    assert items["candidature:000003"] == -30


def test_missing_constituency_is_a_gap_not_a_match(tmp_path):
    statements, totals = load(tmp_path)
    report = verify([s for s in statements if s.constituency == "es/08"], totals)
    assert not report.ok
    assert report.missing_statements == ["es/28"]


def test_station_internal_inconsistencies(tmp_path):
    stations = dict(synth.STATIONS)
    stations[("28", "079", "05", "123 ", "A")] = (100, 9, 7, {"000001": 300})
    statements, totals = load(tmp_path, stations=stations)
    codes = {i.code for i in verify(statements, totals).station_issues}
    assert codes == {"more-ballots-than-registered"}


def test_duplicate_statement_is_refused(tmp_path):
    statements, totals = load(tmp_path)
    with pytest.raises(VerificationError, match="more than one statement"):
        verify(statements + [statements[0]], totals)


def test_wrong_election_is_refused(tmp_path):
    statements, totals = load(tmp_path)
    other = type(totals)(
        profile=totals.profile, election="es/congreso/2023-07",
        constituencies=totals.constituencies,
    )
    with pytest.raises(VerificationError, match="belongs to election"):
        verify(statements, other)


def test_short_line_is_a_format_error(tmp_path):
    mesa, _ = synth.build(tmp_path, as_zip=False)
    target = mesa / "09021911.DAT"
    target.write_text(target.read_text(encoding="iso-8859-1")[:40] + "\n", encoding="iso-8859-1")
    with pytest.raises(FormatError, match="expected at least 86"):
        infoelectoral.read_statements(infoelectoral.load_dataset(str(mesa)))


def test_unsupported_election_type(tmp_path, monkeypatch):
    monkeypatch.setattr(synth, "ELECTION", ("04", "2019", "05"))
    mesa, _ = synth.build(tmp_path)
    with pytest.raises(FormatError, match="not supported"):
        infoelectoral.read_statements(infoelectoral.load_dataset(str(mesa)))


def test_cli_replay_and_exit_codes(tmp_path, capsys):
    (tmp_path / "ok").mkdir()
    (tmp_path / "bad").mkdir()
    mesa, tota = synth.build(tmp_path / "ok")
    assert main(["es", "replay", "--mesa", str(mesa), "--tota", str(tota)]) == 0
    assert "match the official totals" in capsys.readouterr().out

    def tweak(provinces):
        provinces["28"]["null"] += 1

    mesa, tota = synth.build(tmp_path / "bad", official_tweak=tweak)
    assert main(["es", "replay", "--mesa", str(mesa), "--tota", str(tota), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False
    assert report["differences"] == [
        {"constituency": "es/28", "item": "null", "recomputed": 7, "official": 8, "delta": -1}
    ]
    assert main(["es", "replay", "--mesa", str(tmp_path / "nope.zip"), "--tota", str(tota)]) == 2


def test_cli_two_step_pipeline_matches_replay(tmp_path, capsys):
    mesa, tota = synth.build(tmp_path)
    statements, official = tmp_path / "statements.jsonl", tmp_path / "official.json"
    assert main(["es", "convert", "--mesa", str(mesa), "--out", str(statements)]) == 0
    assert main(["es", "official", "--tota", str(tota), "--out", str(official)]) == 0
    capsys.readouterr()
    assert main(["verify", "--statements", str(statements), "--official", str(official)]) == 0
    assert "Polling stations read: 4" in capsys.readouterr().out
    assert len(statements.read_text(encoding="utf-8").splitlines()) == 4


def test_reader_ignores_overseas_subtotals_in_station_files(tmp_path):
    statements, _ = load(tmp_path)
    assert not [s for s in statements if s.station.startswith("es/99/")]
    assert len(statements) == len(synth.STATIONS)


def test_real_station_row_layout():
    """Two rows copied from 09021911.DAT (Congreso, November 2019)."""
    rows = [
        "022019111010400302001 B00004460000446000000000000000000141000021500000010000000000027000000000000000S",
        "0220191110407999090000U00283150028315000000000000000000000000000000000060000009000132400000000000000S",
    ]
    dataset = infoelectoral.Dataset(
        path="sample", sha256=None,
        files={"09": ("09021911.DAT", rows), "10": ("10021911.DAT", [])},
    )
    first, overseas = infoelectoral.read_statements(dataset)
    assert first.station == "es/04/003/02/001/B"
    assert (first.registered, first.blank, first.null, first.candidature_total) == (446, 1, 0, 270)
    assert overseas.station == "es/07/999/09/0000/U"
    assert (overseas.blank, overseas.null, overseas.candidature_total) == (6, 9, 1324)
