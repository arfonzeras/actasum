"""Build synthetic files in the Ministry's fixed-width layout.

These are NOT real election data. They follow the column positions the reader
expects, so they test the reader against its own understanding of the layout,
not against the Ministry's actual files.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ELECTION = ("02", "2019", "11")  # type, year, month


def _line(length: int, fields: list[tuple[int, int, object]]) -> str:
    buffer = [" "] * length
    for start, end, value in fields:
        width = end - start + 1
        text = str(value)
        text = text.rjust(width, "0") if isinstance(value, int) else text.ljust(width)
        assert len(text) == width, (start, end, value)
        buffer[start - 1 : end] = text
    return "".join(buffer)


def _head(province: str, region: str = "09") -> list[tuple[int, int, object]]:
    kind, year, month = ELECTION
    return [(1, 2, kind), (3, 6, year), (7, 8, month), (9, 9, "1"), (10, 11, region), (12, 13, province)]


def station_row(province, municipality, district, section, station, registered, blank, null, total):
    return _line(101, _head(province) + [
        (14, 16, municipality), (17, 18, district), (19, 22, section), (23, 23, station),
        (24, 30, registered), (66, 72, blank), (73, 79, null), (80, 86, total), (101, 101, "S"),
    ])


def station_candidature_row(province, municipality, district, section, station, code, votes):
    return _line(36, _head(province) + [
        (14, 16, municipality), (17, 18, district), (19, 22, section), (23, 23, station),
        (24, 29, code), (30, 36, votes),
    ])


def province_row(province, stations, blank, null, total):
    return _line(172, _head(province) + [
        (14, 14, "9"), (15, 64, "PROVINCIA " + province), (73, 77, stations),
        (126, 133, blank), (134, 141, null), (142, 149, total), (172, 172, "S"),
    ])


def province_candidature_row(province, code, votes):
    return _line(33, _head(province) + [(14, 14, "9"), (15, 20, code), (21, 28, votes)])


# (province, municipality, district, section, station) -> (registered, blank, null, {code: votes})
STATIONS = {
    ("08", "019", "01", "001 ", "A"): (500, 4, 3, {"000001": 120, "000002": 200}),
    ("08", "019", "01", "001 ", "B"): (450, 2, 1, {"000001": 90, "000002": 150}),
    ("08", "101", "02", "010 ", "U"): (300, 0, 5, {"000001": 60, "000003": 30}),
    ("28", "079", "05", "123 ", "A"): (800, 9, 7, {"000001": 300, "000002": 250, "000003": 10}),
}


def build(tmp_path: Path, *, stations=None, official_tweak=None, as_zip=True):
    """Write a synthetic MESA and TOTA dataset. Returns (mesa_path, tota_path)."""
    stations = STATIONS if stations is None else stations
    suffix = ELECTION[0] + ELECTION[1][2:] + ELECTION[2] + ".DAT"

    rows09, rows10 = [], []
    provinces: dict[str, dict] = {}
    for key, (registered, blank, null, votes) in stations.items():
        rows09.append(station_row(*key, registered, blank, null, sum(votes.values())))
        for code, count in votes.items():
            rows10.append(station_candidature_row(*key, code, count))
        p = provinces.setdefault(key[0], {"stations": 0, "blank": 0, "null": 0, "votes": {}})
        p["stations"] += 1
        p["blank"] += blank
        p["null"] += null
        for code, count in votes.items():
            p["votes"][code] = p["votes"].get(code, 0) + count
    # Overseas-vote subtotals per region and for the whole country. The real
    # per-station files carry them with province 99, municipality 999 and the
    # same station key for every region; the reader must ignore them.
    for region in ("09", "13", "99"):
        aggregate = _head("99", region) + [
            (14, 16, "999"), (17, 18, "09"), (19, 22, "0000"), (23, 23, "U"),
        ]
        rows09.append(_line(101, aggregate + [(24, 30, 9999), (80, 86, 77), (101, 101, "S")]))
        rows10.append(_line(36, aggregate + [(24, 29, "000001"), (30, 36, 77)]))
    if official_tweak:
        official_tweak(provinces)

    rows07, rows08 = [], []
    for province, p in provinces.items():
        rows07.append(province_row(province, p["stations"], p["blank"], p["null"], sum(p["votes"].values())))
        for code, count in p["votes"].items():
            rows08.append(province_candidature_row(province, code, count))
    # National subtotal rows (province 99) that the reader must ignore.
    rows07.append(province_row("99", 9999, 1, 1, 1))
    rows08.append(province_candidature_row("99", "000001", 1))

    def write(name: str, members: dict[str, list[str]]) -> Path:
        if as_zip:
            path = tmp_path / f"{name}.zip"
            with zipfile.ZipFile(path, "w") as archive:
                for member, lines in members.items():
                    archive.writestr(member, ("\r\n".join(lines) + "\r\n").encode("iso-8859-1"))
            return path
        path = tmp_path / name
        path.mkdir()
        for member, lines in members.items():
            (path / member).write_bytes(("\n".join(lines) + "\n").encode("iso-8859-1"))
        return path

    mesa = write("02201911_MESA", {"09" + suffix: rows09, "10" + suffix: rows10})
    tota = write("02201911_TOTA", {"07" + suffix: rows07, "08" + suffix: rows08})
    return mesa, tota
