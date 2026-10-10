"""Reader for the result files published by the Spanish Ministry of the Interior.

The Ministry publishes one ZIP per election and level at
https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/
Each ZIP holds fixed-width ``.DAT`` text files encoded in ISO-8859-1 and named
``NNTTYYMM.DAT`` (NN = file number, TT = election type, YY = year, MM = month).

Files used here:

* ``_MESA`` ZIP: 09 (one row per polling station) and 10 (one row per polling
  station and candidature).
* ``_TOTA`` ZIP: 07 (one row per province or higher) and 08 (one row per
  province or higher and candidature).

Column positions follow the record layout documented by the Ministry, as
implemented in the rOpenSpain ``infoelectoral`` R package. They have been
exercised here against synthetic files only; see docs/spec/profile-es.md.
"""

from __future__ import annotations

import hashlib
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Iterator

from ...statement import ConstituencyTotals, FormatError, OfficialTotals, Statement
from . import PROFILE

ENCODING = "iso-8859-1"

# Election types whose constituency is the province, which is the unit the
# Ministry's totals files report. Other types need their own mapping.
ELECTION_TYPES = {"02": "congreso"}

# Province code 99 marks rows that are subtotals, not a province: national and
# regional totals in files 07/08, and overseas-vote (CERA) totals per region in
# the per-station files 09/10. The same votes also appear under their province.
AGGREGATE_PROVINCE = "99"

_MEMBER = re.compile(r"^(\d{2})(\d{2})(\d{2})(\d{2})\.DAT$", re.IGNORECASE)


@dataclass(frozen=True)
class Dataset:
    """The ``.DAT`` files of one ZIP (or directory), keyed by file number."""

    path: str
    sha256: str | None
    files: dict[str, tuple[str, list[str]]]  # number -> (member name, lines)

    def lines(self, number: str) -> list[str]:
        if number not in self.files:
            raise FormatError(f"{self.path}: no file {number}TTYYMM.DAT found")
        return self.files[number][1]

    def name(self, number: str) -> str:
        return self.files[number][0]


def load_dataset(path: str) -> Dataset:
    """Read every ``NNTTYYMM.DAT`` member of a ZIP file or directory."""
    files: dict[str, tuple[str, list[str]]] = {}
    digest: str | None = None

    def add(name: str, raw: bytes) -> None:
        match = _MEMBER.match(os.path.basename(name))
        if not match:
            return
        number = match.group(1)
        if number in files:
            raise FormatError(f"{path}: more than one file numbered {number}")
        files[number] = (os.path.basename(name), raw.decode(ENCODING).splitlines())

    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isfile(full) and _MEMBER.match(name):
                with open(full, "rb") as handle:
                    add(name, handle.read())
    else:
        with open(path, "rb") as handle:
            digest = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if not info.is_dir():
                        add(info.filename, archive.read(info))
        except zipfile.BadZipFile as exc:
            raise FormatError(f"{path}: not a ZIP file") from exc
    if not files:
        raise FormatError(f"{path}: no NNTTYYMM.DAT files found")
    return Dataset(path=path, sha256=digest, files=files)


def _field(line: str, start: int, end: int) -> str:
    """Slice using the 1-based inclusive positions of the record layout."""
    return line[start - 1 : end]


def _number(line: str, start: int, end: int, where: str) -> int:
    text = _field(line, start, end).strip()
    if not text:
        return 0
    if not text.isdigit():
        raise FormatError(f"{where}: columns {start}-{end} are not a number: {text!r}")
    return int(text)


def _rows(dataset: Dataset, number: str, min_length: int) -> Iterator[tuple[str, str]]:
    """Yield (location, line) for every row that belongs to a province."""
    name = dataset.name(number)
    for index, line in enumerate(dataset.lines(number), start=1):
        if not line.strip():
            continue
        where = f"{name}:{index}"
        if len(line) < min_length:
            raise FormatError(
                f"{where}: line has {len(line)} characters, expected at least {min_length}"
            )
        if _field(line, 12, 13) == AGGREGATE_PROVINCE:
            continue
        yield where, line


