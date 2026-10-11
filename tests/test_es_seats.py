"""Seat allocation (LOREG arts. 163.1 and 180) and the local-election check."""

import json

import pytest

import synth
from actasum.cli import main
from actasum.profiles.es.seats import allocate


def test_worked_example_of_article_163():
    # The example printed in the law: 480,000 valid votes, eight seats.
    votes = {"A": 168000, "B": 104000, "C": 72000, "D": 64000, "E": 40000, "F": 32000}
    assert allocate(votes, 0, 8, 3).seats == {"A": 4, "B": 2, "C": 1, "D": 1}


def test_threshold_counts_blank_votes_as_valid():
    votes = {"A": 900, "B": 50}
    # 50 of 950 valid votes is above 5 per cent; of 1,050 it is below.
    assert allocate(votes, 0, 20, 5).seats == {"A": 19, "B": 1}
    assert allocate(votes, 100, 20, 5).seats == {"A": 20}


def test_equal_quotients_go_to_the_candidature_with_more_votes():
    # Third seat: 201/3 = 67 against 134/2 = 67.
    result = allocate({"A": 201, "B": 134}, 0, 4, 5)
    assert result.seats == {"A": 3, "B": 1}
    assert not result.by_lot


def test_equal_quotients_and_equal_votes_are_left_to_the_lot():
    assert allocate({"A": 100, "B": 100}, 0, 3, 5).by_lot
    assert not allocate({"A": 100, "B": 100}, 0, 2, 5).by_lot


def put(line, start, end, value):
    return line[: start - 1] + str(value).rjust(end - start + 1, "0") + line[end:]


def local_dataset(tmp_path, monkeypatch, seats, published, municipal_tweak=None):
    """A synthetic local election with seats written into files 05 and 06."""
    monkeypatch.setattr(synth, "ELECTION", ("04", "2023", "05"))
    mesa, _ = synth.build(tmp_path, as_zip=False, municipal_tweak=municipal_tweak)
    path05, path06 = mesa / "05042305.DAT", mesa / "06042305.DAT"
    path05.write_text(
        "\n".join(put(line, 214, 216, seats) for line in path05.read_text().splitlines()) + "\n"
    )
    lines = []
    for line in path06.read_text().splitlines():
        key = (line[9:14], line[16:22])  # province + municipality, candidature
        whole = line[14:16] == "99"
        lines.append(put(line, 31, 33, published.get(key, 0) if whole else 0))
    path06.write_text("\n".join(lines) + "\n")
    return str(mesa)


# Seven seats per municipality, allocated from the votes in synth.STATIONS.
PUBLISHED = {
    ("08019", "000001"): 2, ("08019", "000002"): 5,
    ("08101", "000001"): 5, ("08101", "000003"): 2,
    ("28079", "000001"): 4, ("28079", "000002"): 3,
}


def test_cli_seats_agree_when_votes_agree(tmp_path, monkeypatch, capsys):
    path = local_dataset(tmp_path, monkeypatch, 7, PUBLISHED)
    assert main(["es", "seats", "--mesa", path]) == 0
    out = capsys.readouterr().out
    assert "Municipalities compared: 3" in out
    assert "lead to the published seats everywhere" in out


def test_cli_seats_reports_a_changed_allocation(tmp_path, monkeypatch, capsys):
    # The municipal file gives candidature 000003 enough votes for a third
    # seat in es/08/101; the stations do not.
    def tweak(municipalities):
        municipalities[("08", "101")]["votes"]["000003"] += 20

    published = {**PUBLISHED, ("08101", "000001"): 4, ("08101", "000003"): 3}
    path = local_dataset(tmp_path, monkeypatch, 7, published, municipal_tweak=tweak)
    assert main(["es", "seats", "--mesa", path, "--json"]) == 1
    doc = json.loads(capsys.readouterr().out)
    (row,) = doc["municipalities_where_an_allocation_differs"]
    assert row["area"] == "es/08/101"
    assert row["published"] == row["from_published_votes"] == {"000001": 4, "000003": 3}
    assert row["from_station_votes"] == {"000001": 5, "000003": 2}


def test_cli_seats_is_for_local_elections_only(tmp_path, capsys):
    mesa, _ = synth.build(tmp_path)
    assert main(["es", "seats", "--mesa", str(mesa)]) == 2
    assert "only read for local elections" in capsys.readouterr().err
