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
* 05 and 06 (one row per municipality, and per municipality and candidature).
* 03 (the list of candidatures), only to learn under which code the national
  totals merge several candidatures.

Three election types are read. What differs between them is the constituency:
the province for the Congreso, the municipality for local elections and the
whole country for the European Parliament.

Column positions follow the Ministry's record-layout document, "Ficheros de
Carga de Datos de Elecciones" (2010), which ships inside the ZIP files as
``FICHEROS.doc``. See docs/spec/profile-es.md.
"""

from __future__ import annotations

import hashlib
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Iterator

from ...statement import AreaTotals, FormatError, OfficialTotals, Statement
from . import PROFILE
from .seats import LOCAL_THRESHOLD_PERCENT

ENCODING = "iso-8859-1"

# Municipality code used for the overseas-voter census (CERA). Each province
# has one such row in the per-station files. It carries votes but the Ministry
# does not count it as a polling station.
OVERSEAS_MUNICIPALITY = "999"

# Election types this profile reads, and what the constituency is in each.
# Other types (Senate, regional parliaments, island councils...) need their
# own mapping and are refused.
ELECTION_TYPES = {"02": "congreso", "04": "municipales", "07": "europeas"}
CONSTITUENCY = {"02": "province", "04": "municipality", "07": "country"}

# Identifier of the single constituency of European Parliament elections.
COUNTRY = "es"

# Province code 99 marks rows that are subtotals, not a province: national and
# regional totals in files 07/08, and overseas-vote (CERA) totals per region in
# the per-station files 09/10. The same votes also appear under their province.
AGGREGATE_PROVINCE = "99"

_MEMBER = re.compile(r"^(\d{2})(\d{2})(\d{2})(\d{2})\.DAT$", re.IGNORECASE)


@dataclass(frozen=True)
class Dataset:
    """The ``.DAT`` files of one election in a ZIP (or directory).

    A ZIP can carry files of more than one election type: the local-election
    ZIP also holds the files of the provincial councils, which use type 10.
    ``files`` holds the files of the main type, keyed by file number, and
    ``other`` the names of the members that were set aside.
    """

    path: str
    sha256: str | None
    files: dict[str, tuple[str, list[str]]]  # number -> (member name, lines)
    kind: str = ""
    other: tuple[str, ...] = ()

    def lines(self, number: str) -> list[str]:
        if number not in self.files:
            raise FormatError(f"{self.path}: no file {number}TTYYMM.DAT found")
        return self.files[number][1]

    def name(self, number: str) -> str:
        return self.files[number][0]


def load_dataset(path: str) -> Dataset:
    """Read every ``NNTTYYMM.DAT`` member of a ZIP file or directory."""
    by_kind: dict[str, dict[str, tuple[str, list[str]]]] = {}
    digest: str | None = None

    def add(name: str, raw: bytes) -> None:
        match = _MEMBER.match(os.path.basename(name))
        if not match:
            return
        number, kind = match.group(1), match.group(2)
        files = by_kind.setdefault(kind, {})
        if number in files:
            raise FormatError(
                f"{path}: more than one file numbered {number} for election type {kind}"
            )
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
    if not by_kind:
        raise FormatError(f"{path}: no NNTTYYMM.DAT files found")
    kind = _main_kind(path, by_kind)
    other = tuple(
        sorted(name for k, files in by_kind.items() if k != kind for name, _ in files.values())
    )
    return Dataset(path=path, sha256=digest, files=by_kind[kind], kind=kind, other=other)


def _main_kind(path: str, by_kind: dict[str, dict]) -> str:
    """Pick the election type a dataset is about when it carries several."""
    if len(by_kind) == 1:
        return next(iter(by_kind))
    # The per-station file exists for one type only in the ZIPs seen so far.
    for number in ("09", "07", "05"):
        holders = [kind for kind, files in by_kind.items() if number in files]
        if len(holders) == 1:
            return holders[0]
        supported = [kind for kind in holders if kind in ELECTION_TYPES]
        if len(supported) == 1:
            return supported[0]
    raise FormatError(
        f"{path}: files of several election types ({', '.join(sorted(by_kind))}) "
        "and no way to tell which one is meant"
    )


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


def _rows(
    dataset: Dataset, number: str, min_length: int, province_at: tuple[int, int] = (12, 13)
) -> Iterator[tuple[str, str]]:
    """Yield (location, line) for every row that belongs to a province.

    ``province_at`` is where the province code sits; file 06 has no region
    column, so its province is two columns to the left.
    """
    name = dataset.name(number)
    for index, line in enumerate(dataset.lines(number), start=1):
        if not line.strip():
            continue
        where = f"{name}:{index}"
        if len(line) < min_length:
            raise FormatError(
                f"{where}: line has {len(line)} characters, expected at least {min_length}"
            )
        if _field(line, *province_at) == AGGREGATE_PROVINCE:
            continue
        yield where, line


def _election_id(line: str, where: str) -> str:
    kind = _field(line, 1, 2)
    if kind not in ELECTION_TYPES:
        raise FormatError(
            f"{where}: election type {kind!r} is not supported by this profile version"
        )
    return f"es/{ELECTION_TYPES[kind]}/{_field(line, 3, 6)}-{_field(line, 7, 8)}"


def _constituency(line: str) -> str:
    """The constituency of a per-station row, which depends on the election."""
    scope = CONSTITUENCY[_field(line, 1, 2)]
    if scope == "country":
        return COUNTRY
    if scope == "municipality":
        return f"es/{_field(line, 12, 13)}/{_field(line, 14, 16)}"
    return f"es/{_field(line, 12, 13)}"


def _scope(dataset: Dataset, number: str) -> str:
    """What the constituency is in this dataset, read from its first row."""
    name = dataset.name(number)
    for index, line in enumerate(dataset.lines(number), start=1):
        if line.strip():
            _election_id(line, f"{name}:{index}")
            return CONSTITUENCY[_field(line, 1, 2)]
    raise FormatError(f"{name}: no rows found")


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
        # "Censo de escrutinio", the roll used at the count; for overseas rows
        # the same columns hold the CERA census. The INE census (24-30) can
        # differ from it and is zero in some overseas rows.
        registered = _number(line, 31, 37, where)
        extra: dict[str, object] = {}
        for label, start, end in (
            ("censo_ine", 24, 30),
            ("censo_cere", 38, 44),
            ("votantes_cere", 45, 51),
        ):
            value = _number(line, start, end, where)
            if value and not (label == "censo_ine" and value == registered):
                extra[label] = value
        flag = _field(line, 101, 101).strip()
        if flag:
            extra["datos_oficiales"] = flag
        statements.append(
            Statement(
                profile=PROFILE,
                election=election,
                station=station,
                constituency=_constituency(line),
                registered=registered,
                blank=_number(line, 66, 72, where),
                null=_number(line, 73, 79, where),
                candidature_total=_number(line, 80, 86, where),
                candidatures=votes.pop(key, {}),
                unit="aggregate"
                if _field(line, 14, 16) == OVERSEAS_MUNICIPALITY
                else "station",
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
    """Official totals per constituency, whatever the constituency is.

    Province rows for the Congreso, whole-municipality rows for local
    elections and the national row for the European Parliament.
    """
    scope = _scope(dataset, "05" if "07" not in dataset.files else "07")
    if scope == "municipality":
        return read_municipal_totals(dataset, as_constituency=True)
    if scope == "country":
        return read_national_totals(dataset)
    return read_province_totals(dataset)


def read_province_totals(dataset: Dataset, *, as_level: bool = False) -> OfficialTotals:
    """Turn the province rows of files 07 and 08 into official totals.

    With ``as_level`` the provinces are a level below the constituency (or the
    same thing under another name) and statements are assigned to them by the
    province part of the station identifier, overseas rows included.
    """

    votes: dict[str, dict[str, int]] = {}
    for where, line in _rows(dataset, "08", 28):
        _election_id(line, where)
        per_province = votes.setdefault(_field(line, 12, 13), {})
        code = _field(line, 15, 20).strip()
        if code in per_province:
            raise FormatError(f"{where}: candidature {code} repeated")
        per_province[code] = _number(line, 21, 28, where)

    election: str | None = None
    constituencies: dict[str, AreaTotals] = {}
    for where, line in _rows(dataset, "07", 149):
        this_election = _election_id(line, where)
        if election not in (None, this_election):
            raise FormatError(f"{where}: more than one election in the file")
        election = this_election
        province = _field(line, 12, 13)
        key = f"es/{province}"
        if key in constituencies:
            raise FormatError(f"{where}: province {province} appears twice")
        constituencies[key] = AreaTotals(
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
    if as_level:
        return OfficialTotals(
            profile=PROFILE,
            election=election,
            areas=constituencies,
            level="province",
            grouping="station-prefix/2",
            source=source,
        )
    return OfficialTotals(
        profile=PROFILE, election=election, areas=constituencies, source=source
    )


def read_candidature_heads(dataset: Dataset, columns: tuple[int, int]) -> dict[str, str]:
    """Which code the totals at some level use for each candidature.

    File 03 gives, for every candidature, the code under which its votes are
    accumulated at province, region and national level (columns 215-220,
    221-226 and 227-232). Only pairs where the two codes differ are returned.
    A dataset without file 03 gives an empty mapping.
    """
    if "03" not in dataset.files:
        return {}
    heads: dict[str, str] = {}
    name = dataset.name("03")
    for index, line in enumerate(dataset.lines("03"), start=1):
        if not line.strip():
            continue
        where = f"{name}:{index}"
        if len(line) < columns[1]:
            raise FormatError(
                f"{where}: line has {len(line)} characters, expected at least {columns[1]}"
            )
        code = _field(line, 9, 14).strip()
        head = _field(line, *columns).strip()
        if head and head.strip("0") and head != code:
            heads[code] = head
    return heads


NATIONAL_HEAD = (227, 232)


def read_national_totals(dataset: Dataset) -> OfficialTotals:
    """Turn the national row of files 07 and 08 into official totals.

    The national row has region 99 and province 99. Its candidature rows use
    the national accumulation code of file 03, so the mapping travels with the
    totals and the verifier merges the station votes the same way.
    """
    name07, name08 = dataset.name("07"), dataset.name("08")
    votes: dict[str, int] = {}
    for index, line in enumerate(dataset.lines("08"), start=1):
        if not line.strip():
            continue
        where = f"{name08}:{index}"
        if len(line) < 28:
            raise FormatError(f"{where}: line has {len(line)} characters, expected at least 28")
        if _field(line, 10, 13) != "9999":
            continue
        _election_id(line, where)
        code = _field(line, 15, 20).strip()
        if code in votes:
            raise FormatError(f"{where}: candidature {code} repeated in the national rows")
        votes[code] = _number(line, 21, 28, where)

    election: str | None = None
    national: AreaTotals | None = None
    for index, line in enumerate(dataset.lines("07"), start=1):
        if not line.strip():
            continue
        where = f"{name07}:{index}"
        if len(line) < 149:
            raise FormatError(f"{where}: line has {len(line)} characters, expected at least 149")
        if _field(line, 10, 13) != "9999":
            continue
        if national is not None:
            raise FormatError(f"{where}: more than one national row")
        election = _election_id(line, where)
        national = AreaTotals(
            stations=_number(line, 73, 77, where),
            blank=_number(line, 126, 133, where),
            null=_number(line, 134, 141, where),
            candidature_total=_number(line, 142, 149, where),
            candidatures=votes,
        )
    if national is None or election is None:
        raise FormatError(f"{name07}: no national row found")
    source: dict[str, object] = {"kind": "official-dataset"}
    if dataset.sha256:
        source["sha256"] = dataset.sha256
    return OfficialTotals(
        profile=PROFILE,
        election=election,
        areas={COUNTRY: national},
        merge=read_candidature_heads(dataset, NATIONAL_HEAD),
        source=source,
    )


# In the municipal files, district 99 marks the row for the whole municipality.
WHOLE_MUNICIPALITY = "99"


def read_municipal_totals(dataset: Dataset, *, as_constituency: bool = False) -> OfficialTotals:
    """Turn the municipality-level files (05 and 06) into official totals.

    In local elections the municipality is the constituency. In the others it
    is a level below, used to locate a difference: comparing per municipality
    shows where the station sums and the published totals part ways. Overseas
    rows belong to no municipality and are left out.
    """
    votes: dict[str, dict[str, int]] = {}
    for where, line in _rows(dataset, "06", 30, province_at=(10, 11)):
        if _field(line, 15, 16) != WHOLE_MUNICIPALITY:
            continue
        _election_id(line, where)
        key = f"es/{_field(line, 10, 11)}/{_field(line, 12, 14)}"
        per_municipality = votes.setdefault(key, {})
        code = _field(line, 17, 22).strip()
        if code in per_municipality:
            raise FormatError(f"{where}: candidature {code} repeated")
        per_municipality[code] = _number(line, 23, 30, where)

    election: str | None = None
    municipalities: dict[str, AreaTotals] = {}
    for where, line in _rows(dataset, "05", 213):
        if _field(line, 17, 18) != WHOLE_MUNICIPALITY:
            continue
        this_election = _election_id(line, where)
        if election not in (None, this_election):
            raise FormatError(f"{where}: more than one election in the file")
        election = this_election
        key = f"es/{_field(line, 12, 13)}/{_field(line, 14, 16)}"
        if key in municipalities:
            raise FormatError(f"{where}: municipality {key} appears twice")
        municipalities[key] = AreaTotals(
            stations=_number(line, 137, 141, where),
            blank=_number(line, 190, 197, where),
            null=_number(line, 198, 205, where),
            candidature_total=_number(line, 206, 213, where),
            candidatures=votes.get(key, {}),
        )
    if election is None:
        raise FormatError(f"{dataset.name('05')}: no municipality rows found")
    source: dict[str, object] = {"kind": "official-dataset"}
    if dataset.sha256:
        source["sha256"] = dataset.sha256
    if as_constituency:
        return OfficialTotals(
            profile=PROFILE, election=election, areas=municipalities, source=source
        )
    return OfficialTotals(
        profile=PROFILE,
        election=election,
        areas=municipalities,
        level="municipality",
        grouping="station-prefix/3",
        source=source,
    )


def read_municipal_seats(dataset: Dataset) -> dict[str, tuple[int, dict[str, int]]]:
    """Seats to fill and seats published per candidature, by municipality.

    Only meaningful in local elections, where the municipality is the
    constituency: file 05 gives the seats to fill (columns 214-216) and file
    06 the candidates each candidature obtained (columns 31-33).
    """
    if _scope(dataset, "05") != "municipality":
        raise FormatError(
            f"{dataset.path}: seats per municipality are only read for local elections"
        )
    published: dict[str, dict[str, int]] = {}
    for where, line in _rows(dataset, "06", 33, province_at=(10, 11)):
        if _field(line, 15, 16) != WHOLE_MUNICIPALITY:
            continue
        key = f"es/{_field(line, 10, 11)}/{_field(line, 12, 14)}"
        won = _number(line, 31, 33, where)
        if won:
            published.setdefault(key, {})[_field(line, 17, 22).strip()] = won
    result: dict[str, tuple[int, dict[str, int]]] = {}
    for where, line in _rows(dataset, "05", 216):
        if _field(line, 17, 18) != WHOLE_MUNICIPALITY:
            continue
        key = f"es/{_field(line, 12, 13)}/{_field(line, 14, 16)}"
        result[key] = (_number(line, 214, 216, where), published.get(key, {}))
    return result


def read_province_seats(dataset: Dataset) -> tuple[dict[str, int], dict[str, str]]:
    """Seats won per province, added up over its candidatures, and the
    province names, for the Congreso.

    File 08 gives, after the votes, the "número de candidatos obtenidos por la
    candidatura" (columns 29-33), and file 07 the province name (columns
    15-64). Those positions were taken from the rows themselves, in the order
    of fields the record-layout document lists; the seats add up to 350 in
    the Congreso of November 2019.
    """
    if _scope(dataset, "08") != "province":
        raise FormatError(f"{dataset.path}: seats per province are only read for the Congreso")
    seats: dict[str, int] = {}
    for where, line in _rows(dataset, "08", 33):
        province = _field(line, 12, 13)
        if province == AGGREGATE_PROVINCE:
            continue
        key = f"es/{province}"
        seats[key] = seats.get(key, 0) + _number(line, 29, 33, where)
    names: dict[str, str] = {}
    for _, line in _rows(dataset, "07", 64):
        province = _field(line, 12, 13)
        if province != AGGREGATE_PROVINCE:
            names[f"es/{province}"] = _field(line, 15, 64).strip()
    return seats, names


def card_context(dataset: Dataset) -> dict:
    """What a verifiability card needs to know about a Spanish election, as
    far as the Ministry's files say it. Facts the files do not give are left
    for a person to fill in, with their source."""
    scope = _scope(dataset, "09")
    statements_election = None
    for index, line in enumerate(dataset.lines("09"), start=1):
        if line.strip():
            statements_election = _election_id(line, f"{dataset.name('09')}:{index}")
            break
    layout = {
        "document": "Ministerio del Interior, Ficheros de Carga de Datos de Elecciones "
        "(FICHEROS.doc, inside the ZIP)",
        "sha256": dataset.sha256,
    }
    channels: list[dict] = []
    if scope != "municipality":
        channels.append(
            {
                "name": "abroad (CERA)",
                "match": {"unit": "aggregate"},
                "published_at": "province",
                "by_area": True,
                "custody_chain": {"value": None, "status": "unverified"},
                "source": dict(layout, note="one row per province, municipality code 999"),
            }
        )
    channels.append(
        {
            "name": "postal",
            "published_at": "not_published_separately",
            "custody_chain": {"value": None, "status": "unverified"},
            "source": dict(
                layout,
                note="the fields of files 09 and 10 have no postal vote; read in the text "
                "extracted from the document, which may miss a field",
            ),
        }
    )
    if scope == "province":
        seats, names = read_province_seats(dataset)
        contest = {
            "kind": "seats",
            "seats": seats,
            "names": names,
            "threshold_percent": 3,
            "ties": "more_votes_then_lot",
            "detail": "by_constituency",
            "source": dict(
                layout,
                file=dataset.name("08"),
                note="seats to fill: the candidates each candidature obtained, added up; "
                "rule: LOREG, article 163.1",
            ),
        }
    elif scope == "municipality":
        contest = {
            "kind": "seats",
            "seats": {key: to_fill for key, (to_fill, _) in read_municipal_seats(dataset).items()},
            "threshold_percent": LOCAL_THRESHOLD_PERCENT,
            "ties": "more_votes_then_lot",
            "detail": "distribution_only",
            "source": dict(
                layout,
                file=dataset.name("05"),
                note="seats to fill, columns 214-216; rule: LOREG, articles 163.1 and 180",
            ),
        }
    else:
        contest = {
            "kind": "seats",
            "status": "pending",
            "reason": "the allocation articles for the European Parliament have not been read",
        }
    return {
        "spec": "actasum/card-context/v0.1",
        "election": statements_election,
        "contest": contest,
        "channels": channels,
    }


def read_overseas_residuals(dataset: Dataset) -> OfficialTotals:
    """What the official totals imply for each province's overseas row.

    The Ministry publishes province totals and municipality totals, but no
    separate overseas (CERA) total per province in those files. The province
    total minus the sum of its municipalities is what is left for the overseas
    vote. Comparing that residual with the overseas row of the per-station
    file tells whether a province-level difference sits in that row.

    A residual can be negative when the two official levels disagree with each
    other; that is reported as a difference like any other.
    """
    if _scope(dataset, "07") == "municipality":
        raise FormatError(
            f"{dataset.path}: local elections have no overseas rows to compare"
        )
    provinces = read_province_totals(dataset)
    municipalities = read_municipal_totals(dataset)
    sums: dict[str, dict] = {}
    for key, totals in municipalities.areas.items():
        province = "/".join(key.split("/")[:2])
        bucket = sums.setdefault(province, {"blank": 0, "null": 0, "total": 0, "votes": {}})
        bucket["blank"] += totals.blank
        bucket["null"] += totals.null
        bucket["total"] += totals.candidature_total or 0
        for code, count in totals.candidatures.items():
            bucket["votes"][code] = bucket["votes"].get(code, 0) + count
    residuals: dict[str, AreaTotals] = {}
    for key, totals in provinces.areas.items():
        inner = sums.get(key, {"blank": 0, "null": 0, "total": 0, "votes": {}})
        codes = set(totals.candidatures) | set(inner["votes"])
        residuals[key] = AreaTotals(
            blank=totals.blank - inner["blank"],
            null=totals.null - inner["null"],
            candidature_total=(totals.candidature_total or 0) - inner["total"],
            candidatures={
                code: totals.candidatures.get(code, 0) - inner["votes"].get(code, 0)
                for code in codes
            },
        )
    return OfficialTotals(
        profile=PROFILE,
        election=provinces.election,
        areas=residuals,
        level="overseas row",
        grouping="station-prefix/2",
        source=dict(provinces.source, derived="province total minus municipalities"),
    )


def describe(dataset: Dataset) -> dict:
    """What a dataset contains, without interpreting any result.

    Meant for a first look at an election type or year that has not been run
    before: which files are there, how long their lines are, how many rows are
    subtotals or overseas rows, and whether file 03 merges candidatures.
    """
    files = []
    for number in sorted(dataset.files):
        name, lines = dataset.files[number]
        rows = [line for line in lines if line.strip()]
        lengths = sorted({len(line) for line in rows})
        entry: dict[str, object] = {
            "file": name,
            "rows": len(rows),
            "line_lengths": lengths[:6] + (["..."] if len(lengths) > 6 else []),
        }
        if number not in ("11", "12"):
            # Files 11 and 12 use columns 1-2 for something else.
            entry["types_in_rows"] = sorted({_field(line, 1, 2) for line in rows})
        if number in ("09", "10"):
            entry["subtotal_rows_province_99"] = sum(
                1 for line in rows if _field(line, 12, 13) == AGGREGATE_PROVINCE
            )
            entry["overseas_rows_municipality_999"] = sum(
                1
                for line in rows
                if _field(line, 14, 16) == OVERSEAS_MUNICIPALITY
                and _field(line, 12, 13) != AGGREGATE_PROVINCE
            )
            entry["provinces"] = len(
                {_field(line, 12, 13) for line in rows} - {AGGREGATE_PROVINCE}
            )
        if number in ("07", "08"):
            entry["national_rows"] = sum(1 for line in rows if _field(line, 10, 13) == "9999")
            entry["region_rows"] = sum(
                1
                for line in rows
                if _field(line, 12, 13) == AGGREGATE_PROVINCE and _field(line, 10, 11) != "99"
            )
            entry["province_rows"] = sum(
                1 for line in rows if _field(line, 12, 13) != AGGREGATE_PROVINCE
            )
            if number == "07":
                entry["district_codes"] = sorted({_field(line, 14, 14) for line in rows})
        if number == "05":
            entry["whole_municipality_rows"] = sum(
                1 for line in rows if _field(line, 17, 18) == WHOLE_MUNICIPALITY
            )
        if number == "03":
            entry["candidatures"] = len(rows)
            for label, columns in (
                ("province", (215, 220)),
                ("region", (221, 226)),
                ("national", NATIONAL_HEAD),
            ):
                usable = [line for line in rows if len(line) >= columns[1]]
                entry[f"merged_under_another_code_{label}"] = sum(
                    1
                    for line in usable
                    if _field(line, *columns).strip("0 ")
                    and _field(line, *columns) != _field(line, 9, 14)
                )
        files.append(entry)
    return {
        "path": dataset.path,
        "sha256": dataset.sha256,
        "election_type": dataset.kind,
        "supported": dataset.kind in ELECTION_TYPES,
        "files": files,
        "files_of_other_types_set_aside": list(dataset.other),
    }