def _election_id(line: str, where: str) -> str:
    kind = _field(line, 1, 2)
    if kind not in ELECTION_TYPES:
        raise FormatError(
            f"{where}: election type {kind!r} is not supported by this profile version"
        )
    return f"es/{ELECTION_TYPES[kind]}/{_field(line, 3, 6)}-{_field(line, 7, 8)}"


def _station_id(line: str) -> str:
    province = _field(line, 12, 13)
    municipality = _field(line, 14, 16)
    district = _field(line, 17, 18)
    section = _field(line, 19, 22).strip()
    station = _field(line, 23, 23).strip()
    return f"es/{province}/{municipality}/{district}/{section}/{station}"


def read_statements(dataset: Dataset) -> list[Statement]:
    """Turn the per-station files (09 and 10) into statements."""
    votes: dict[tuple[str, str], dict[str, int]] = {}
    for where, line in _rows(dataset, "10", 36):
        key = (_election_id(line, where), _station_id(line))
        code = _field(line, 24, 29).strip()
        per_station = votes.setdefault(key, {})
        if code in per_station:
            raise FormatError(f"{where}: candidature {code} repeated for {key[1]}")
        per_station[code] = _number(line, 30, 36, where)

    evidence: dict[str, object] = {"kind": "official-dataset"}
    if dataset.sha256:
        evidence["sha256"] = dataset.sha256

    statements: list[Statement] = []
    seen: set[tuple[str, str]] = set()
    for where, line in _rows(dataset, "09", 86):
        election = _election_id(line, where)
        station = _station_id(line)
        key = (election, station)
        if key in seen:
            raise FormatError(f"{where}: polling station {station} appears twice")
        seen.add(key)
        extra: dict[str, object] = {}
        for label, start, end in (
            ("censo_cera", 31, 37),
            ("censo_cere", 38, 44),
            ("votantes_cere", 45, 51),
        ):
            value = _number(line, start, end, where)
            if value:
                extra[label] = value
        flag = _field(line, 101, 101).strip()
        if flag:
            extra["datos_oficiales"] = flag
        statements.append(
            Statement(
                profile=PROFILE,
                election=election,
                station=station,
                constituency=f"es/{_field(line, 12, 13)}",
                registered=_number(line, 24, 30, where),
                blank=_number(line, 66, 72, where),
                null=_number(line, 73, 79, where),
                candidature_total=_number(line, 80, 86, where),
                candidatures=votes.pop(key, {}),
                evidence=dict(evidence),
                extra=extra,
            )
        )
    if votes:
        orphan = sorted(station for _, station in votes)[0]
        raise FormatError(
            f"{dataset.name('10')}: {len(votes)} polling station(s) have candidature "
            f"rows but no row in {dataset.name('09')}, e.g. {orphan}"
        )
    return statements


def read_official_totals(dataset: Dataset) -> OfficialTotals:
    """Turn the province-level files (07 and 08) into official totals."""

    votes: dict[str, dict[str, int]] = {}
    for where, line in _rows(dataset, "08", 28):
        _election_id(line, where)
        per_province = votes.setdefault(_field(line, 12, 13), {})
        code = _field(line, 15, 20).strip()
        if code in per_province:
            raise FormatError(f"{where}: candidature {code} repeated")
        per_province[code] = _number(line, 21, 28, where)

    election: str | None = None
    constituencies: dict[str, ConstituencyTotals] = {}
    for where, line in _rows(dataset, "07", 149):
        this_election = _election_id(line, where)
        if election not in (None, this_election):
            raise FormatError(f"{where}: more than one election in the file")
        election = this_election
        province = _field(line, 12, 13)
        key = f"es/{province}"
        if key in constituencies:
            raise FormatError(f"{where}: province {province} appears twice")
        constituencies[key] = ConstituencyTotals(
            stations=_number(line, 73, 77, where),
            blank=_number(line, 126, 133, where),
            null=_number(line, 134, 141, where),
            candidature_total=_number(line, 142, 149, where),
            candidatures=votes.get(province, {}),
        )
    if election is None:
        raise FormatError(f"{dataset.name('07')}: no province rows found")
    source: dict[str, object] = {"kind": "official-dataset"}
    if dataset.sha256:
        source["sha256"] = dataset.sha256
    return OfficialTotals(
        profile=PROFILE, election=election, constituencies=constituencies, source=source
    )
