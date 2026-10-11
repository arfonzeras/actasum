"""Reader for two databases published by Mexico's Instituto Nacional Electoral.

* The **PREP** database (*Programa de Resultados Electorales Preliminares*):
  one row per tally sheet (*acta de escrutinio y cómputo*) as it was captured
  from the copy that reached a collection centre on election night. The INE
  calls these results preliminary and not definitive.
* The **Cómputos Distritales** database: one row per tally sheet as the
  district councils computed it in the days after the election, either by
  comparing tally sheets (*cotejo*) or by counting the ballots of the station
  again (*recuento*).

A PREP row gives a statement of the count at the station; a Cómputos row gives
a statement of the canvass that replaces it. The two files are published by
the same authority, with different separators, encodings and column names.

Neither file carries the name of any person other than the district names,
and nothing but figures and codes is copied.

See docs/spec/profile-mx.md.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

from ...statement import FormatError, Statement
from . import PROFILE

COUNTRY = "mx"

# Election types this profile reads, by the first word of the file's title line.
ELECTIONS = {"PRESIDENCIA": "presidencia"}

# Category of ballots that are neither null nor for a registered candidature.
UNREGISTERED = "unregistered"

# Reason given for PREP rows that add up the vote from abroad of a whole state.
STATE_WIDE = "vote from abroad given per state, not per counting table"

# What the PREP writes in a vote cell it could not capture, and the reason
# the core gives for an unread figure (core, section 3.4).
NO_FIGURE, ILLEGIBLE = "Sin dato", "Ilegible"
UNREADABLE = {NO_FIGURE: "empty", ILLEGIBLE: "illegible"}

_KEY_COLUMN = "CLAVE_CASILLA"
_UNREGISTERED_COLUMNS = ("NO_REGISTRADAS", "CANDIDATO/A NO REGISTRADO/A")
_NULL_COLUMNS = ("NULOS", "VOTOS NULOS")
# The vote columns start after the last of these that the file has.
_BEFORE_VOTES = ("TIPO_ACTA", "TOTAL_VOTOS_SACADOS")
_STATION_KEY = re.compile(r"(\d{2})(\d{4})([A-Z]\d{4})")

PREP, COMPUTOS = "prep", "computos"


@dataclass(frozen=True)
class Table:
    """The rows of one database file, and what its own header says."""

    path: str
    sha256: str
    kind: str  # PREP or COMPUTOS
    title: str  # first line: the election
    cut: str  # second line: date and time the file was generated
    summary: dict[str, str]  # the file's own totals, as printed
    columns: list[str]
    rows: list[dict[str, str]]
    # Candidature codes in the order of the file: parties and combinations of
    # parties of one coalition, as they appear on the tally sheet.
    codes: list[str]
    unregistered_column: str
    null_column: str

    @property
    def vote_columns(self) -> list[str]:
        start = self.columns.index(self.unregistered_column) - len(self.codes)
        return self.columns[start : start + len(self.codes)]


def _clean(value: str) -> str:
    """Undo the spreadsheet guards the files put around some values."""
    value = value.strip()
    if value.startswith('="') and value.endswith('"'):
        value = value[2:-1]
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        value = value[1:-1]
    return value


def _number(text: str) -> int | None:
    text = text.replace(",", "")
    return int(text) if text.isdigit() else None


def code_of(column: str) -> str:
    """A vote column as a candidature code: ``PVEM_PT`` and ``PVEM-PT`` are one."""
    return column.replace("_", "-")


def load(path: str) -> Table:
    """Read a PREP or a Cómputos Distritales database file (``PRES_2024.csv``)."""
    with open(path, "rb") as handle:
        raw = handle.read()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    lines = [line for line in text.splitlines() if not line.startswith("sep=")]
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith(_KEY_COLUMN))
    except StopIteration:
        raise FormatError(f"{path}: no header line starting with {_KEY_COLUMN}") from None
    delimiter = "|" if "|" in lines[start] else ","

    def split(line: str) -> list[str]:
        return [_clean(value) for value in next(csv.reader([line], delimiter=delimiter))]

    columns = split(lines[start])
    preamble = [line for line in lines[:start] if line.strip()]
    if len(preamble) < 2:
        raise FormatError(f"{path}: the title and cut lines are missing")
    summary: dict[str, str] = {}
    if len(preamble) >= 4:
        summary = dict(zip(split(preamble[-2]), split(preamble[-1])))

    if "CONTABILIZADA" in columns:
        kind = PREP
    elif "TOTAL_VOTOS_CALCULADOS" in columns:
        kind = COMPUTOS
    else:
        raise FormatError(f"{path}: neither a PREP nor a Cómputos Distritales database")
    unregistered = next((c for c in _UNREGISTERED_COLUMNS if c in columns), None)
    null = next((c for c in _NULL_COLUMNS if c in columns), None)
    before = [columns.index(c) for c in _BEFORE_VOTES if c in columns]
    if unregistered is None or null is None or not before:
        raise FormatError(f"{path}: the vote columns could not be located")
    codes = [code_of(c) for c in columns[max(before) + 1 : columns.index(unregistered)]]
    if not codes or len(set(codes)) != len(codes):
        raise FormatError(f"{path}: the vote columns could not be located")

    rows: list[dict[str, str]] = []
    for number, line in enumerate(lines[start + 1 :], start=start + 2):
        if not line.strip():
            continue
        fields = split(line)
        if len(fields) != len(columns):
            raise FormatError(
                f"{path}: data line {number}: {len(fields)} columns, expected {len(columns)}"
            )
        rows.append(dict(zip(columns, fields)))
    if not rows:
        raise FormatError(f"{path}: no rows")
    return Table(
        path=path, sha256=digest, kind=kind, title=preamble[0].strip(),
        cut=preamble[1].strip(), summary=summary, columns=columns, rows=rows,
        codes=codes, unregistered_column=unregistered, null_column=null,
    )  # fmt: skip


def election_id(table: Table, year_month: str) -> str:
    """``mx/presidencia/2024-06``. The files do not carry the election date."""
    if not re.fullmatch(r"\d{4}-\d{2}", year_month):
        raise FormatError("the election date must be given as YYYY-MM")
    words = table.title.split()
    kind = ELECTIONS.get(words[0].upper() if words else "")
    if kind is None:
        raise FormatError(
            f"{table.path}: election {table.title!r} is not supported by this profile version"
        )
    return f"{COUNTRY}/{kind}/{year_month}"


def station_id(key: str) -> str | None:
    """``010338B0100`` -> ``mx/01/0338/B0100``: state, section, station.

    Returns None for a key that is not one, as in the PREP rows of tally
    sheets that could not be matched to an approved station.
    """
    match = _STATION_KEY.fullmatch(key)
    return f"{COUNTRY}/{match[1]}/{match[2]}/{match[3]}" if match else None


def coalition_merge(codes: list[str]) -> dict[str, str]:
    """Candidature code -> the code of the whole coalition it belongs to.

    A coalition's candidate receives the votes of each of its parties and of
    every combination of them marked on a ballot. The files have one column
    per party and per combination. The whole coalition is the longest
    combination; a party that appears in no combination stands alone. The
    result is what ``OfficialTotals.merge`` and ``aggregate`` expect.
    """
    combos = sorted((c for c in codes if "-" in c), key=lambda c: -len(c.split("-")))
    merge: dict[str, str] = {}
    for code in codes:
        parts = set(code.split("-"))
        whole = next((c for c in combos if parts <= set(c.split("-"))), code)
        if whole != code:
            merge[code] = whole
    return merge


@dataclass
class Reading:
    """Statements built from one file, and everything that was left out."""

    statements: list[Statement] = field(default_factory=list)
    rows: int = 0
    # Rows that gave no statement, by the reason the file itself states.
    left_out: Counter = field(default_factory=Counter)
    # PREP only: tally sheets the PREP counted although it could not capture
    # every figure, by which marks they carry, and the cells concerned.
    with_unread_figures: Counter = field(default_factory=Counter)
    unread_cells: Counter = field(default_factory=Counter)
    # PREP only: tally sheets whose written total is not the sum of their figures.
    stated_total_differs: int = 0
    # Cómputos only: station -> what the file says of a row without figures.
    no_figures: dict[str, str] = field(default_factory=dict)
    # PREP only: ballots in the rows left out as STATE_WIDE.
    state_wide_ballots: int = 0
    # Station -> identifier of its statement, to chain a later act to it.
    identifiers: dict[str, str] = field(default_factory=dict)


def _figures(table: Table, row: dict[str, str]) -> tuple[dict[str, int], dict[str, str]]:
    """The vote cells of a row: those with a figure, and those without one."""
    known: dict[str, int] = {}
    unknown: dict[str, str] = {}
    cells = list(zip(table.codes, table.vote_columns)) + [
        (f"other:{UNREGISTERED}", table.unregistered_column),
        ("null", table.null_column),
    ]
    for item, column in cells:
        number = _number(row[column])
        if number is None:
            unknown[item] = row[column]
        else:
            known[item] = number
    return known, unknown


def _item(name: str) -> str:
    """A cell as the core names it: ``candidature:PAN``, ``other:...``, ``null``."""
    return name if name == "null" or name.startswith("other:") else f"candidature:{name}"


def _registered(row: dict[str, str]) -> int | None:
    # Special stations have no voter list: the files give zero or N/A.
    return _number(row.get("LISTA_NOMINAL", "")) or None


def _statement(table, row, election, station, known, unread=None, **more) -> Statement:
    codes = set(table.codes)
    other = known.get(f"other:{UNREGISTERED}")
    return Statement(
        profile=PROFILE,
        election=election,
        station=station,
        constituency=COUNTRY,
        # These tally sheets have no figure for blank votes (core, section 3.5).
        blank=None,
        not_on_sheet={"blank": "no-field"},
        null=known.get("null"),
        candidatures={item: votes for item, votes in known.items() if item in codes},
        other={} if other is None else {UNREGISTERED: other},
        unread=unread or {},
        registered=_registered(row),
        evidence={"kind": "official-dataset", "sha256": table.sha256},
        **more,
    )


def read_prep(table: Table, year_month: str) -> Reading:
    """One statement of the count per tally sheet the PREP counted.

    The PREP counts a tally sheet when at least one figure could be captured,
    and adds up the cells it could not capture as zero. A figure that could
    not be read is not a zero: those cells go to ``counts.unread``, as
    ``empty`` for ``Sin dato`` and ``illegible`` for ``Ilegible``, and carry
    no value. The rows of the vote from abroad give no statement (see
    ``STATE_WIDE``).
    """
    if table.kind != PREP:
        raise FormatError(f"{table.path}: not a PREP database")
    election = election_id(table, year_month)
    reading = Reading(rows=len(table.rows))
    seen: set[str] = set()
    for row in table.rows:
        station = station_id(row[_KEY_COLUMN])
        if row["CONTABILIZADA"] != "1" or station is None:
            reason = row["OBSERVACIONES"] or "no tally sheet captured at the cut"
            reading.left_out[reason] += 1
            continue
        if station in seen:
            raise FormatError(f"{table.path}: station {station} appears twice")
        seen.add(station)
        if station.split("/")[2] == "0000":
            # One row for the vote from abroad of a whole state. The canvass
            # file gives that vote per counting table, under other keys, so
            # nothing there could replace this row and its votes would stand
            # twice. The core cannot say that several later statements
            # replace one earlier one.
            reading.left_out[STATE_WIDE] += 1
            reading.state_wide_ballots += sum(_figures(table, row)[0].values())
            continue
        known, unknown = _figures(table, row)
        for item, text in unknown.items():
            if text not in UNREADABLE:
                raise FormatError(f"{table.path}: {station}: {item} is not a number: {text!r}")
            reading.unread_cells[UNREADABLE[text]] += 1
        stated = _number(row.get("TOTAL_VOTOS_ASENTADO", ""))
        if stated is not None and stated != sum(known.values()):
            reading.stated_total_differs += 1
        if unknown:
            marks = sorted({UNREADABLE[text] for text in unknown.values()})
            reading.with_unread_figures[" and ".join(marks)] += 1
        extra: dict = {}
        if row.get("TIPO_DOCUMENTO", "-") not in ("", "-"):
            extra["document"] = row["TIPO_DOCUMENTO"]
        if re.fullmatch(r"[0-9a-f]{64}", row.get("CODIGO_INTEGRIDAD", "")):
            # Hash of the scanned tally sheet, as the PREP gives it.
            extra["image_sha256"] = row["CODIGO_INTEGRIDAD"]
        if stated is not None:
            extra["stated_total"] = stated
        unread = {_item(name): UNREADABLE[text] for name, text in unknown.items()}
        statement = _statement(table, row, election, station, known, unread, extra=extra)
        reading.statements.append(statement)
        reading.identifiers[station] = statement.statement_id()
    return reading


def recounted(observation: str) -> bool | None:
    """True when the ballots were counted again (*recuento*), False when the
    tally sheets were compared (*cotejo*), as the file's OBSERVACIONES column
    says; None when it says neither."""
    word = observation.split(" ", 1)[0].lower()
    return {"recuento": True, "cotejo": False}.get(word)


def read_computos(
    table: Table, year_month: str, counts: dict[str, str] | None = None
) -> Reading:
    """One statement of the canvass per tally sheet the district councils computed.

    ``counts`` maps a station to the identifier of its statement of the count
    (``Reading.identifiers`` of the PREP); the statement of the canvass then
    names it in ``supersedes``. A row without figures (package not received,
    station not installed) gives no statement.
    """
    if table.kind != COMPUTOS:
        raise FormatError(f"{table.path}: not a Cómputos Distritales database")
    election = election_id(table, year_month)
    counts = counts or {}
    reading = Reading(rows=len(table.rows))
    for row in table.rows:
        station = station_id(row[_KEY_COLUMN])
        if station is None:
            raise FormatError(f"{table.path}: not a station key: {row[_KEY_COLUMN]!r}")
        if station in reading.identifiers:
            raise FormatError(f"{table.path}: station {station} appears twice")
        known, unknown = _figures(table, row)
        if unknown:
            if any(text != "-" for text in unknown.values()) or known:
                raise FormatError(f"{table.path}: {station}: figures are not numbers")
            reading.left_out[row["OBSERVACIONES"] or "no figures"] += 1
            reading.no_figures[station] = row["OBSERVACIONES"]
            continue
        extra: dict = {"observation": row["OBSERVACIONES"]}
        recount = recounted(row["OBSERVACIONES"])
        if recount is not None:
            # The key shared across profiles: core, section 7.
            extra["recount"] = recount
        statement = _statement(
            table, row, election, station, known,
            stage="canvass", supersedes=counts.get(station), extra=extra,
        )  # fmt: skip
        reading.statements.append(statement)
        reading.identifiers[station] = statement.statement_id()
    return reading


@dataclass(frozen=True)
class HeaderCheck:
    name: str
    in_header: int
    from_rows: int

    @property
    def ok(self) -> bool:
        return self.in_header == self.from_rows


def check_header(table: Table) -> list[HeaderCheck]:
    """Recompute from the rows the totals the file prints above them.

    The PREP's totals are those of the tally sheets it counted, with the
    cells it could not capture added up as zero.
    """
    counted = [
        row for row in table.rows
        if table.kind == COMPUTOS or (row["CONTABILIZADA"] == "1" and station_id(row[_KEY_COLUMN]))
    ]  # fmt: skip
    votes = sum(sum(_figures(table, row)[0].values()) for row in counted)
    registered = sum(_number(row.get("LISTA_NOMINAL", "")) or 0 for row in counted)
    names = (
        ("ACTAS_CONTABILIZADAS", "TOTAL_VOTOS_C_CS", "LISTA_NOMINAL_ACTAS_CONTABILIZADAS")
        if table.kind == PREP
        else ("ACTAS_COMPUTADAS", "TOTAL_VOTOS", "LISTA_NOMINAL_ACTAS_COMPUTADAS")
    )
    checks = []
    for name, value in zip(names, (len(counted), votes, registered)):
        printed = _number(table.summary.get(name, ""))
        if printed is not None:
            checks.append(HeaderCheck(name, printed, value))
    return checks


_SIZES = ((1, "1 vote"), (10, "2 to 10"), (100, "11 to 100"), (float("inf"), "more than 100"))


def _how(statement: Statement) -> str:
    recount = statement.extra.get("recount")
    return "not stated" if recount is None else "recount" if recount else "collation"


def describe(resolution, merge: dict[str, str]) -> dict:
    """What the core's resolution of the two acts says, in this profile's terms.

    ``resolution`` is the result of ``actasum.verify.resolve`` on the
    statements of both files. Stations whose figures changed are split by
    whether the ballots were counted again and by the largest change in a
    single figure of the sheet. Changes that only move votes between the
    columns of one coalition are told apart from those that change what a
    candidature gets. Figures the count could not read are not changes: the
    core leaves them out, and they are described by ``unread_against_canvass``.
    """
    how = {s.station: _how(s) for s in resolution.standing}
    changed: Counter = Counter()
    sizes: dict[str, Counter] = {}
    within_coalition = 0
    net: Counter = Counter()
    net_of_largest: Counter = Counter()
    net_in_part: Counter = Counter()
    net_by_kind: dict[str, Counter] = {}
    in_part = set(resolution.partly_compared)
    changed_in_part = 0
    for change in resolution.changes:
        kind = how.get(change.station, "not stated")
        changed[kind] += 1
        moved: Counter = Counter()
        largest = 0
        for item, (earlier, standing) in change.items.items():
            name = item.removeprefix("candidature:")
            moved[merge.get(name, name)] += standing - earlier
            largest = max(largest, abs(standing - earlier))
        label = next(label for limit, label in _SIZES if largest <= limit)
        sizes.setdefault(kind, Counter())[label] += 1
        if not any(moved.values()):
            within_coalition += 1
        if largest > _SIZES[-2][0]:
            net_of_largest.update(moved)
        if change.station in in_part:
            changed_in_part += 1
            net_in_part.update(moved)
        net_by_kind.setdefault(kind, Counter()).update(moved)
        net.update(moved)
    compared = [s for s in resolution.standing if s.supersedes]
    by_kind = Counter(_how(s) for s in compared)
    return {
        "stations_with_both_acts": len(compared),
        "of_them_by_canvass": dict(sorted(by_kind.items())),
        "of_them_compared_only_in_part": len(resolution.partly_compared),
        "stations_whose_figures_changed": len(resolution.changes),
        "changed_by_canvass": dict(sorted(changed.items())),
        # Size of a change: the largest change in one figure of the sheet.
        "changed_by_canvass_and_size": {
            kind: {label: tally[label] for _, label in _SIZES if tally[label]}
            for kind, tally in sorted(sizes.items())
        },
        "changed_only_within_a_coalition": within_coalition,
        "net_change_by_candidature": {k: v for k, v in sorted(net.items()) if v},
        "net_change_by_canvass": {
            kind: {k: v for k, v in sorted(tally.items()) if v}
            for kind, tally in sorted(net_by_kind.items())
        },
        "net_change_where_a_figure_changed_by_more_than_100": {
            k: v for k, v in sorted(net_of_largest.items()) if v
        },
        # Stations where the count has unread figures: only the others are compared.
        "changed_among_those_compared_only_in_part": changed_in_part,
        "net_change_among_those_compared_only_in_part": {
            k: v for k, v in sorted(net_in_part.items()) if v
        },
        "stations_with_a_canvass_but_no_count": len(resolution.without_count),
        "stations_with_a_count_but_no_canvass": sum(
            1 for s in resolution.standing if s.stage == "count"
        ),
        "stations_in_conflict": len(resolution.conflicts),
        "stations_undetermined": len(resolution.undetermined),
    }


def unread_against_canvass(resolution) -> dict:
    """What the canvass gives where the count could not read a figure, by reason."""
    standing = {s.station: s for s in resolution.standing if s.stage != "count"}
    result: dict[str, Counter] = {}
    for counted in resolution.counted:
        later = standing.get(counted.station)
        if later is None:
            continue
        for item, reason in counted.unread.items():
            value = later.value(item)
            if value is None:
                continue
            tally = result.setdefault(reason, Counter())
            tally["cells"] += 1
            tally["zero_in_the_canvass" if value == 0 else "not_zero_in_the_canvass"] += 1
            tally["votes_in_the_canvass"] += value
    return {reason: dict(tally) for reason, tally in sorted(result.items())}
